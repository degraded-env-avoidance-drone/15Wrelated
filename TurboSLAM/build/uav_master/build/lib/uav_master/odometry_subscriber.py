import math
import os
import time
from collections import deque

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

os.environ['MAVLINK20'] = '1'
os.environ['MAVLINK_DIALECT'] = 'common'
from pymavlink import mavutil


def _safe_sqrt(x):
    """安全开方: 输入 <= 0 或 NaN 时返回 0.0, 避免 ValueError: math domain error"""
    return math.sqrt(x) if x > 0.0 else 0.0


def evaluate_odom_health(cov, pos_std_thresh=0.2, att_std_deg_thresh=5.0,
                         ratio_thresh=10.0, max_ratio_thresh=100.0):
    """基于 6x6 协方差 (row-major) 评估里程计健康度。

    判定维度:
      - 位置/姿态平均标准差 (对角线 [0,7,13] / [18,22,25])
      - 水平面主/次不确定度比 (退化检测, 长廊/空旷时某方向方差剧增)
      - 水平/垂直不确定度比

    容错:
      - 对角元素为负值 (异常/占位数据) 时 clamp 到 0, 并在描述中标记
      - 协方差全零 (上游未填充) 时不判退化/超限, 直接返回 OK
      - 输入为 NaN 时按 0 处理, 避免 math domain error

    返回 (level, desc):
      level: 0=OK 1=WARN 2=FAULT
      desc:  可读描述
    """
    if cov is None or len(cov) < 26:
        return 2, 'invalid_cov'

    px, py, pz = cov[0], cov[7], cov[13]
    ar, ap, ay = cov[18], cov[22], cov[25]

    # 负方差为异常数据: clamp 并标记
    neg_flags = [
        f'{n}={v:.3g}' for n, v in
        (('px', px), ('py', py), ('pz', pz), ('att_r', ar), ('att_p', ap), ('att_y', ay))
        if v < 0
    ]

    pos_std = _safe_sqrt((max(px, 0.0) + max(py, 0.0) + max(pz, 0.0)) / 3.0)
    att_std = _safe_sqrt((max(ar, 0.0) + max(ap, 0.0) + max(ay, 0.0)) / 3.0)
    att_std_deg = math.degrees(att_std)

    # 协方差未填充 (全零) 时无信息量, 不做退化/超限判定
    if pos_std <= 0.0 and att_std <= 0.0:
        return 0, 'cov-unset(pos/att=0) OK'

    # 退化检测: 标准差比值 (√(max/min 方差))
    h_max, h_min = max(px, py), min(px, py)
    if h_min > 1e-12:
        ratio_h = _safe_sqrt(h_max / h_min)
    else:
        ratio_h = float('inf') if h_max > 1e-12 else 0.0
    if pz > 1e-12:
        ratio_v = _safe_sqrt(max(px, py) / pz)
    else:
        ratio_v = float('inf') if max(px, py) > 1e-12 else 0.0

    problems = []
    if pos_std > pos_std_thresh:
        problems.append(f'pos_std={pos_std:.3f}m>{pos_std_thresh}')
    if att_std_deg > att_std_deg_thresh:
        problems.append(f'att_std={att_std_deg:.1f}deg>{att_std_deg_thresh}')
    if ratio_h > max_ratio_thresh or ratio_v > max_ratio_thresh:
        problems.append(f'degraded(rh={ratio_h:.1f},rv={ratio_v:.1f})')
    elif ratio_h > ratio_thresh or ratio_v > ratio_thresh:
        problems.append(f'warn(rh={ratio_h:.1f},rv={ratio_v:.1f})')
    if neg_flags:
        problems.append('neg-var:' + ','.join(neg_flags))

    desc = (f'pos={pos_std:.3f}m att={att_std_deg:.2f}deg '
            f'rh={ratio_h:.1f} rv={ratio_v:.1f}')
    if not problems:
        return 0, desc + ' OK'
    if any(p.startswith('degraded') for p in problems):
        return 2, desc + ' | ' + ' | '.join(problems)
    return 1, desc + ' | ' + ' | '.join(problems)


