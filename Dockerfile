FROM python:3.10-slim

# 设置时区，可被 docker run 时的环境变量覆盖
ENV TZ=Asia/Shanghai    
# 安装 tzdata 并设置时区机制
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

VOLUME ["/app/data"]
ENV DATA_DIR=/app/data

CMD ["python", "main.py"] 