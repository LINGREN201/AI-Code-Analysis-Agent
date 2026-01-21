# Docker 部署指南

## 快速开始

### 方式一：使用 docker-compose（推荐）

这是最简单的方式，适合开发和测试环境。

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

### 方式二：使用 docker build 和 docker run

适合生产环境或需要更多自定义的场景。

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

## 环境变量配置

### 必需的环境变量

- `OPENAI_API_KEY`: API 密钥（必需）

### 可选的环境变量

- `OPENAI_MODEL`: 模型名称（默认：qwen3-max）
- `OPENAI_BASE_URL`: API 基础 URL（默认：DashScope 兼容端点）

### 配置方式

#### 1. 使用 .env 文件（docker-compose）

创建 `.env` 文件：

```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=qwen3-max
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

#### 2. 使用 -e 参数（docker run）

```bash
docker run -e OPENAI_API_KEY=your_key -e OPENAI_MODEL=qwen3-max ...
```

#### 3. 使用环境变量文件

```bash
docker run --env-file .env ...
```

## 端口配置

默认端口是 8000，可以通过以下方式修改：

### docker-compose

修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:8000"  # 主机端口:容器端口
```

### docker run

```bash
docker run -p 8080:8000 ...  # 映射到主机 8080 端口
```

## 常用命令

### 查看容器状态

```bash
# docker-compose
docker-compose ps

# docker
docker ps | grep ai-code-analysis-agent
```

### 查看日志

```bash
# docker-compose
docker-compose logs -f agent

# docker
docker logs -f ai-code-analysis-agent
```

### 重启服务

```bash
# docker-compose
docker-compose restart

# docker
docker restart ai-code-analysis-agent
```

### 进入容器

```bash
# docker-compose
docker-compose exec agent bash

# docker
docker exec -it ai-code-analysis-agent bash
```

### 停止服务

```bash
# docker-compose
docker-compose down

# docker
docker stop ai-code-analysis-agent
docker rm ai-code-analysis-agent
```

## 健康检查

容器包含健康检查功能，可以通过以下命令查看：

```bash
docker inspect --format='{{.State.Health.Status}}' ai-code-analysis-agent
```

健康检查会每 30 秒检查一次服务是否正常运行。

## 生产环境建议

1. **使用环境变量文件**: 不要将敏感信息硬编码在命令中
2. **设置资源限制**: 在 docker-compose.yml 中添加资源限制
3. **配置日志**: 使用日志驱动收集日志
4. **使用反向代理**: 在生产环境中使用 Nginx 或 Traefik 作为反向代理
5. **定期更新镜像**: 保持基础镜像和依赖的更新

### 示例：生产环境配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  agent:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ai-code-analysis-agent
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 故障排查

### 容器无法启动

1. 检查端口是否被占用：
   ```bash
   netstat -tuln | grep 8000
   ```

2. 查看容器日志：
   ```bash
   docker logs ai-code-analysis-agent
   ```

3. 检查环境变量：
   ```bash
   docker exec ai-code-analysis-agent env | grep OPENAI
   ```

### API 调用失败

1. 检查 API Key 是否正确设置
2. 检查网络连接（需要访问 DashScope API）
3. 查看应用日志获取详细错误信息

### 镜像构建失败

1. 检查 Dockerfile 语法
2. 检查网络连接（需要下载基础镜像）
3. 使用 `--no-cache` 重新构建：
   ```bash
   docker build --no-cache -t ai-code-analysis-agent .
   ```
