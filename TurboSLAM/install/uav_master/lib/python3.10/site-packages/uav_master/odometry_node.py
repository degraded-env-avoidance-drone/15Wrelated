import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

from tpxsdk.share.data_utils import *
from tpxsdk.tplink.tplink import TPLink
from tpxsdk.uav.uav_admin import UavAdmin
from tpxsdk.uav.uav_item import UavItem

# ============================================================
#  ENU <-> NED 坐标变换辅助函数
# ============================================================
# ROS 通常使用 ENU (East-North-Up) 坐标系
# TPLINK 使用 NED (North-East-Down) 坐标系
#
# 旋转矩阵 R_ENU_to_NED = [[0,1,0],[1,0,0],[0,0,-1]]
# 等价于绕 [1/sqrt(2), 1/sqrt(2), 0] 旋转 180°
# 对应四元数: q = [0, sqrt(2)/2, sqrt(2)/2, 0]

_SQRT2_2 = math.sqrt(2) / 2.0

# q_ENU_to_NED: 将 ENU 旋转到 NED 的四元数 [w, x, y, z]
Q_ENU_TO_NED = [0.0, _SQRT2_2, _SQRT2_2, 0.0]

# q_NED_to_ENU = conj(q_ENU_to_NED): 将 NED 旋转到 ENU 的四元数
Q_NED_TO_ENU = [0.0, -_SQRT2_2, -_SQRT2_2, 0.0]


def quat_multiply(q1, q2):
    """Hamilton 乘积: q1 * q2，四元数格式为 [w, x, y, z]"""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]


def enu_quat_to_ned(q_wxyz):
    """将 ENU 系下的姿态四元数转换为 NED 系下的姿态四元数。
    q_ENU->body → q_NED->body = q_ENU->body * q_NED->ENU
    """
    return quat_multiply(q_wxyz, Q_NED_TO_ENU)


class OdometryNode(Node):
    """订阅 /Odometry 话题，转换为 TPLINK ODOMETRY 消息并通过串口发送"""

    SERIAL_PORT = '/dev/ttyS0'
    SERIAL_BAUD = 57600

    # TPLINK 坐标系定义
    MAV_FRAME_LOCAL_NED = 1
    MAV_FRAME_LOCAL_FRD = 12

    def __init__(self):
        super().__init__('odometry_subscriber')

        # -- 订阅 ROS Odometry --
        self.subscription = self.create_subscription(
            Odometry,
            '/Odometry',
            self.odom_callback,
            10
        )

        # 创建飞控通讯
        meta_path = os.path.expanduser('.')
        lnk = TPLink(SERIAL_PORT, None)

        # 等待TPLink连接成功
        while lnk.is_opened is False:
            time.sleep(1)
            lnk.open(SERIAL_PORT, SERIAL_BAUD)

        # 创建Uav对象
        uav = UavItem(lnk)
        admin = UavAdmin()
        admin.add(uav)
        
        # 连接UAV
        logging.info(f'Start UAV connecting...')
        while not admin.connect(meta_path):
            time.sleep(1)
        while True:
            if uav.IsConnected:
                logging.info(f'UAV Connected:{uav.IsConnected}')
                break

        self.get_logger().info(
            f'TPLINK 串口已连接: {self.SERIAL_PORT} @ {self.SERIAL_BAUD}'
        )

        self.get_logger().info(
            'Odometry 订阅节点已启动，正在监听 /Odometry 话题, 通过 TPLINK 发送到飞控 ...'
        )

    def odom_callback(self, msg: Odometry):
        """ROS Odometry 回调：转换并发送 TPLINK ODOMETRY 消息"""

        # --------------------------------------------------------
        #  1. 提取时间戳 (单位: 微秒)
        # --------------------------------------------------------
        time_usec = msg.header.stamp.sec * 1_000_000 + msg.header.stamp.nanosec / 1000

        # --------------------------------------------------------
        #  2. 位置: ENU -> NED
        #     x_ned = y_enu , y_ned = x_enu , z_ned = -z_enu
        # --------------------------------------------------------
        pos_ros = msg.pose.pose.position
        pos_ned = (pos_ros.y, pos_ros.x, -pos_ros.z)

        # --------------------------------------------------------
        #  3. 姿态四元数: ENU -> NED
        #     q_NED->body = q_ENU->body * q_NED->ENU
        # --------------------------------------------------------
        orient = msg.pose.pose.orientation
        q_enu_wxyz = [orient.w, orient.x, orient.y, orient.z]
        q_ned_wxyz = enu_quat_to_ned(q_enu_wxyz)

        # TPLINK ODOMETRY 的 q 字段格式: [w, x, y, z]
        q_mav = q_ned_wxyz

        # --------------------------------------------------------
        #  4. 线速度: ENU -> NED
        #     vx_ned = vy_enu , vy_ned = vx_enu , vz_ned = -vz_enu
        # --------------------------------------------------------
        vel_ros = msg.twist.twist.linear
        vel_ned = (vel_ros.y, vel_ros.x, -vel_ros.z)

        # --------------------------------------------------------
        #  5. 角速度: ROS(FLU) -> TPLINK(FRD)
        #     rollspeed = angular.x  (body x, 相同)
        #     pitchspeed = -angular.y (body y, ROS左 <-> TPLINK右)
        #     yawspeed = -angular.z (body z, ROS上 <-> TPLINK下)
        # --------------------------------------------------------
        ang_ros = msg.twist.twist.angular
        rollspeed = ang_ros.x
        pitchspeed = -ang_ros.y
        yawspeed = -ang_ros.z

        # --------------------------------------------------------
        #  6. 协方差: ROS 提供 36 元素(6x6)，只取对角线
        #     TPLINK 需要 21 元素(上三角矩阵)
        # --------------------------------------------------------
        pose_cov = [0.0] * 21
        vel_cov = [0.0] * 21
        # 填充对角线元素 (位置 x,y,z)
        for i in range(3):
            diag_val = msg.pose.covariance[i * 6 + i]
            # TPLINK 上三角矩阵索引: 对角线位置
            # [0] (1,2,3,4,5,6), [7] (2,3,4,5,6), [13] (3,4,5,6), [18] (4,5,6),
            # [22] (5,6), [25] (6)
            idx = sum(range(6 - i, 7))  # 6+5+4+3+2+1 -> offset
            # 简化: 直接使用对角索引 [0, 7, 13, 18, 22, 25] -> 对应 i=0..5
            diag_indices = [0, 7, 13, 18, 22, 25]
            pose_cov[diag_indices[i]] = msg.pose.covariance[i * 6 + i]
            vel_cov[diag_indices[i]] = msg.twist.covariance[i * 6 + i]

        # --------------------------------------------------------
        #  7. 发送 TPLINK ODOMETRY 数据
        # --------------------------------------------------------
        #FIXME: 实现 TPLINK ODOMETRY 数据发送

        # --------------------------------------------------------
        #  8. 日志输出
        # --------------------------------------------------------
        self.get_logger().debug(
            f'[TPLINK ODOMETRY] '
            f'pos(NED): ({pos_ned[0]:.3f}, {pos_ned[1]:.3f}, {pos_ned[2]:.3f}) | '
            f'q(w,x,y,z): ({q_mav[0]:.3f}, {q_mav[1]:.3f}, {q_mav[2]:.3f}, {q_mav[3]:.3f}) | '
            f'vel(NED): ({vel_ned[0]:.3f}, {vel_ned[1]:.3f}, {vel_ned[2]:.3f})'
        )


def main(args=None):
    rclpy.init(args=args)
    node = OdometryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
