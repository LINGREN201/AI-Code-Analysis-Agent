# AI Code Analysis Agent

一个基于 Python 的智能代码分析 Agent，能够分析代码库并生成结构化的功能实现报告。

支持 Docker 部署，开箱即用。

## 功能特性

- 📦 接收代码 ZIP 文件和功能描述，进行代码分析
- 🔍 分析代码结构并匹配功能到实现位置
- 📊 生成结构化的 JSON 报告，包含文件路径、函数名和行号
- 🧪 **动态测试生成和执行**: 使用 LLM Function Calling 智能生成和执行测试
  - LLM 可以探索代码库、生成测试并动态执行
  - 支持多种执行方式：代码执行、shell 命令、API 测试
  - 智能测试验证和结果分析

## 快速开始

### 方式一：使用 Docker（推荐）

#### 使用 docker-compose（最简单）

```bash
# 1. 创建 .env 文件
cat > .env << EOF
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=qwen3-max
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f agent

# 4. 访问 API 文档
# 浏览器打开: http://localhost:8000/docs

# 5. 停止服务
docker-compose down
```

#### 使用 docker build 和 docker run

```bash
# 1. 构建镜像
docker build -t ai-code-analysis-agent .

# 2. 运行容器
docker run -d \
  --name ai-code-analysis-agent \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_api_key_here \
  -e OPENAI_MODEL=qwen3-max \
  -e OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  ai-code-analysis-agent

# 3. 查看日志
docker logs -f ai-code-analysis-agent

# 4. 停止容器
docker stop ai-code-analysis-agent
docker rm ai-code-analysis-agent
```

### 方式二：本地运行

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量

创建 `.env` 文件：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=qwen3-max
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

#### 3. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 访问 API 文档

启动服务后（Docker 或本地），访问：**http://localhost:8000/docs**

**推荐使用 Swagger UI 进行测试**，它提供了：
- 📖 完整的 API 文档
- 🧪 交互式测试界面
- 📝 请求/响应示例
- ✅ 直接在浏览器中测试接口

也可以访问 ReDoc：`http://localhost:8000/redoc`

## API 接口说明

### POST /analyze - 代码分析

分析代码库并生成功能定位报告。

**请求参数**:
- `problem_description`: 功能描述（字符串，必填）
- `code_zip`: 代码 ZIP 文件（文件上传，必填）
- `include_tests`: 是否包含测试生成（布尔值，可选，默认 false）

**响应格式**:
```json
{
  "feature_analysis": [
    {
      "feature_description": "功能描述",
      "implementation_location": [
        {
          "file": "path/to/file.py",
          "function": "function_name",
          "lines": "10-20"
        }
      ]
    }
  ],
  "execution_plan_suggestion": "执行计划建议",
  "functional_verification": {
    "generated_test_code": "...",
    "execution_result": {
      "tests_passed": true,
      "log": "..."
    }
  }
}
```

### POST /generate-tests - 测试生成

动态生成和执行测试代码。

**请求参数**:
- `problem_description`: 要测试的功能描述（字符串，必填）
- `code_zip`: 代码 ZIP 文件（文件上传，必填）

**响应格式**:
```json
{
  "feature_analysis": [...],
  "functional_verification": {
    "generated_test_code": "完整的测试代码",
    "execution_result": {
      "tests_passed": true,
      "log": "测试执行日志"
    }
  }
}
```

## 使用示例

### 使用 Swagger UI（推荐）

1. 访问 http://localhost:8000/docs
2. 选择要测试的接口（`/analyze` 或 `/generate-tests`）
3. 点击 "Try it out"
4. 填写参数并上传文件
5. 点击 "Execute" 执行
6. 查看响应结果

### 使用 curl

```bash
# 测试 /analyze 接口
curl -X POST "http://localhost:8000/analyze" \
  -F "problem_description=实现用户管理功能" \
  -F "code_zip=@project.zip" \
  -F "include_tests=true"

# 测试 /generate-tests 接口
curl -X POST "http://localhost:8000/generate-tests" \
  -F "problem_description=测试产品创建功能" \
  -F "code_zip=@project.zip"
```

### 使用 Python requests

