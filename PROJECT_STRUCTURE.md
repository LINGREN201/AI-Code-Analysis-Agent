# 项目结构说明

## 目录结构

```
agent_test/
├── app/                          # 应用主目录
│   ├── __init__.py              # 应用包初始化
│   ├── main.py                  # FastAPI 应用入口
│   ├── api/                     # API 路由模块
│   │   ├── __init__.py
│   │   └── routes/              # 路由定义
│   │       ├── __init__.py
│   │       ├── analyze.py       # 代码分析路由
│   │       └── generate_tests.py # 测试生成路由
│   ├── core/                    # 核心配置模块
│   │   ├── __init__.py
│   │   └── config.py           # 应用配置（环境变量、设置）
│   ├── services/                # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── code_analyzer.py    # 代码分析服务
│   │   ├── ai_analyzer.py      # AI 分析服务
│   │   ├── test_generator.py   # 测试生成服务
│   │   └── test_executor_functions.py # 测试执行函数
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       └── response_formatter.py # 响应格式化工具
├── tests/                        # 测试目录
├── main.py                       # 应用启动入口（可选）
├── requirements.txt              # Python 依赖
├── Dockerfile                    # Docker 镜像构建文件
├── docker-compose.yml           # Docker Compose 配置
├── .dockerignore                # Docker 忽略文件
├── README.md                    # 项目主文档
├── ARCHITECTURE.md              # 架构设计文档
├── USAGE.md                     # 使用指南
├── DOCKER.md                    # Docker 部署指南
└── PROJECT_STRUCTURE.md         # 项目结构说明（本文件）
```

## 模块说明

### app/main.py
FastAPI 应用主文件，负责：
- 创建 FastAPI 应用实例
- 配置中间件（CORS）
- 注册路由
- 定义根路径和健康检查端点

### app/core/config.py
应用配置模块，使用 Pydantic Settings：
- 管理环境变量
- 提供配置默认值
- 统一配置访问接口

### app/api/routes/
API 路由模块：
- `analyze.py`: `/analyze` 端点，代码分析和功能定位
- `generate_tests.py`: `/generate-tests` 端点，动态测试生成和执行

### app/services/
业务逻辑服务层：
- `code_analyzer.py`: ZIP 提取、代码结构分析、AST 解析
- `ai_analyzer.py`: LLM API 调用、功能分析、执行计划生成
- `test_generator.py`: LLM Function Calling、测试生成和执行
- `test_executor_functions.py`: LLM 可调用的执行函数定义

### app/utils/
工具函数模块：
- `response_formatter.py`: JSON 响应格式化、错误处理

## 设计原则

1. **分层架构**: API → Services → Utils，职责清晰
2. **配置集中管理**: 所有配置通过 `app/core/config.py` 访问
3. **模块化设计**: 每个模块独立，易于测试和维护
4. **标准 FastAPI 结构**: 遵循 FastAPI 最佳实践

## 启动方式

### 本地运行
```bash
uvicorn app.main:app --reload
```

### Docker 运行
```bash
docker build -t ai-code-analysis-agent .
docker run -p 8000:8000 ai-code-analysis-agent
```

### Docker Compose
```bash
docker-compose up -d
```
