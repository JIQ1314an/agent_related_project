text_to_sql/
│── chinook.db          # 下载的数据库文件
│── config.py            # 存放 API 密钥和基础配置
│── main.py             # 主运行程序（测试 8 个用例）
└── sql_generator.py    # 核心逻辑：Schema 提取 -> LLM 交互 -> SQL 执行