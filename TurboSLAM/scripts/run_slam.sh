#!/usr/bin/env bash
# ============================================================
# 文件名: tmux_multi_windows.sh
# 功能: 创建一个 Tmux 会话，启动多个窗口并执行指定命令
# 使用: chmod +x tmux_multi_windows.sh && ./tmux_multi_windows.sh
# ============================================================

# ----- 配置区域 -----
SESSION_NAME="SLAM"        # Tmux 会话名称
# 定义每个窗口要执行的命令（按顺序对应窗口 0,1,2,...）
COMMANDS=(
    "roslaunch livox_ros_driver2 msg_MID360s.launch"          # 窗口0: 激光雷达
    "roslaunch fast_lio mapping_mid360.launch"                # 窗口1: 定位
    "sudo chmod 0777 /dev/ttyS0"                              # 窗口2: 实时日志（Linux）
    "roslaunch prometheus_uav_control odom_to_mavlink.launch" # 窗口3: 转换脚本
)

# ----- 脚本主体 -----
# 检查 tmux 是否安装
if ! command -v tmux &> /dev/null; then
    echo "错误: 未找到 tmux，请先安装 tmux (apt install tmux / brew install tmux)"
    exit 1
fi

# 如果会话已存在，可选择杀掉旧会话（或直接附加）
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "会话 $SESSION_NAME 已存在，正在杀死旧会话..."
    tmux kill-session -t "$SESSION_NAME"
fi

# 创建第一个窗口（窗口索引 0）
# 注意：new-session 默认会创建并进入一个窗口，我们用 -d 先不附加，-n 指定窗口名
FIRST_CMD="${COMMANDS[0]}"
tmux new-session -d -s "$SESSION_NAME" -n "win0" "bash -c '$FIRST_CMD; exec bash'"

# 循环创建其余窗口（索引 >= 1）
for i in "${!COMMANDS[@]}"; do
    if [ $i -eq 0 ]; then
        continue    # 第一个窗口已创建
    fi
    cmd="${COMMANDS[$i]}"
    win_name="win$i"
    tmux new-window -t "$SESSION_NAME" -n "$win_name" "bash -c '$cmd; exec bash'"
done

# 可选: 设置第一个窗口为活动窗口
tmux select-window -t "$SESSION_NAME:win0"

# 附加到会话（让用户进入 Tmux 界面）
echo "成功创建会话 $SESSION_NAME，包含 ${#COMMANDS[@]} 个窗口。"
echo "正在附加到 Tmux 会话... (按 Ctrl+B D 脱离会话)"
tmux attach-session -t "$SESSION_NAME"
