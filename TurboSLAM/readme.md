# TurboSLAM 简介
该项目缝合 Fast-Lio2、lightning-lm、foxglove 等组件，实现雷达SLAM导航/避障/规划等功能。
https://gitee.com/Kerwin8357/TurboSLAM.git

## How to build
```shell
cd TurboSLAM
bash ./scripts/install_dep.sh
bash ./scripts/build_all.sh
```

## 环境依赖
  * Ubuntu22.04
  * ROS2-${ROS_DISTRO}
  * foxglove-sdk
  * Livox-SDK2
  * livox_ros_driver2
  * Pangolin
  * Sophus
  * GTSAM
  * Fast-Lio2
  * lightning-lm

## 安装系统基础依赖
```shell
sudo apt update && sudo apt install -y \
  git cmake build-essential \
  libpcl-dev \
  libeigen3-dev \
  libboost-all-dev \
  libwebsocketpp-dev \
  libtbb-dev \
  libgflags-dev \
  libgoogle-glog-dev \
  libatlas-base-dev \
  libopencv-dev \
  libpcl-dev \
  libyaml-cpp-dev \
  libgoogle-glog-dev \
  libgflags-dev \
  libpcap-dev \
  libepoxy-dev \
  libopenexr-dev \
  pcl-tools \
  ros-${ROS_DISTRO}-pcl-conversions \
  ros-${ROS_DISTRO}-pcl-ros \
  python3-pip \
  python3-colcon-common-extensions \
  python3-rosdep
```

## ROS2 安装
wget http://fishros.com/install -O fishros && bash fishros

## foxglove-sdk
pip install foxglove-sdk -i https://mirrors.aliyun.com/pypi/simple/

## Livox-SDK2
```shell
git clone https://gh.llkk.cc/https://github.com/Livox-SDK/Livox-SDK2.git
cd Livox-SDK2

mkdir build && cd build
cmake .. && make -j$(nproc)
sudo make install
```

注意：MID630s 默认IP地址为192.168.1.1XX, XX为产品序列号最后两位

## livox_ros_driver2
Livox雷达的ROS2驱动，它有自己的构建脚本，需要单独编译。
[WSL2部署22.04环境不能正常安装, 24.04环境正常]

### 修改驱动发布格式：
驱动默认发布 PointCloud2 格式

Fast-LIO2 期望 CustomMsg 格式

修正如下文件：
livox_ros_driver2/launch_ROS2/rviz_MID360_launch.py文件中的 xfer_format

### 作为项目的子节点工程构建
```shell
mkdir -p ros2_ws/src
git clone https://github.com/Livox-SDK/livox_ros_driver2.git ros2_ws/src/livox_ros_driver2

cd ros2_ws/src/livox_ros_driver2
source /opt/ros/${ROS_DISTRO}/setup.bash
./build.sh ${ROS_DISTRO}
```

### 启用改节点环境配置
source ./ros2_ws/install/setup.bash
或者永久配置：

```shell
echo "source ~/xxx/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

## Fast-Lio2

### 该项目有两个版本
(1) 官方版本的ROS2分支
https://github.com/hku-mars/FAST_LIO/tree/ROS2

```shell
cd <ros2_ws>/src # cd into a ros2 workspace folder
git clone https://github.com/Ericsii/FAST_LIO.git --recursive

# or
git clone https://gh.llkk.cc/https://github.com/Ericsii/FAST_LIO.git --recursive

