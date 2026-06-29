"""
DeepSeek 处方生成服务。

调用 DeepSeek API，将体态评估 + FMS 数据 + 动作库 输入模型，
生成结构化 JSON 处方计划，解析并验证后返回。
"""
import json
import re
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from config.settings import settings
from .action_library import StandardActionLibrary, Action, get_action_library
from .template_engine import TemplateEngine
from .eligibility_checker import EligibilityChecker, EligibilityResult
from .volume_calculator import VolumeCalculator, VolumeResult
from .prescription_builder import PrescriptionPlan, PrescriptionPlanItem


@dataclass
class DeepSeekResult:
    """DeepSeek 处方生成结果。"""
    success: bool
    plan: Optional[PrescriptionPlan] = None
    raw_response: Optional[str] = None
    error_message: str = ""
    parse_attempts: int = 0


class DeepSeekPrescription:
    """DeepSeek 处方生成器。

    流程：
    1. 加载模板
    2. 构建上下文（体态评估摘要、FMS摘要、可用动作列表）
    3. 调用 DeepSeek API
    4. 解析 JSON 响应
    5. 验证 action_id 合法性
    6. 应用 VolumeCalculator 覆盖训练量
    7. 返回 PrescriptionPlan

    使用示例：
        service = DeepSeekPrescription()
        result = await service.generate(
            assessment_record=record,
            fms_record=fms_record,
            user_level=2,
        )
        if result.success:
            print(result.plan.plan_name)
    """

    def __init__(
        self,
        library: StandardActionLibrary = None,
        engine: TemplateEngine = None,
        checker: EligibilityChecker = None,
        calculator: VolumeCalculator = None,
    ):
        self.library = library or get_action_library()
        self.engine = engine or TemplateEngine()
        self.checker = checker or EligibilityChecker()
        self.calculator = calculator or VolumeCalculator()

    # ── 摘要构建 ────────────────────────

    def _build_assessment_summary(self, assessment_record) -> str:
        """构建体态评估摘要文本。"""
        parts = []

        # 综合评分
        overall = getattr(assessment_record, "overall_score", None)
        risk = getattr(assessment_record, "risk_level", None)
        if overall is not None:
            parts.append(f"综合评分: {overall:.0f}/100，风险等级: {risk or '未知'}")

        # 各维度分数
        dims = ["balance", "flexibility", "upper_limb", "core", "symmetry"]
        dim_labels = {"balance": "平衡", "flexibility": "柔韧", "upper_limb": "上肢",
                      "core": "核心", "symmetry": "对称"}
        dim_scores = {}
        for dim in dims:
            score = getattr(assessment_record, f"{dim}_score", None)
            if score is not None:
                dim_scores[dim_labels[dim]] = f"{score:.0f}"
        if dim_scores:
            parts.append("各维度: " + ", ".join(f"{k}={v}" for k, v in dim_scores.items()))

        # 体态问题
        posture_data = self._parse_json(getattr(assessment_record, "posture_data", None))
        if isinstance(posture_data, dict):
            problems = posture_data.get("problems", []) or posture_data.get("flags", [])
            if problems:
                prob_texts = []
                name_map = {
                    "head_forward_posture": "头前倾",
                    "shoulder_imbalance": "肩膀不对称",
                    "pelvic_lateral_tilt": "骨盆侧倾",
                    "possible_scoliosis": "疑似脊柱侧弯",
                    "knee_hyperextension": "膝关节超伸",
                    "pelvic_anterior_tilt": "骨盆前倾",
                    "pelvic_posterior_tilt": "骨盆后倾",
                }
                for p in problems:
                    flag = p if isinstance(p, str) else p.get("flag", "")
                    if flag and flag != "possible_scoliosis":
                        prob_texts.append(name_map.get(flag, flag))
                if prob_texts:
                    parts.append("检测到的体态问题: " + ", ".join(prob_texts))

        # 肌肉分析
        muscle = self._parse_json(getattr(assessment_record, "muscle_findings", None))
        if isinstance(muscle, dict):
            tight = muscle.get("tight_muscles", [])
            weak = muscle.get("weak_muscles", [])
            if tight:
                parts.append(f"紧张肌群: {', '.join(tight)}")
            if weak:
                parts.append(f"薄弱肌群: {', '.join(weak)}")

        return "\n".join(parts) if parts else "评估数据不完整"

    def _build_fms_summary(self, fms_record) -> str:
        """构建 FMS 摘要文本。"""
        parts = []
        overall = getattr(fms_record, "overall_score", None)
        risk = getattr(fms_record, "risk_level", None)
        if overall is not None:
            parts.append(f"FMS 综合评分: {overall:.0f}/100，风险等级: {risk or '未知'}")

        dims = ["balance", "flexibility", "upper_limb", "core", "symmetry"]
        dim_labels = {"balance": "平衡", "flexibility": "柔韧", "upper_limb": "上肢",
                      "core": "核心", "symmetry": "对称"}
        scores = {}
        weak = []
        for dim in dims:
            score = getattr(fms_record, f"{dim}_score", None)
            if score is not None:
                scores[dim_labels[dim]] = f"{score:.0f}"
                if score < 60:
                    weak.append(dim_labels[dim])
        if scores:
            parts.append("各维度: " + ", ".join(f"{k}={v}" for k, v in scores.items()))
        if weak:
            parts.append(f"较弱维度: {', '.join(weak)}（低于60分）")
        return "\n".join(parts) if parts else "FMS 数据不完整"

    def _build_eligible_actions_text(
        self,
        fms_scores: Dict[str, Optional[float]],
        problem_ids: List[str],
    ) -> str:
        """构建可用动作列表文本（供 DeepSeek 选择）。"""
        # 获取与问题相关的动作
        relevant = self.library.get_by_problem(problem_ids, min_relevance=0.2, max_results=40)

        lines = []
        for action in relevant:
            result = self.checker.check(action, fms_scores)
            if result.risk_level == "unsafe":
                continue

            match_score = sum(action.problem_mapping.get(pid, 0) for pid in problem_ids)

            sets = action.default_sets
            reps = action.default_reps
            dur = action.default_duration_seconds

            line = (
                f"  - id={action.id} | name={action.name} | family={action.family_name} | "
                f"category={action.category} | difficulty={action.difficulty}/5 | "
                f"intensity={action.intensity} | phases={','.join(action.phases)} | "
                f"target={','.join(action.target_body_parts)} | "
                f"problem_match={match_score:.2f} | risk={result.risk_level}"
            )
            if reps > 0:
                line += f" | recommend={sets}sets x {reps}reps"
            else:
                line += f" | recommend={sets}sets x {dur}s"
            if result.failing_dimensions:
                line += f" | caution_dims={' '.join(result.failing_dimensions)}"
            if action.is_regression_of:
                reg = self.library.get_by_id(action.is_regression_of)
                if reg:
                    line += f" | regression_of={reg.name}"
            lines.append(line)

        return "\n".join(lines) if lines else "（没有符合条件的动作）"

    def _build_action_reference(self) -> str:
        """构建动作库完整参考（精简版，供 AI 寻找替代动作）。"""
        lines = []
        for action in self.library.get_all():
            lines.append(
                f"  id={action.id} | {action.name} | {action.family_name} | "
                f"diff={action.difficulty} | {action.intensity} | {action.category}"
            )
        return "\n".join(lines)

    # ── API 调用 ────────────────────────

    async def _call_deepseek(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """调用 DeepSeek API。

        Returns:
            原始响应文本

        Raises:
            RuntimeError: API 调用失败
            ValueError: API Key 未配置
        """
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DeepSeek API Key 未配置")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,  # 低温度保证格式一致性
                    "max_tokens": 4096,
                },
            )

            if response.status_code != 200:
                error_detail = response.text[:1000]
                raise RuntimeError(
                    f"DeepSeek API 调用失败 (HTTP {response.status_code}): {error_detail}"
                )

            data = response.json()
            msg = data["choices"][0]["message"]
            content = msg.get("content", "")

            # deepseek-v4-pro 思维链模型可能把内容放在 reasoning_content 中
            if not content and msg.get("reasoning_content"):
                content = msg["reasoning_content"]

            if not content:
                raise RuntimeError(
                    f"DeepSeek 返回空内容，原始响应: {json.dumps(data, ensure_ascii=False)[:500]}"
                )

            return content

    # ── 响应解析 ────────────────────────

    def _parse_json_response(self, content: str) -> Dict:
        """从 DeepSeek 响应中提取 JSON。

        Attempts:
        1. 直接 json.loads
        2. 正则提取第一个 { 到最后一个 } 之间
        3. 去掉 Markdown ```json``` 标记后重试
        """
        content = content.strip()

        # 尝试 1: 直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试 2: 去掉 Markdown 代码块
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

        # 尝试 3: 正则提取
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从响应中解析JSON，原始内容: {content[:500]}...")

    def _validate_and_build_plan(
        self,
        data: Dict,
        fms_scores: Dict[str, Optional[float]],
        user_level: int,
        assessment_record_id: Optional[int] = None,
        fms_record_id: Optional[int] = None,
    ) -> PrescriptionPlan:
        """验证 DeepSeek 返回的 JSON 并构建 PrescriptionPlan。

        - 验证 action_id 存在于动作库
        - 验证 phase 合法
        - 用 VolumeCalculator 覆盖训练量
        """
        phases_data = data.get("phases", {})
        valid_phases = ["warmup", "main", "cooldown"]

        plan_phases = {}
        all_items = []

        for phase_name in valid_phases:
            items_data = phases_data.get(phase_name, [])
            phase_items = []

            for item_data in items_data:
                action_id = item_data.get("action_id", "")
                action = self.library.get_by_id(action_id)

                if action is None:
                    # 动作不存在，跳过
                    continue

                # 检查可行性
                elig_result = self.checker.check(action, fms_scores)
                if elig_result.risk_level == "unsafe":
                    continue

                # 用 VolumeCalculator 计算安全训练量（覆盖 AI 的值）
                vol = self.calculator.calculate(action, fms_scores, user_level)

                plan_item = PrescriptionPlanItem(
                    action_id=action.id,
                    action_name=action.name,
                    family_name=action.family_name,
                    category=action.category,
                    phase=phase_name,
                    sets=vol.sets,
                    reps=vol.reps,
                    duration_seconds=vol.duration_seconds,
                    order_index=len(phase_items),
                    difficulty=action.difficulty,
                    intensity=action.intensity,
                    notes=item_data.get("notes", vol.notes),
                    steps=action.steps,
                    cues=action.cues,
                    display_type=action.display_type,
                    display_url=action.display_url,
                )
                phase_items.append(plan_item)
                all_items.append(plan_item)

            plan_phases[phase_name] = phase_items

        # 计算总量
        total_sets = sum(item.sets for item in all_items)
        total_reps = sum(item.sets * item.reps for item in all_items)
        total_dur = sum(item.sets * item.duration_seconds for item in all_items)

        plan = PrescriptionPlan(
            plan_name=data.get("plan_name", "AI生成训练计划"),
            overall_strategy=data.get("overall_strategy", ""),
            generation_method="deepseek",
            assessment_record_id=assessment_record_id,
            fms_record_id=fms_record_id,
            phases=plan_phases,
            total_volume={
                "total_actions": len(all_items),
                "total_sets": total_sets,
                "total_reps": total_reps,
                "total_duration_minutes": round(total_dur / 60, 1),
            },
        )

        return plan

    # ── 主入口 ────────────────────────

    async def generate(
        self,
        assessment_record,
        fms_record,
        user_level: int = 1,
    ) -> DeepSeekResult:
        """生成训练处方。

        Args:
            assessment_record: AssessmentRecord ORM 对象
            fms_record: FMSRecord ORM 对象
            user_level: 用户训练水平 1-5

        Returns:
            DeepSeekResult
        """
        # 1. 提取问题
        posture_data = self._parse_json(
            getattr(assessment_record, "posture_data", None)
        )
        problem_ids = []
        if isinstance(posture_data, dict):
            flags = posture_data.get("flags", [])
            for f in flags:
                flag = f if isinstance(f, str) else f.get("flag", "")
                if flag and flag != "possible_scoliosis":
                    problem_ids.append(flag)

        # 2. FMS 分数
        fms_scores = {
            "balance_score": getattr(fms_record, "balance_score", None),
            "flexibility_score": getattr(fms_record, "flexibility_score", None),
            "core_score": getattr(fms_record, "core_score", None),
            "upper_limb_score": getattr(fms_record, "upper_limb_score", None),
            "symmetry_score": getattr(fms_record, "symmetry_score", None),
        }

        # 3. 构建上下文
        context = {
            "user_level": user_level,
            "assessment_summary": self._build_assessment_summary(assessment_record),
            "fms_summary": self._build_fms_summary(fms_record),
            "eligible_actions": self._build_eligible_actions_text(fms_scores, problem_ids),
            "action_library_reference": self._build_action_reference(),
        }

        # 4. 渲染模板
        system_prompt = self.engine.get_system_prompt()
        user_prompt = self.engine.render_prescription_prompt(context)

        # 5. 调用 DeepSeek
        try:
            raw_response = await self._call_deepseek(system_prompt, user_prompt)

            # 6. 解析并验证
            data = self._parse_json_response(raw_response)
            plan = self._validate_and_build_plan(
                data,
                fms_scores,
                user_level,
                assessment_record_id=getattr(assessment_record, "id", None),
                fms_record_id=getattr(fms_record, "id", None),
            )

            return DeepSeekResult(
                success=True,
                plan=plan,
                raw_response=raw_response,
            )

        except (ValueError, RuntimeError, httpx.TimeoutException) as e:
            return DeepSeekResult(
                success=False,
                error_message=str(e),
            )

    # ── 工具方法 ────────────────────────

    @staticmethod
    def _parse_json(value, default=None):
        """安全解析 JSON 字段。"""
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
