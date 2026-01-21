# 使用指南

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

# 4. 停止服务
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

### 4. 访问 API 文档

打开浏览器访问：**http://localhost:8000/docs**

无论使用哪种方式启动，API 文档都在同一个地址。

## API 接口说明

### 1. POST /analyze - 代码分析

**功能**: 分析代码库并生成功能定位报告

**请求**:
- `problem_description`: 功能描述（字符串）
- `code_zip`: 代码 ZIP 文件
- `include_tests`: 是否包含测试生成（可选，默认 false）

**响应示例**:
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

### 2. POST /generate-tests - 测试生成

**功能**: 动态生成和执行测试代码

**请求**:
- `problem_description`: 要测试的功能描述
- `code_zip`: 代码 ZIP 文件

**响应示例**:
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

## 使用 Swagger UI 测试

### 推荐方式：使用 Swagger UI

1. 启动服务后访问：http://localhost:8000/docs
2. 选择要测试的接口（`/analyze` 或 `/generate-tests`）
3. 点击 "Try it out"
4. 填写参数：
   - `problem_description`: 输入功能描述
   - `code_zip`: 点击 "Choose File" 选择 ZIP 文件
5. 点击 "Execute" 执行
6. 查看响应结果

### 使用 curl 测试

```bash
# 测试 /analyze 接口
curl -X POST "http://localhost:8000/analyze" \
  -F "problem_description=实现用户管理功能" \
  -F "code_zip=@test_project.zip" \
  -F "include_tests=true"

# 测试 /generate-tests 接口
curl -X POST "http://localhost:8000/generate-tests" \
  -F "problem_description=测试产品创建功能" \
  -F "code_zip=@test_project.zip"
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

## 测试项目准备

项目提供了测试项目示例：`test_project.zip`

包含的功能：
- 用户管理 API
- 产品管理 API
- 订单管理 API
- 完整的测试用例

## 常见问题

### 1. API Key 错误
确保 `.env` 文件中设置了正确的 `OPENAI_API_KEY`

### 2. 测试执行失败
- 检查项目依赖是否已安装
- 查看日志中的错误信息
- 确保测试环境正确配置

### 3. 文件上传失败
- 确保文件大小不超过 50MB
- 确保文件格式为 ZIP
- 检查文件路径是否正确

## 最佳实践

1. **使用 Swagger UI**: 推荐使用 http://localhost:8000/docs 进行测试，界面友好且直观
2. **清晰的描述**: 提供清晰的功能描述有助于更准确的分析
3. **完整的代码**: 确保 ZIP 文件包含完整的项目代码
4. **依赖管理**: 确保项目包含 `requirements.txt` 或 `package.json` 等依赖文件
