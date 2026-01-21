# 架构设计文档

## 项目概述

AI Code Analysis Agent 是一个基于 FastAPI 的智能代码分析服务，能够：
- 分析代码库结构并定位功能实现
- 使用 LLM Function Calling 动态生成和执行测试代码
- 生成结构化的功能分析报告

## 系统架构

```
┌─────────────────────┐
│   FastAPI App       │
│  (app/main.py)      │
└──────────┬──────────┘
           │
      ┌────┴────┐
      │         │
┌─────▼─────┐ ┌▼──────────────┐
│ /analyze  │ │/generate-tests │
│ (routes)  │ │ (routes)       │
└─────┬─────┘ └┬───────────────┘
      │        │
      │        │
┌─────▼────────▼──────────────┐
│   CodeAnalyzer              │
│  (services/)                │
│  - Extract ZIP              │
│  - Parse Structure           │
│  - AST Analysis             │
└─────┬───────────────────────┘
      │
┌─────▼─────────────────────┐
│   AIAnalyzer                │
│  (services/)                │
│  - OpenAI/Qwen API          │
│  - Feature Analysis          │
│  - Execution Plan            │
└─────┬───────────────────────┘
      │
┌─────▼───────────────────────┐
│   TestGenerator            │
│  (services/)               │
│  - LLM Function Call        │
│  - Test Execution           │
└─────┬───────────────────────┘
      │
┌─────▼───────────────────────┐
│ TestExecutorFunctions       │
│  (services/)               │
│  - execute_code            │
│  - run_command             │
│  - check_api_endpoint      │
└────────────────────────────┘
```

## 核心模块

### 1. app/main.py - FastAPI 应用入口
- 创建 FastAPI 应用实例
- 配置中间件（CORS）
- 注册路由模块
- `/`: 根路径和 API 信息
- `/health`: 健康检查

### 2. app/api/routes/ - API 路由层
- `analyze.py`: `/analyze` 端点，代码分析和功能定位
- `generate_tests.py`: `/generate-tests` 端点，动态测试生成和执行

### 3. app/core/config.py - 配置管理
- 使用 Pydantic Settings 管理环境变量
- 统一配置访问接口

### 2. code_analyzer.py - 代码分析模块
- ZIP 文件提取
- 文件树构建
- AST 解析（Python, JavaScript/TypeScript）
- 代码结构提取

### 5. app/services/ai_analyzer.py - AI 分析模块
- OpenAI/Qwen API 集成
- 功能分析和匹配
- 执行计划生成

### 6. app/services/test_generator.py - 测试生成模块
- LLM Function Calling 实现
- 测试代码生成
- 测试执行和结果收集

### 7. app/services/test_executor_functions.py - 测试执行函数
- `execute_code`: 执行代码片段
- `read_file`: 读取文件
- `write_file`: 写入文件
- `run_command`: 执行 shell 命令
- `check_api_endpoint`: API 端点测试

### 6. response_formatter.py - 响应格式化
- JSON 响应格式化
- 错误响应处理

## 数据流

### 分析流程
1. 接收 ZIP 文件和问题描述
2. 提取并分析代码结构
3. AI 分析功能实现位置
4. 生成结构化报告

### 测试生成流程
1. 分析代码库结构
2. LLM 通过 Function Calling 探索代码
3. 生成测试代码并写入文件
4. 安装依赖并执行测试
5. 收集并返回结果

## 技术栈

- **Web Framework**: FastAPI
- **AI Service**: OpenAI API (兼容 Qwen via DashScope)
- **Code Analysis**: AST (Python), Regex (JavaScript/TypeScript)
- **Test Execution**: subprocess, pytest, jest

## 配置

环境变量：
- `OPENAI_API_KEY`: API 密钥
- `OPENAI_BASE_URL`: API 基础 URL（默认：DashScope 兼容端点）
- `OPENAI_MODEL`: 模型名称（默认：qwen3-max）
