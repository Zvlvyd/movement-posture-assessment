"""
提示词模板引擎。

加载 templates/ 目录下的模板文件，进行简单的 {{ placeholder }} 替换。
不引入 Jinja2 等外部依赖，使用内置字符串替换。
"""
import os
import re
from typing import Dict, Any


class TemplateEngine:
    """简单模板引擎。

    支持：
    - 变量替换: {{ variable_name }}
    - 从 templates/ 目录加载 .txt 模板文件
    - 缓存已加载的模板

    使用示例：
        engine = TemplateEngine()
        prompt = engine.render("prescription_plan.txt", {"user_level": 3, ...})
    """

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.template_dir = template_dir
        self._cache: Dict[str, str] = {}

    def load(self, template_name: str) -> str:
        """加载模板文件。

        Args:
            template_name: 模板文件名，如 "system.txt"

        Returns:
            模板内容字符串
        """
        if template_name in self._cache:
            return self._cache[template_name]

        file_path = os.path.join(self.template_dir, template_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"模板文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        self._cache[template_name] = content
        return content

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """加载模板并替换变量。

        Args:
            template_name: 模板文件名
            context: 变量字典，如 {'user_level': 3}

        Returns:
            渲染后的字符串
        """
        template = self.load(template_name)

        def replace_var(match):
            var_name = match.group(1).strip()
            value = context.get(var_name, "")
            if value is None:
                return ""
            if isinstance(value, (list, dict)):
                import json
                return json.dumps(value, ensure_ascii=False, indent=2)
            return str(value)

        result = re.sub(r"\{\{\s*(\w+)\s*\}\}", replace_var, template)
        return result

    def render_prescription_prompt(self, context: Dict[str, Any]) -> str:
        """渲染处方生成提示词（user message）。

        Args:
            context: 必须包含:
                - user_level: int
                - assessment_summary: str
                - fms_summary: str
                - eligible_actions: str
                - action_library_reference: str

        Returns:
            渲染后的完整提示词
        """
        return self.render("prescription_plan.txt", context)

    def get_system_prompt(self) -> str:
        """获取系统提示词。"""
        return self.load("system.txt")

    def clear_cache(self):
        """清空模板缓存（调试用）。"""
        self._cache.clear()
