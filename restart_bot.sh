#!/bin/bash
set -e  # 任何命令失败立即退出

# --- 配置 ---
REMOTE_USER="${REMOTE_USER}"
REMOTE_HOST="${REMOTE_HOST}"
CONTAINER_NAME="yahoo-mercari-discord-bot_1"
IMAGE_NAME="yahoo-mercari-discord-bot"
REMOTE_PERSISTENT_DATA_HOST_PATH="/Users/${REMOTE_USER}/docker_data/${IMAGE_NAME}/app_data"
REMOTE_CONFIG_DIR="/Users/${REMOTE_USER}/docker_data/${IMAGE_NAME}"

if [ -f .env ]; then
  export $(grep -v '^#' .env | sed 's/\r$//' | awk '/=/ {print $1}')
fi

NOTIFICATION=$(grep -E '^notification:' config.yaml | head -1 | sed -E 's/^notification:[[:space:]]*//' | tr -d '"' | tr '[:upper:]' '[:lower:]')
NOTIFICATION="${NOTIFICATION:-discord}"

if [ "$NOTIFICATION" = "bark" ]; then
  : "${BARK_KEY:?错误：bark 模式请在 .env 中设置 BARK_KEY}"
  BOT_TOKEN="${BOT_TOKEN:-}"
else
  : "${BOT_TOKEN:?错误：discord 模式请在 .env 中设置 BOT_TOKEN}"
  BARK_KEY="${BARK_KEY:-}"
fi

echo ">>> 重启远程容器: ${CONTAINER_NAME} (mode: ${NOTIFICATION})"

scp config.yaml "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_CONFIG_DIR}/config.yaml"

ssh "${REMOTE_USER}@${REMOTE_HOST}" << EOF
  set -e
  echo ">>> [${REMOTE_HOST}] 停止并删除旧的容器 (如果存在)..."
  docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true
  docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || true
  echo ">>> [${REMOTE_HOST}] 旧容器已处理。"

  echo ">>> [${REMOTE_HOST}] 运行新容器并挂载数据目录..."
  docker run -d \
    -v "${REMOTE_PERSISTENT_DATA_HOST_PATH}:/app/data" \
    -v "${REMOTE_CONFIG_DIR}/config.yaml:/app/config.yaml:ro" \
    -e BOT_TOKEN="${BOT_TOKEN}" \
    -e BARK_KEY="${BARK_KEY}" \
    -e ENV="prod" \
    --name "${CONTAINER_NAME}" \
    ${IMAGE_NAME}:latest
  echo ">>> [${REMOTE_HOST}] 新容器已启动: ${CONTAINER_NAME}"
  echo ">>> [${REMOTE_HOST}] 重启完成。"
EOF

echo ">>> 查看容器日志（Ctrl+C 停止）..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "docker logs -f ${CONTAINER_NAME}"
