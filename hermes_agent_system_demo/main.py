import os
import sys
from config import config
from logger import logger, log_step
from core.llm_client import QwenLLMClient
from skills.skill_manager import SkillManager
from core.agent_engine import HermesAgentEngine

def main():
    print("""
    ============================================================
    * Enterprise Hermes Agent & Dynamic Skill Runtime System *
    * Driven by Alibaba Qwen3.7-Plus Model (Refactored & Fixed)*
    ============================================================
    """)

    llm_client = QwenLLMClient()
    skill_manager = SkillManager(custom_skills_dir=config.SKILLS_DIR)
    agent_engine = HermesAgentEngine(llm_client=llm_client, skill_manager=skill_manager)

    initial_skills = skill_manager.skills.keys()
    log_step("Main Check", f"当前系统拥有的初始化 Skill 列表: {list(initial_skills)}")

    # 体验 Hermes /learn 机制：从文档学习新 Skill
    doc_path = os.path.join(os.path.dirname(__file__), "docs", "mock_server_api.md")
    print("\n>>> 开始演示 Hermes /learn 功能：从 OpenAPI/Markdown 文档构建 Skill...")
    
    learn_success = skill_manager.learn_from_doc(doc_path=doc_path, llm_client=llm_client)
    
    if learn_success:
        log_step("Main Check", f"学习完成！最新 Skill 列表: {list(skill_manager.skills.keys())}")
    else:
        logger.error("学习失败，终止后续演示！")
        sys.exit(1)

    # 运行 Agent 执行实际运维查询任务
    user_query = "请帮我检查服务器 'srv-bj-001' 的运行状态和资源使用情况，如果有异常请指出。"
    
    print(f"\n>>> 启动 Hermes Agent 执行任务: '{user_query}'\n")
    final_output = agent_engine.run(user_query=user_query)

    print("\n==================== 最终回答结果 ====================")
    print(final_output)
    print("======================================================")

if __name__ == "__main__":
    main()