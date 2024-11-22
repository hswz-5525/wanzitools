FROM golang:1.19-alpine

WORKDIR /app

# 设置Alpine镜像源为阿里云
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# 设置Go代理
ENV GOPROXY=https://goproxy.cn,direct

# 设置时区为亚洲/上海
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    apk del tzdata

# 安装必要的系统依赖
RUN apk add --no-cache gcc musl-dev

# 复制 Go 项目文件
COPY go.mod .
COPY docker_manager.go .

# 下载依赖并生成 go.sum
RUN go mod tidy

# 编译
RUN go build -o docker_manager

# 暴露端口
EXPOSE 5526

# 运行
CMD ["./docker_manager"] 