"""
DeepSeek 处方生成服务。

调用 DeepSeek API，将体态评估 + FMS 数据 + 动作库 输入模型，
生成结构化 JSON 处方计划，解析并验证后返回。
"""
import asyncio
import json
import logging
import re
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from config.settings import settings
from .action_library import StandardActionLibrary, Action, get_action_library
from .template_engine import TemplateEngine
from .eligibility_checker import EligibilityChecker, EligibilityResult
from .volume_calculator import VolumeCalculator, VolumeResult
from .prescription_builder import PrescriptionPlan, PrescriptionPlanItem, SkippedItem


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
    6. 融合 AI 训练量建议与 VolumeCalculator 安全边界
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
                tight_names = [m.get('name', str(m)) if isinstance(m, dict) else str(m) for m in tight]
                parts.append(f"紧张肌群: {', '.join(tight_names)}")
            if weak:
                weak_names = [m.get('name', str(m)) if isinstance(m, dict) else str(m) for m in weak]
                parts.append(f"薄弱肌群: {', '.join(weak_names)}")

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
        user_level: int = 1,
        hidden_names: set = None,
    ) -> str:
        """构建可用动作列表文本（供 DeepSeek 选择）。

        Args:
            fms_scores: FMS 各维度分数
            problem_ids: 体态问题 ID 列表
            user_level: 用户训练水平 1-5，用于按难度过滤动作
            hidden_names: 被隐藏的动作名称集合
        """
        hidden_names = hidden_names or set()
        # 根据用户训练水平确定最大允许动作难度
        USER_LEVEL_MAX_DIFFICULTY = {1: 2, 2: 3, 3: 4, 4: 5, 5: 5}
        max_difficulty = USER_LEVEL_MAX_DIFFICULTY.get(user_level, 5)

        # 获取与问题相关的动作
        relevant = self.library.get_by_problem(problem_ids, min_relevance=0.2, max_results=40)

        lines = []
        for action in relevant:
            # 排除隐藏动作
            if action.name in hidden_names:
                continue
            # ★ 按用户训练水平过滤动作难度
            if action.difficulty > max_difficulty:
                continue

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

    def _build_action_reference(self, hidden_names: set = None) -> str:
        """构建动作库完整参考（精简版，供 AI 寻找替代动作，排除隐藏动作）。"""
        hidden_names = hidden_names or set()
        lines = []
        for action in self.library.get_all():
            if action.name in hidden_names:
                continue
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

        last_error = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
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
                            "temperature": 0.3,
                            "max_tokens": 8192,
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
                reasoning = msg.get("reasoning_content", "")

                # deepseek-reasoner 等思维链模型：content 可能为空但 reasoning_content 有内容
                # 注意：reasoning_content 是模型的内部推理过程，不是最终答案
                # 如果 content 为空，尝试从 reasoning_content 末尾提取可能的最终输出
                if not content and reasoning:
                    # reasoning 的最后一段可能是最终答案，尝试提取
                    # 但不应直接使用 reasoning 作为处方 JSON
                    logger.warning(
                        "DeepSeek 返回空 content，仅有 reasoning_content（长度=%d），"
                        "尝试从推理过程提取最终输出",
                        len(reasoning),
                    )
                    # 尝试从 reasoning 中查找 JSON 块
                    json_match = re.search(r'\{[^{}]*"plan_name"[^{}]*\}', reasoning, re.DOTALL)
                    if json_match:
                        # 扩展匹配范围以获取完整 JSON
                        start = json_match.start()
                        # 从 start 往前找到最后一个完整 JSON 开始位置
                        brace_count = 0
                        json_start = start
                        for i in range(start, len(reasoning)):
                            if reasoning[i] == '{':
                                brace_count += 1
                            elif reasoning[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    content = reasoning[json_start:i+1]
                                    break
                    if not content:
                        # 最后手段：尝试使用 reasoning 的最后一段（可能包含有效信息）
                        content = reasoning

                if not content:
                    raise RuntimeError(
                        f"DeepSeek 返回空内容，原始响应: {json.dumps(data, ensure_ascii=False)[:500]}"
                    )

                return content

            except (httpx.TimeoutException, httpx.ConnectError,
                    httpx.RemoteProtocolError, httpx.ReadError,
                    httpx.WriteError, httpx.NetworkError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(f"DeepSeek API 请求失败 (已重试 {max_retries} 次): {e}")

        raise RuntimeError(f"DeepSeek API 请求失败: {last_error}")

    # ── 响应解析 ────────────────────────

    def _parse_json_response(self, content: str) -> Dict:
        """从 DeepSeek 响应中提取 JSON。

        Attempts:
        1. 直接 json.loads
        2. 去掉 Markdown ```json``` 标记后重试
        3. 正则提取第一个 { 开始、配对的 } 结束的 JSON 块
        4. 如果 JSON 被截断，尝试修复后解析
        """
        content = content.strip()
        last_error = None

        # 尝试 1: 直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            last_error = e

        # 尝试 2: 去掉 Markdown 代码块
        cleaned = content
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                last_error = e

        # 尝试 3: 从 content 中提取第一个 { 到配对的 } —— 比 .* 贪婪匹配更准确
        # 找第一个 {
        start_idx = content.find("{")
        if start_idx >= 0:
            # 手动配对括号，找到匹配的 }
            brace_count = 0
            end_idx = -1
            for i in range(start_idx, len(content)):
                ch = content[i]
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break

            if end_idx > start_idx:
                json_str = content[start_idx:end_idx + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    last_error = e
            else:
                # 括号不配对 — JSON 被截断了
                logger.warning(
                    "DeepSeek 返回的 JSON 括号不配对（起始位置=%d，未找到配对的 }），"
                    "max_tokens 可能不够，响应被截断。响应长度=%d，最后200字符: %s",
                    start_idx, len(content), content[-200:],
                )
                # 尝试在末尾补 } 修复截断的 JSON
                truncated = content[start_idx:]
                missing = truncated.count("{") - truncated.count("}")
                if missing > 0:
                    repaired = truncated + ("}" * missing)
                    try:
                        logger.info("尝试修复截断的 JSON：补充了 %d 个 }", missing)
                        return json.loads(repaired)
                    except json.JSONDecodeError as e:
                        last_error = e

        # 如果以上都失败，尝试对 cleaned 文本做配对提取
        if cleaned != content:
            start_idx = cleaned.find("{")
            if start_idx >= 0:
                brace_count = 0
                end_idx = -1
                for i in range(start_idx, len(cleaned)):
                    if cleaned[i] == "{":
                        brace_count += 1
                    elif cleaned[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                if end_idx > start_idx:
                    try:
                        return json.loads(cleaned[start_idx:end_idx + 1])
                    except json.JSONDecodeError as e:
                        last_error = e

        # 所有尝试失败，给出详细错误信息
        raise ValueError(
            f"无法从响应中解析JSON。"
            f"响应长度={len(content)}，"
            f"JSON错误={last_error}，"
            f"响应开头: {content[:300]}，"
            f"响应结尾: {content[-200:]}"
        )

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
        - 验证 phase 合法性
        - 按用户训练水平校验动作难度上限
        - 用 VolumeCalculator 覆盖训练量（组数/次数/时长由计算器决定，不由 AI）
        """
        phases_data = data.get("phases", {})
        valid_phases = ["warmup", "main", "cooldown"]

        # 根据用户训练水平确定最大允许动作难度（与服务端过滤保持一致）
        USER_LEVEL_MAX_DIFFICULTY = {1: 2, 2: 3, 3: 4, 4: 5, 5: 5}
        max_difficulty = USER_LEVEL_MAX_DIFFICULTY.get(user_level, 5)

        plan_phases = {}
        all_items = []
        skipped_items = []  # 收集被过滤掉的动作及原因

        for phase_name in valid_phases:
            items_data = phases_data.get(phase_name, [])
            phase_items = []

            for item_data in items_data:
                action_id = item_data.get("action_id", "")
                action = self.library.get_by_id(action_id)

                if action is None:
                    # 动作不存在 — AI 可能编造了不在动作库中的 ID
                    ai_name = item_data.get("action_name", "") or item_data.get("name", "")
                    skipped_items.append(SkippedItem(
                        action_id=action_id,
                        action_name=ai_name,
                        phase=phase_name,
                        reason="unknown_action",
                        detail=f"AI 返回的动作 '{action_id}' 不在标准动作库中，可能为编造",
                    ))
                    logger.warning(
                        "DeepSeek 返回了未知 action_id='%s'（phase=%s），已跳过。"
                        "AI 可能编造了不在动作库中的动作。",
                        action_id, phase_name,
                    )
                    continue

                # 检查可行性
                elig_result = self.checker.check(action, fms_scores)
                if elig_result.risk_level == "unsafe":
                    skipped_items.append(SkippedItem(
                        action_id=action.id,
                        action_name=action.name,
                        phase=phase_name,
                        reason="fms_contraindication",
                        detail=f"FMS 禁忌：{'；'.join(elig_result.reasons)}",
                    ))
                    logger.info(
                        "动作 '%s'（id=%s）因 FMS 禁忌被跳过（risk=%s，failing=%s）",
                        action.name, action_id, elig_result.risk_level,
                        elig_result.failing_dimensions,
                    )
                    continue

                # ★ 按用户训练水平校验动作难度上限
                if action.difficulty > max_difficulty:
                    skipped_items.append(SkippedItem(
                        action_id=action.id,
                        action_name=action.name,
                        phase=phase_name,
                        reason="difficulty_exceeded",
                        detail=f"动作难度 {action.difficulty}/5 超过用户训练水平上限 {max_difficulty}/5",
                    ))
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
                    order_index=len(phase_items) + 1,
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

        # 检查是否有任何有效动作被选入计划
        if len(all_items) == 0:
            raise ValueError(
                f"DeepSeek 返回的处方计划中没有有效动作。"
                f"原始 phases 数据: {json.dumps(phases_data, ensure_ascii=False)[:500]}"
            )

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
            skipped_items=skipped_items,
        )

        return plan

    # ── 主入口 ────────────────────────

    async def generate(
        self,
        assessment_record,
        fms_record,
        user_level: int = 1,
        hidden_names: set = None,
        training_goal: str = 'comprehensive',
        training_duration: int = 30,
        training_frequency: int = 3,
    ) -> DeepSeekResult:
        """生成训练处方。

        Args:
            assessment_record: AssessmentRecord ORM 对象
            fms_record: FMSRecord ORM 对象
            user_level: 用户训练水平 1-5
            hidden_names: 被隐藏的动作名称集合
            training_goal: 训练目标
            training_duration: 单次时长（分钟）
            training_frequency: 每周频率

        Returns:
            DeepSeekResult
        """
        hidden_names = hidden_names or set()
        # 1. 提取问题
        posture_data = self._parse_json(
            getattr(assessment_record, "posture_data", None)
        )
        problem_ids = []
        if isinstance(posture_data, dict):
            # 兼容两种格式：{"flags": [...]} 和 {"problems": [{"flag": "..."}, ...]}
            flags = posture_data.get("flags", [])
            if not flags:
                # 如果 flags 为空，尝试从 problems 列表提取
                problems_list = posture_data.get("problems", [])
                flags = [
                    p.get("flag", "") if isinstance(p, dict) else p
                    for p in problems_list
                ]
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

        # API Key 提前检查，避免构建大量上下文后才发现未配置
        if not settings.DEEPSEEK_API_KEY:
            return DeepSeekResult(
                success=False,
                error_message="DeepSeek API Key 未配置，请在 .env 文件中设置 DEEPSEEK_API_KEY",
            )

        # 3. 构建上下文（排除隐藏动作）
        goal_labels = {'comprehensive': '综合提升', 'posture': '体态矫正', 'strength': '力量增强', 'flexibility': '柔韧恢复', 'fatloss': '减脂塑形'}
        context = {
            "user_level": user_level,
            "training_goal": goal_labels.get(training_goal, '综合提升'),
            "training_duration": training_duration,
            "training_frequency": training_frequency,
            "assessment_summary": self._build_assessment_summary(assessment_record),
            "fms_summary": self._build_fms_summary(fms_record),
            "eligible_actions": self._build_eligible_actions_text(fms_scores, problem_ids, user_level, hidden_names),
            "action_library_reference": self._build_action_reference(hidden_names),
        }

        # 4. 渲染模板（system prompt 也传入 user_level，使 AI 明确当前用户等级）
        system_prompt = self.engine.get_system_prompt({"user_level": user_level})
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
