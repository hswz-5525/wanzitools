# 使用官方 Python 镜像作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置国内镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian-security/ bullseye-security main" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bullseye-backports main non-free contrib" >> /etc/apt/sources.list

# 安装系统依赖和 Docker CLI
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    curl \
    gnupg \
    lsb-release \
    ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL --retry 5 --retry-delay 2 https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# 使用阿里云 PyPI 镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip config set install.trusted-host mirrors.aliyun.com

# 复制项目文件
COPY requirements.txt .
COPY *.py .
COPY templates/ templates/
COPY languages/ languages/
COPY config.yaml .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV NAS_MOUNT_POINT=/mnt/nas
ENV COMPOSE_ROOT=/mnt/nas/docker

# 创建必要的目录
RUN mkdir -p /mnt/nas/docker

# 暴露端口
EXPOSE 5525

# 启动应用
CMD ["python", "wanzitools.py"] 