cd ..
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source ../install/setup.bash # use setup.zsh if use zsh
```

### 启动 Fast-Lio2
ros2 launch fast_lio mapping.launch.py config_file:=mid360.yaml

(2) 自定义ROS2版本
https://github.com/liangheming/FASTLIO2_ROS2

### (1) 重构[FASTLIO2](https://github.com/hku-mars/FAST_LIO) 适配ROS2
### (2) 添加回环节点，基于位置先验+ICP进行回环检测，基于GTSAM进行位姿图优化
### (3) 添加重定位节点，基于由粗到细两阶段ICP进行重定位
### (4) 增加一致性地图优化，基于[BLAM](https://github.com/hku-mars/BALM) (小场景地图) 和[HBA](https://github.com/hku-mars/HBA) (大场景地图)


## 适配 livox_ros_driver2
livox_ros_driver是旧版本ROS支持包，更新为livox_ros_driver2

替换工程文件和源码所有 livox_ros_driver 为 livox_ros_driver2
CMakelists.txt
package.xml
FAST_LIO/src/preprocess.h
FAST_LIO/src/laserMapping.cpp
FAST_LIO的命名空间...

## 雷达参数配置：
ros2_ws/src/livox_ros_driver2/config/MID360s_config.json

## lightning-lm
### 适配 livox_ros_driver2

### 安装依赖
xxx\lightning-lm\scripts\install_dep.sh

### foxglove
```shell
sudo apt install ros-${ROS_DISTRO}-foxglove-bridge
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```
Foxglove Studio:
打开软件，点击 "Open connection". 选择 "Foxglove WebSocket" (default is ws://localhost:8765).

## Pangolin
安装：
```shell
git clone --recursive https://github.com/stevenlovegrove/Pangolin.git
cd Pangolin
./scripts/install_prerequisites.sh recommended
cmake -B build -DPython3_EXECUTABLE=$(which python3) -DBUILD_PANGOLIN_LIBOPENEXR=OFF
cmake --build build -j $(nproc)

cd ./build
sudo make install
```

## Sophus
```shell
git clone https://github.com/strasdat/Sophus.git
cd Sophus
git checkout 1.22.10

mkdir build && cd build
cmake .. -DSOPHUS_USE_BASIC_LOGGING=ON
make -j$(nproc)
sudo make install

# GTSAM
GTSAM 是位姿图优化（PGO）模块的核心依赖。
在 Ubuntu 22.04 上建议使用 4.2a9 版本，并启用系统 Eigen

git clone https://github.com/borglab/gtsam.git
cd gtsam
git checkout 4.2a9

mkdir build && cd build
cmake .. \
  -DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF \
  -DGTSAM_BUILD_TESTS=OFF \
  -DGTSAM_WITH_TBB=OFF \
  -DGTSAM_USE_SYSTEM_EIGEN=ON \
  -DGTSAM_BUILD_WITH_MARCH_NATIVE=OFF
make -j$(nproc)
sudo make install
```

## 系统运行控制
启动脚本：
```shell
tmuxinator start -p ./scripts/slam.yaml
```

关闭脚本：
```shell
tmux kill-server
```

重新关联
```shell
tmux attach
```

## uav_master
### 编译
```shell
colcon build --packages-select uav_master
```

### 运行
```shell
source install/setup.bash
ros2 run uav_master odometry_subscriber
```

### 安装 pymavlink 依赖（可选）
# Install pymavlink and its dependencies
```shell
sudo python3 -m pip install --upgrade pymavlink
```

### apriltag_ros
https://github.com/christianrauch/apriltag_ros
ROS 2 node for AprilTag detection

https://april.eecs.umich.edu/software/apriltag.html

### 检查服务文件是否正确
待修正：
sudo systemd-analyze verify turbo_slam.service
/etc/systemd/system/turbo_slam.service:77: Failed to parse resource value, ignoring: 65536          # SLAM 可能打开大量文件/套接字
/etc/systemd/system/turbo_slam.service:79: Failed to parse the OOM score adjust value '-500        # 降低被 OOM Killer 选中概率', ignoring: Invalid argument
/etc/systemd/system/turbo_slam.service:80: Failed to parse nice priority '-10                   # 略高于普通进程的调度优先级', ignoring: Invalid argument
/lib/systemd/system/snapd.service:23: Unknown key name 'RestartMode' in section 'Service', ignoring.

### frpc 配置
frpc -c {config_path}
