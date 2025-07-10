#!/bin/bash
set -e  # 任何命令失败立即退出

# --- 配置 ---
REMOTE_USER="${REMOTE_USER}"  # Remote server 用户名
REMOTE_HOST="${REMOTE_HOST}"  # Remote server 主机名或 IP
CONTAINER_NAME="yahoo-mercari-discord-bot_1"  # 容器名

# 加载本地 .env 中的变量（包括 BOT_TOKEN 等）
if [ -f .env ]; then
  export $(grep -v '^#' .env | sed 's/\r$//' | awk '/=/ {print $1}')
fi

: "${BOT_TOKEN:?错误：请设置 BOT_TOKEN 环境变量或 .env 文件中定义它}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
ENABLE_YAHOO_AUCTION="${ENABLE_YAHOO_AUCTION:-true}"
ENABLE_MERCARI="${ENABLE_MERCARI:-true}"
TZ="${TZ:-Asia/Shanghai}"
DO_NOT_RUN_START_HOUR="${DO_NOT_RUN_START_HOUR:-2}"
DO_NOT_RUN_END_HOUR="${DO_NOT_RUN_END_HOUR:-6}"

echo ">>> 重启远程容器: ${CONTAINER_NAME}"

# SSH 到远程主机并重启容器
ssh "${REMOTE_USER}@${REMOTE_HOST}" << EOF
  set -e
  echo ">>> [${REMOTE_HOST}] 停止并删除旧的容器 (如果存在)..."
  docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true # 如果容器不存在则忽略错误
  docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || true   # 如果容器不存在则忽略错误
  echo ">>> [${REMOTE_HOST}] 旧容器已处理。"

  echo ">>> [${REMOTE_HOST}] 运行新容器并挂载数据目录..."
  docker run -d \
    -v "/Users/${REMOTE_USER}/docker_data/yahoo-mercari-discord-bot/app_data:/app/data" \
    -e BOT_TOKEN="${BOT_TOKEN}" \
    -e CHECK_INTERVAL="${CHECK_INTERVAL}" \
    -e ENABLE_YAHOO_AUCTION="${ENABLE_YAHOO_AUCTION}" \
    -e ENABLE_MERCARI="${ENABLE_MERCARI}" \
    -e TZ="${TZ}" \
    -e DO_NOT_RUN_START_HOUR="${DO_NOT_RUN_START_HOUR}" \
    -e DO_NOT_RUN_END_HOUR="${DO_NOT_RUN_END_HOUR}" \
    -e ENV="prod" \
    --name "${CONTAINER_NAME}" \
    yahoo-mercari-discord-bot:latest
  echo ">>> [${REMOTE_HOST}] 新容器已启动: ${CONTAINER_NAME}"
  echo ">>> [${REMOTE_HOST}] 重启完成。"
EOF

echo ">>> 查看容器日志（Ctrl+C 停止）..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "docker logs -f ${CONTAINER_NAME}"