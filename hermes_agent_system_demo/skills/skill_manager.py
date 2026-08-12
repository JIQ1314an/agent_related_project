import os
import sys
import re
import importlib
import importlib.util
from typing import Dict, List, Any
from skills.base_skill import BaseSkill
from logger import logger, log_step, log_error

class SkillManager:
    """Skill 管理器：支持热重载、安全性校验与防转义 Prompt 构建"""

    def __init__(self, custom_skills_dir: str):
        self.custom_skills_dir = custom_skills_dir
        self.skills: Dict[str, BaseSkill] = {}
        os.makedirs(self.custom_skills_dir, exist_ok=True)
        self.load_all_skills()

    def register_skill(self, skill: BaseSkill):
        """注册一个 Skill 实例"""
        self.skills[skill.name] = skill
        log_step("SkillManager.register_skill", f"成功注册技能: {skill.name}")

    def load_all_skills(self):
        """动态扫描、重新加载或热更新 custom_skills 目录下的所有 Python 模块"""
        log_step("SkillManager.load_all_skills", f"开始扫描并刷新 Skill 目录: {self.custom_skills_dir}")
        for file_name in os.listdir(self.custom_skills_dir):
            if file_name.endswith(".py") and not file_name.startswith("__"):
                module_name = file_name[:-3]
                file_path = os.path.join(self.custom_skills_dir, file_name)
                
                try:
                    # 修复：处理热重载（Reload）逻辑，避免内存缓存旧代码
                    if module_name in sys.modules:
                        module = importlib.reload(sys.modules[module_name])
                    else:
                        spec = importlib.util.spec_from_file_location(module_name, file_path)
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                    # 寻找模块中继承自 BaseSkill 的子类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                            skill_instance = attr()
                            self.register_skill(skill_instance)
                except Exception as e:
                    log_error("SkillManager.load_all_skills", f"加载技能文件 {file_name} 失败: {str(e)}")

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有 Skill 的 JSON Schema"""
        return [skill.to_schema() for skill in self.skills.values()]

    def execute_skill(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """代理执行指定的 Skill"""
        if name not in self.skills:
            error_msg = f"未找到名为 [{name}] 的技能"
            log_error("SkillManager.execute_skill", error_msg)
            return {"status": "error", "message": error_msg}
        
        log_step("SkillManager.execute_skill", f"正在执行技能: {name}\n参数: {params}")
        try:
            result = self.skills[name].execute(**params)
            log_step("SkillManager.execute_skill_result", f"技能 [{name}] 返回值:\n{result}")
            return result
        except Exception as e:
            err_str = f"技能 [{name}] 在执行过程中发生未捕获异常: {str(e)}"
            log_error("SkillManager.execute_skill", err_str)
            return {"status": "error", "message": err_str}

    def learn_from_doc(self, doc_path: str, llm_client) -> bool:
        """从 API 文档解析并生成 Skill Python 代码"""
        log_step("Hermes /learn", f"正在读取文档: {doc_path}")
        if not os.path.exists(doc_path):
            log_error("Hermes /learn", f"文档路径不存在: {doc_path}")
            return False

        with open(doc_path, 'r', encoding='utf-8') as f:
            doc_content = f.read()

        # 修复：避免使用 f-string 拼接包含 JSON/花括号的 Markdown 文档
        prompt_template = """你是一个精通 Agent Skill 开发的资深架构师。请阅读以下 API 文档，并生成符合规范的 Python 代码。文档内容:```markdown{doc_content}```

【严格的要求】：
1. 必须继承 `skills.base_skill.BaseSkill`。
2. 类名使用驼峰命名（如 `DynamicGeneratedSkill`）。
3. 必须实现 `name`, `description`, `parameters`, `execute` 四个属性/方法。
4. `execute` 方法必须包含 `**kwargs` 允许弹性入参，并返回包含 status 的 dict。
5. **只输出纯 Python 代码**，包裹在 `python` 代码块中。
"""
        prompt = prompt_template.replace("{doc_content}", doc_content)

        log_step("Hermes /learn LLM Task", "正在请求 Qwen3.7-Plus 编译文档为 Skill 源码...")
        response_text = llm_client.one_shot_chat(prompt)

        # 修复：使用正则安全抽取代码块
        try:
            match = re.search(r"```(?:python)?\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                code = match.group(1).strip()
            else:
                code = response_text.strip()

            skill_filename = "generated_learned_skill.py"
            save_path = os.path.join(self.custom_skills_dir, skill_filename)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(code)

            log_step("Hermes /learn Save", f"代码已持久化至: {save_path}\n代码预览:\n{code[:300]}...")

            # 重新加载模块
            self.load_all_skills()
            return True
        except Exception as e:
            log_error("Hermes /learn Parse", f"代码解析与落盘失败: {str(e)}")
            return False