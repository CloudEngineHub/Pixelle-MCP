# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 设置工作目录
WORKDIR /app

# 复制所有文件
COPY . .

# 使用uv安装依赖
RUN uv sync --frozen --no-cache

# 确保使用虚拟环境中的Python
ENV PATH="/app/.venv/bin:$PATH"

# 暴露端口
EXPOSE 9002

# 启动命令
CMD ["python", "main.py"] 