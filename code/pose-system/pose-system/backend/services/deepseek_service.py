"""
DeepSeek AI 体态评估报告生成服务。

通过 DeepSeek Chat API 将体态评估原始数据转化为自然语言专业报告。
"""
import json
import httpx
from config.settings import settings


def _build_prompt(assessment: dict) -> str:
    """根据体态评估数据构造提示词。"""
    scores = {
        "平衡": assessment.get("balance_score"),
        "柔韧性": assessment.get("flexibility_score"),
        "上肢": assessment.get("upper_limb_score"),
        "核心": assessment.get("core_score"),
        "对称性": assessment.get("symmetry_score"),
    }
    overall = assessment.get("overall_score", 0)
    risk = assessment.get("risk_level", "未知")

    # 解析 JSON 字段
    posture_problems = _parse_json(assessment.get("posture_data"), [])
    muscle_findings = _parse_json(assessment.get("muscle_findings"), {})
    rom_analysis = _parse_json(assessment.get("rom_data"), [])
    asymmetry = _parse_json(assessment.get("movement_data"), [])

    prompt = f"""你是一位资深的运动康复与体态纠正专家。请根据以下体态评估数据，撰写一份专业、详尽的中文体态评估分析报告。

## 评估综合结果
- 综合评分：{overall}/100
- 风险等级：{risk}
- 各维度评分：{json.dumps(scores, ensure_ascii=False)}

## 体态问题发现
{json.dumps(posture_problems, ensure_ascii=False) if posture_problems else "未发现明显体态问题"}

## 肌肉分析
{json.dumps(muscle_findings, ensure_ascii=False) if muscle_findings else "暂无肌肉分析数据"}

## 关节活动度分析
{json.dumps(rom_analysis, ensure_ascii=False) if rom_analysis else "暂无ROM数据"}

## 不对称性分析
{json.dumps(asymmetry, ensure_ascii=False) if asymmetry else "暂无不对称数据"}

## 报告要求
请按以下结构撰写报告，用中文输出（约800-1200字）：

### 1. 总体评估
用一段话概括该用户的体态状况，说明整体风险等级和需要关注的核心问题。

### 2. 各维度详细分析
针对平衡、柔韧性、上肢、核心、对称性五个维度，逐一分析：
- 当前得分反映的问题
- 可能的原因（结合肌肉紧张/薄弱情况）
- 对日常活动和运动表现的影响

### 3. 体态问题解读
基于体态问题发现数据，用通俗语言解释每个问题的含义、成因和潜在风险。

### 4. 改善建议
针对发现的主要问题，给出具体的、可操作的改善建议，包括：
- 推荐优先纠正的问题及顺序
- 日常注意事项（坐姿、站姿、运动习惯）
- 预期改善周期的大致时间框架

### 5. 总结
一段激励性的总结，鼓励用户坚持训练。

请确保报告专业但易懂，避免过于学术化的术语，让普通健身爱好者也能理解。"""

    return prompt


def _parse_json(value, default):
    """安全解析 JSON 字段。"""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


async def generate_assessment_report(assessment: dict) -> str:
    """调用 DeepSeek API 生成体态评估报告。

    Args:
        assessment: 评估记录字典（含 scores, posture_data, muscle_findings 等字段）

    Returns:
        AI 生成的报告文本（markdown 格式）
    """
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API Key 未配置，请在环境变量中设置 DEEPSEEK_API_KEY")

    prompt = _build_prompt(assessment)

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
                    {
                        "role": "system",
                        "content": "你是一位资深的运动康复与体态纠正专家，擅长将体态评估数据转化为专业、易懂的分析报告。请用中文回复。",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 4096,
            },
        )

        if response.status_code != 200:
            error_detail = response.text[:1000]
            raise RuntimeError(f"DeepSeek API 调用失败 (HTTP {response.status_code}): {error_detail}")

        data = response.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")

        # deepseek-reasoner 等思维链模型：最终答案应在 content 中
        # reasoning_content 是模型的内部推理过程，不应直接作为输出
        if not content and reasoning:
            import logging
            _log = logging.getLogger(__name__)
            _log.warning(
                "DeepSeek 返回空 content，仅有 reasoning_content（长度=%d），"
                "尝试从推理过程末尾提取最终答案",
                len(reasoning),
            )
            # 尝试从 reasoning 末尾提取看起来像报告的内容（最后一段通常是总结/最终输出）
            # 找到最后一个明显的分段标记后的内容
            for separator in ["\n\n##", "\n\n###", "\n\n---", "\n\n**总结**", "\n\n总体"]:
                idx = reasoning.rfind(separator)
                if idx > len(reasoning) // 2:
                    content = reasoning[idx:].strip()
                    break
            if not content:
                content = reasoning  # 最后手段

        if not content:
            raise RuntimeError(f"DeepSeek 返回空内容，原始响应: {json.dumps(data, ensure_ascii=False)[:500]}")
        return content
