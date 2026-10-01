#!/usr/bin/env bash
# ============================================================
#  TurboSLAM systemd 服务安装脚本
#
#  用法:
#    sudo ./scripts/install_service.sh        # 常规安装(推荐)
#    ./scripts/install_service.sh             # 已具备 root 权限时
#
#  功能:
#    - 自动检测当前登录用户/组/家目录/项目绝对路径
#    - sed 填充 turbo_slam.service 模板占位符
#    - 安装到 /etc/systemd/system/ 并启用开机自启
#    - 兼容 sudo 调用 (用 SUDO_USER 取真实用户, 而非 root)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE="${SCRIPT_DIR}/turbo_slam.service"
DEST="/etc/systemd/system/turbo_slam.service"
SERVICE_NAME="turbo_slam"

# ---- 检测目标用户: sudo 调用时取 SUDO_USER, 否则取当前用户 ----
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    TARGET_USER="${SUDO_USER}"
else
    TARGET_USER="${USER:-$(id -un)}"
fi

if ! id "${TARGET_USER}" &>/dev/null; then
    echo "ERROR: 用户 '${TARGET_USER}' 不存在" >&2
    exit 1
fi

TARGET_GROUP="$(id -gn "${TARGET_USER}")"
TARGET_HOME="$(getent passwd "${TARGET_USER}" | cut -d: -f6)"
TARGET_UID="$(id -u "${TARGET_USER}")"

[[ -f "${TEMPLATE}" ]] || { echo "ERROR: 找不到模板 ${TEMPLATE}" >&2; exit 1; }
[[ -f "${PROJECT_DIR}/install/setup.bash" ]] || {
    echo "WARN: ${PROJECT_DIR}/install/setup.bash 不存在, 服务启动时会失败" >&2
    echo "      请先 colcon build 再安装服务" >&2
}

# ---- 填充占位符并安装 ----
echo "==> 检测到: 用户=${TARGET_USER} (uid=${TARGET_UID}) 组=${TARGET_GROUP}"
echo "==> 家目录: ${TARGET_HOME}"
echo "==> 项目目录: ${PROJECT_DIR}"

sed \
    -e "s|__USER__|${TARGET_USER}|g" \
    -e "s|__GROUP__|${TARGET_GROUP}|g" \
    -e "s|__HOME__|${TARGET_HOME}|g" \
    -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    "${TEMPLATE}" > "${DEST}"

echo "==> 已生成 ${DEST}"
grep -nE '__USER__|__GROUP__|__HOME__|__PROJECT_DIR__' "${DEST}" && {
    echo "ERROR: 仍有未替换的占位符, 请检查模板与 sed 命令" >&2
    exit 1
}

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

echo "==> 安装完成. 管理命令:"
echo "    sudo systemctl start   ${SERVICE_NAME}"
echo "    sudo systemctl stop    ${SERVICE_NAME}"
echo "    sudo systemctl restart ${SERVICE_NAME}"
echo "    journalctl -u ${SERVICE_NAME} -f"

