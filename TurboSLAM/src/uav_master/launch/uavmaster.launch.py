# ros2 launch uav_master zerone.launch.py

import os
import pathlib
import launch
from launch_ros.actions import Node
from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    """launch内容描述函数，由ros2 launch 扫描调用"""
    package_dir = get_package_share_directory('uav_master')

    drone_node = Node(
        package='uav_master',
        executable='drone_node',
        parameters=[{'rcl_log_level': 40}]
    )

    return LaunchDescription([drone_node])