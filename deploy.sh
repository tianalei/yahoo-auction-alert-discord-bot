#!/bin/bash
set -e  # 任何命令失败立即退出

# --- 配置 ---
# 注意：使用此脚本前请确保以下环境变量已正确设置：
# - REMOTE_USER: 远程服务器用户名
# - REMOTE_HOST: 远程服务器主机名或 IP
# - BOT_TOKEN: Discord Bot Token（可以在 .env 文件中设置）
REMOTE_USER="${REMOTE_USER}"  # Remote server 用户名
REMOTE_HOST="${REMOTE_HOST}"  # Remote server 主机名或 IP
IMAGE_NAME="yahoo-mercari-discord-bot"  # Docker 镜像名
CONTAINER_NAME="yahoo-mercari-discord-bot_1"  # 容器名

# 持久化数据目录（alerts.db 存放在这里）
REMOTE_PERSISTENT_DATA_HOST_PATH="/Users/${REMOTE_USER}/docker_data/${IMAGE_NAME}/app_data"

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

echo ">>> 步骤 1: 构建 Docker 镜像..."
docker build -t "${IMAGE_NAME}:latest" .
echo ">>> 镜像构建完成: ${IMAGE_NAME}:latest"

echo ">>> 步骤 2: 导出并传输镜像到 ${REMOTE_HOST}..."
TMP_IMAGE_FILE=$(mktemp)
trap 'rm -f "${TMP_IMAGE_FILE}"' EXIT

docker save "${IMAGE_NAME}:latest" -o "${TMP_IMAGE_FILE}"
scp "${TMP_IMAGE_FILE}" "${REMOTE_USER}@${REMOTE_HOST}:/tmp/${IMAGE_NAME}.tar"
echo ">>> 镜像文件已传输到 ${REMOTE_HOST}:/tmp/${IMAGE_NAME}.tar"
# MBP 上的临时文件会在脚本退出时通过 trap 命令自动删除

ssh "${REMOTE_USER}@${REMOTE_HOST}" << EOF
  set -e
  echo ">>> [${REMOTE_HOST}] 加载 Docker 镜像..."
  docker load -i "/tmp/${IMAGE_NAME}.tar"
  echo ">>> [${REMOTE_HOST}] 镜像加载完成。"
  rm "/tmp/${IMAGE_NAME}.tar" # 清理远程服务器上的临时镜像文件
  echo ">>> [${REMOTE_HOST}] 临时镜像文件已删除。"

  echo ">>> [${REMOTE_HOST}] 准备持久化数据目录..."
  mkdir -p "${REMOTE_PERSISTENT_DATA_HOST_PATH}"
  echo ">>> [${REMOTE_HOST}] 持久化数据目录就绪: ${REMOTE_PERSISTENT_DATA_HOST_PATH}"

  echo ">>> 步骤 3: [${REMOTE_HOST}] 停止并删除旧的容器 (如果存在)..."
  docker stop "${CONTAINER_NAME}" > /dev/null 2>&1 || true # 如果容器不存在则忽略错误
  docker rm "${CONTAINER_NAME}" > /dev/null 2>&1 || true   # 如果容器不存在则忽略错误
  echo ">>> [${REMOTE_HOST}] 旧容器已处理。"

  echo ">>> [${REMOTE_HOST}] 运行新容器并挂载数据目录..."
  docker run -d \
    -v "${REMOTE_PERSISTENT_DATA_HOST_PATH}:/app/data" \
    -e BOT_TOKEN="${BOT_TOKEN}" \
    -e CHECK_INTERVAL="${CHECK_INTERVAL}" \
    -e ENABLE_YAHOO_AUCTION="${ENABLE_YAHOO_AUCTION}" \
    -e ENABLE_MERCARI="${ENABLE_MERCARI}" \
    -e TZ="${TZ}" \
    -e DO_NOT_RUN_START_HOUR="${DO_NOT_RUN_START_HOUR}" \
    -e DO_NOT_RUN_END_HOUR="${DO_NOT_RUN_END_HOUR}" \
    -e ENV="prod" \
    --name "${CONTAINER_NAME}" \
    "${IMAGE_NAME}:latest"
  echo ">>> [${REMOTE_HOST}] 新容器已启动: ${CONTAINER_NAME}"
  echo ">>> [${REMOTE_HOST}] 部署完成。"
EOF

echo ">>> 步骤 3: 查看容器日志（Ctrl+C 停止）..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "docker logs -f ${CONTAINER_NAME}"