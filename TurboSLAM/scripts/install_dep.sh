#!/bin/bash

sudo apt update 
sudo apt install -y  git cmake build-essential
sudo apt install -y  libatlas-base-dev
sudo apt install -y  libboost-all-dev
sudo apt install -y  libeigen3-dev
sudo apt install -y  libgflags-dev
sudo apt install -y  libgoogle-glog-dev
sudo apt install -y  libpcl-dev
sudo apt install -y  libtbb-dev
sudo apt install -y  libwebsocketpp-dev
sudo apt install -y  python3-pip
sudo apt install -y  python3-colcon-common-extensions
sudo apt install -y  python3-rosdep
sudo apt install -y  libgflags-dev
sudo apt install -y  libunwind-dev
sudo apt install -y  libgoogle-glog-dev
sudo apt install -y  libopencv-dev
sudo apt install -y  libpcap-dev libepoxy-dev libopenexr-dev
sudo apt install -y  libpcl-dev
sudo apt install -y  libyaml-cpp-dev
sudo apt install -y  pcl-tools
sudo apt install -y  ros-${ROS_DISTRO}-pcl-conversions
sudo apt install -y  ros-${ROS_DISTRO}-pcl-ros
sudo apt install -y  ros-${ROS_DISTRO}-rmw-cyclonedds-cpp
sudo apt install -y  ros-${ROS_DISTRO}-foxglove-bridge
sudo apt install -y  tmux tmuxinator
pip install pymavlink -i https://mirrors.aliyun.com/pypi/simple/
pip install pyserial -i https://mirrors.aliyun.com/pypi/simple/
sudo apt autoremove -y