```python
import requests

url = "http://localhost:8000/generate-tests"
files = {
    "code_zip": ("project.zip", open("project.zip", "rb"), "application/zip")
}
data = {
    "problem_description": "测试产品创建功能"
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## Docker 部署

### 快速参考

```bash
# 构建镜像
docker build -t ai-code-analysis-agent .

# 运行容器
docker run -d --name agent -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  ai-code-analysis-agent

# 或使用 docker-compose（推荐）
docker-compose up -d
```

详细说明请参考 [DOCKER.md](DOCKER.md)

## 项目结构

```
agent_test/
├── app/                          # 应用主目录
│   ├── main.py                  # FastAPI 应用入口
│   ├── api/                     # API 路由模块
│   │   └── routes/              # 路由定义
│   │       ├── analyze.py       # 代码分析路由
│   │       └── generate_tests.py # 测试生成路由
│   ├── core/                    # 核心配置模块
│   │   └── config.py           # 应用配置
│   ├── services/                # 业务逻辑服务
│   │   ├── code_analyzer.py    # 代码分析服务
│   │   ├── ai_analyzer.py      # AI 分析服务
│   │   ├── test_generator.py   # 测试生成服务
│   │   └── test_executor_functions.py # 测试执行函数
│   └── utils/                   # 工具函数
│       └── response_formatter.py # 响应格式化
├── tests/                        # 测试目录
├── requirements.txt             # Python 依赖
├── Dockerfile                   # Docker 镜像构建文件
├── docker-compose.yml          # Docker Compose 配置
├── README.md                   # 项目主文档（本文件）
├── ARCHITECTURE.md             # 架构设计文档
├── USAGE.md                    # 详细使用指南
├── PROJECT_STRUCTURE.md        # 项目结构说明
└── DOCKER.md                   # Docker 部署详细指南
```

详细结构说明请参考 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## 测试执行原理

Agent 使用 **LLM Function Calling** 动态执行测试：

1. **函数定义**: Agent 为 LLM 提供可执行函数：
   - `execute_code(code, language)` - 执行代码片段
   - `read_file(file_path)` - 读取文件
   - `write_file(file_path, content)` - 写入测试文件
   - `run_command(command)` - 执行 shell 命令
   - `check_api_endpoint(url, method, payload)` - 测试 API 端点
   - `validate_test_result(result)` - 验证测试结果

2. **LLM 驱动执行**: LLM 智能地：
   - 使用 `read_file` 探索代码库
   - 生成合适的测试代码
   - 使用 `write_file` 写入测试文件
   - 使用 `run_command` 执行测试
   - 验证结果并提供反馈

3. **迭代过程**: LLM 可以连续调用多个函数，根据结果调整策略

## 配置说明

### 环境变量

- `OPENAI_API_KEY`: API 密钥（必需）
- `OPENAI_MODEL`: 模型名称（默认：qwen3-max）
- `OPENAI_BASE_URL`: API 基础 URL（默认：DashScope 兼容端点）

### DashScope/Qwen API

默认配置使用 DashScope 兼容端点：
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Model: `qwen3-max`
- 获取 API Key: [阿里云 DashScope](https://dashscope.console.aliyun.com/)

### 标准 OpenAI API

如需使用标准 OpenAI API，设置：
```bash
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

## 文档

- **README.md** (本文件) - 项目概述和快速开始
- **ARCHITECTURE.md** - 详细的架构设计文档
- **USAGE.md** - 完整的使用指南和示例
- **PROJECT_STRUCTURE.md** - 项目结构说明
- **DOCKER.md** - Docker 部署详细指南

## 常见问题

### Docker 相关

- **端口被占用**: 修改 `docker-compose.yml` 中的端口映射或使用 `-p` 参数
- **环境变量未生效**: 检查 `.env` 文件或 `-e` 参数是否正确
- **容器无法启动**: 查看日志 `docker logs ai-code-analysis-agent`

### API 相关

- **API Key 错误**: 确保环境变量正确设置
- **测试执行失败**: 查看日志中的详细错误信息
- **文件上传失败**: 确保文件大小不超过 50MB，格式为 ZIP

更多问题请参考 [USAGE.md](USAGE.md) 和 [DOCKER.md](DOCKER.md)
# AI-Code-Analysis-Agent
