#!/bin/bash

ROOT=$(pwd)
echo ${ROOT}

#------------------------------------------------------------------------------
echo "build and install Pangolin"
cd ${ROOT}/3rdparty/Pangolin-0.9.5
sudo bash ./scripts/install_prerequisites.sh recommended
cmake -B build -DPython3_EXECUTABLE=$(which python3)
cmake --build build -j $(nproc)
cd ./build
sudo make install

#------------------------------------------------------------------------------
echo "build and install Livox-SDK2"
cd ${ROOT}/3rdparty/Livox-SDK2

# clear old build data
rm -rf build
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install

# clear old build data
rm -rf ${ROOT}/build
#------------------------------------------------------------------------------
echo "install livox_ros_driver2"
# back to project Root
cd ${ROOT}/src/livox_ros_driver2

#------------------------------------------------------------------------------
# build ROS2 package
./build.sh ${ROS_DISTRO}

# Load env
source ${ROOT}/install/setup.bash

cd ${ROOT}

# 选包编译： colcon build --packages-select fast_lio

#------------------------------------------------------------------------------
# How to run:
#------------------------------------------------------------------------------
# 加载包环境：
# source ~/TurboSLAM/install/setup.bash

#------------------------------------------------------------------------------
# start livox node
# 修改配置文件：
# vi livox_ros_driver2/config/MID360s_config.json

# 如果已经安装完毕后，直接更改该处配置
# ~/TurboSLAM/install/livox_ros_driver2/share/livox_ros_driver2/config/


#------------------------------------------------------------------------------
# 启动livox节点
# ros2 launch livox_ros_driver2 msg_MID360s_launch.py

#------------------------------------------------------------------------------
# start FastLIO node
# ros2 launch fast_lio mapping.launch.py config_file:=mid360.yaml