class OdometrySubscriber(Node):
    """订阅 /Odometry 话题，转换为 MAVLink ODOMETRY 消息并通过串口发送"""

    SERIAL_PORT = '/dev/ttyTHS3'
    SERIAL_BAUD = 921600

    # MAVLink 坐标系定义
    MAV_FRAME_LOCAL_NED = 1
    MAV_FRAME_LOCAL_FRD = 12

    # 里程计健康度评估参数 (阈值需按现场实测标定)
    HEALTH_POS_STD_THRESH = 0.2        # 位置平均标准差阈值 (m)
    HEALTH_ATT_STD_DEG_THRESH = 5.0    # 姿态平均标准差阈值 (deg)
    HEALTH_DEGRADED_RATIO = 100.0      # 严重退化: 主/次不确定度比
    HEALTH_WARN_RATIO = 10.0           # 关注: 主/次不确定度比
    HEALTH_REPORT_EVERY = 50                  # 正常状态每 N 帧汇总打印一次
    HEALTH_DIVERGE_WINDOW = 1.0        # 发散检测滑动窗口 (s)
    HEALTH_DIVERGE_RATIO = 5.0         # 窗口内标准差增长倍数判发散

    def __init__(self):
        super().__init__('odometry_subscriber')

        # -- 订阅 ROS Odometry --
        self.subscription = self.create_subscription(
            Odometry,
            '/Odometry',
            self.odom_callback,
            10
        )

        # -- 打开 MAVLink 串口连接 --
        self.get_logger().info(
            f'正在打开 MAVLink 串口: {self.SERIAL_PORT} @ {self.SERIAL_BAUD} ...'
        )
        self.mav_conn = mavutil.mavlink_connection(
            self.SERIAL_PORT,
            baud=self.SERIAL_BAUD,
            source_system=1,
            source_component=197,   # MAV_COMP_ID_ODOMETRY
            dialect='common'
        )
        self.get_logger().info(
            f'MAVLink 串口已连接: {self.SERIAL_PORT} @ {self.SERIAL_BAUD}'
        )

        self.get_logger().info(
            'Odometry 订阅节点已启动，正在监听 /Odometry 话题, 通过 MAVLink 发送到飞控 ...'
        )

        # -- 记录上次 ODOMETRY 发送时间 (用于计算发送间隔) --
        self._last_send_time = None

        # -- 里程计健康度评估状态 --
        self._health_level = 0                  # 0=OK 1=WARN 2=FAULT
        self._health_frames = 0                 # 距上次汇总打印的帧数
        self._std_history = deque(maxlen=400)   # (time, pos_std) 用于发散检测

    def _check_divergence(self, now, pos_std):
        """发散检测: 最近 HEALTH_DIVERGE_WINDOW 秒窗口内位置标准差
        增长超过 HEALTH_DIVERGE_RATIO 倍, 判定滤波发散"""
        self._std_history.append((now, pos_std))
        while self._std_history and now - self._std_history[0][0] > self.HEALTH_DIVERGE_WINDOW:
            self._std_history.popleft()
        if len(self._std_history) < 10:
            return False
        base = self._std_history[0][1]
        return pos_std > base * self.HEALTH_DIVERGE_RATIO and pos_std > 0.05

    def odom_callback(self, msg: Odometry):
        """ROS Odometry 回调：转换并发送 MAVLink ODOMETRY 消息"""

        # --------------------------------------------------------
        #  1. 提取时间戳 (单位: 微秒)
        # --------------------------------------------------------
        time_usec = msg.header.stamp.sec * 1_000_000 + msg.header.stamp.nanosec / 1000

        # --------------------------------------------------------
        #  2. 位置: camera_init -> NED
        # --------------------------------------------------------
        pos_ros = msg.pose.pose.position
        pos_ned = (pos_ros.x, -pos_ros.y, -pos_ros.z)

        # --------------------------------------------------------
        #  3. 姿态四元数: 实测校准
        #     实测: 四元数转欧拉角后 pitch 符号相反、yaw 增长方向相反,
        #     roll 正常。修正: q_mav = (w, x, -y, -z)
        #     对应欧拉角变换 (roll, -pitch, -yaw)
        # --------------------------------------------------------
        orient = msg.pose.pose.orientation

        # MAVLink ODOMETRY 的 q 字段格式: [w, x, y, z]
        q_mav = [orient.w, orient.x, -orient.y, -orient.z]

        # --------------------------------------------------------
        #  4. 线速度: camera_init(world) -> NED
        # --------------------------------------------------------
        vel_ros = msg.twist.twist.linear
        vel_ned = (vel_ros.x, -vel_ros.y, -vel_ros.z)

        # --------------------------------------------------------
        #  5. 角速度: ROS(FLU) -> MAVLink(FRD)
        #     rollspeed = angular.x  (body x, 相同)
        #     pitchspeed = -angular.y (body y, ROS左 <-> MAVLink右)
        #     yawspeed = -angular.z (body z, ROS上 <-> MAVLink下)
        # --------------------------------------------------------
        ang_ros = msg.twist.twist.angular
        rollspeed = ang_ros.x
        pitchspeed = -ang_ros.y
        yawspeed = -ang_ros.z

        # --------------------------------------------------------
        #  6. 协方差: ROS 提供 36 元素(6x6)，只取对角线
        #     MAVLink 需要 21 元素(上三角矩阵)
        # --------------------------------------------------------
        pose_cov = [0.0] * 21
        vel_cov = [0.0] * 21
        # 填充对角线元素 (位置 x,y,z)
        for i in range(3):
            diag_val = msg.pose.covariance[i * 6 + i]
            # MAVLink 上三角矩阵索引: 对角线位置
            # [0] (1,2,3,4,5,6), [7] (2,3,4,5,6), [13] (3,4,5,6), [18] (4,5,6),
            # [22] (5,6), [25] (6)
            idx = sum(range(6 - i, 7))  # 6+5+4+3+2+1 -> offset
            # 简化: 直接使用对角索引 [0, 7, 13, 18, 22, 25] -> 对应 i=0..5
            diag_indices = [0, 7, 13, 18, 22, 25]
            pose_cov[diag_indices[i]] = msg.pose.covariance[i * 6 + i]
            vel_cov[diag_indices[i]] = msg.twist.covariance[i * 6 + i]

        # --------------------------------------------------------
        #  7. 构造 MAVLink ODOMETRY (#331) 消息并发送
        # --------------------------------------------------------
        mav = self.mav_conn.mav        
        mav.odometry_send(               # 调用实例方法
            int(time_usec),
            self.MAV_FRAME_LOCAL_NED,
            self.MAV_FRAME_LOCAL_FRD,
            pos_ned[0], pos_ned[1], pos_ned[2],
            q_mav,                        # [w, x, y, z]
            vel_ned[0], vel_ned[1], vel_ned[2],
            rollspeed, pitchspeed, yawspeed,
            pose_cov,                     # 21 个 float
            vel_cov,                      # 21 个 float
            0, 0, 0,
        )
        
        # --------------------------------------------------------
        #  8. 日志输出 (含 ODOMETRY 发送时间间隔)
        # --------------------------------------------------------
        now = time.time()
        interval_ms = None
        if self._last_send_time is not None:
            interval_ms = (now - self._last_send_time) * 1000.0
        self._last_send_time = now
        
        # 打印 ODOMETRY (定宽右对齐, 便于逐帧对比)
        print(
            f'[ODOM] pos:{pos_ned[0]:>8.3f} {pos_ned[1]:>8.3f} {pos_ned[2]:>8.3f} | '
            f'vel:{vel_ned[0]:>8.3f} {vel_ned[1]:>8.3f} {vel_ned[2]:>8.3f}'
        )

        # --------------------------------------------------------
        #  9. 里程计健康度评估 (基于 pose.covariance)
        # --------------------------------------------------------
        level, health_desc = evaluate_odom_health(
            msg.pose.covariance,
            pos_std_thresh=self.HEALTH_POS_STD_THRESH,
            att_std_deg_thresh=self.HEALTH_ATT_STD_DEG_THRESH,
            ratio_thresh=self.HEALTH_WARN_RATIO,
            max_ratio_thresh=self.HEALTH_DEGRADED_RATIO,
        )
        # 时间维度发散检测
        pos_std = _safe_sqrt(
            (msg.pose.covariance[0] + msg.pose.covariance[7] + msg.pose.covariance[13]) / 3.0
        )
        if self._check_divergence(now, pos_std):
            level = max(level, 2)
            health_desc += ' | DIVERGING'

        self._health_frames += 1
        changed = level != self._health_level
        self._health_level = level
        # 状态变化/异常立即打印, 正常状态每 N 帧汇总一次
        if changed or level > 0 or self._health_frames >= self.HEALTH_REPORT_EVERY:
            tag = {0: 'OK', 1: 'WARN', 2: 'FAULT'}[level]
            print(f'[HEALTH] {tag:<5} {health_desc}')
            self._health_frames = 0

        self.get_logger().debug(
            f'[MAVLink ODOMETRY] '
            f'pos(NED): ({pos_ned[0]:.3f}, {pos_ned[1]:.3f}, {pos_ned[2]:.3f}) | '
            f'q(w,x,y,z): ({q_mav[0]:.3f}, {q_mav[1]:.3f}, {q_mav[2]:.3f}, {q_mav[3]:.3f}) | '
            f'vel(NED): ({vel_ned[0]:.3f}, {vel_ned[1]:.3f}, {vel_ned[2]:.3f})'
        )


def main(args=None):
    rclpy.init(args=args)
    node = OdometrySubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
