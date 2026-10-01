sudo apt-get install -y ca-certificates curl gnupg lsb-release -y

# 创建用于存放密钥的目录
sudo install -m 0755 -d /etc/apt/keyrings

# 下载并安装 Docker 的 GPG 密钥
# curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
# 使用阿里云镜像下载 GPG 密钥
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加 Docker 官方软件源
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 1. 删除旧的 Docker 源文件
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -f /etc/apt/sources.list.d/docker-ce.list

# 2. 删除旧的 GPG 密钥
sudo rm -f /usr/share/keyrings/docker-archive-keyring.gpg
sudo rm -f /etc/apt/keyrings/docker.gpg

# 3. 重新创建密钥目录并下载公钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4. 重新添加 Docker 源（使用国内镜像加速）
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 更新软件包列表
sudo apt-get update

# 6. 安装 Docker
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker 服务并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker

# 通过运行测试容器验证安装是否成功
sudo docker run hello-world

# 拉取 Ubuntu 22.04 镜像
# docker pull ubuntu:22.04

# 创建并运行一个持续运行的开发容器
# docker run -it -d --name ubuntu22_dev --restart=unless-stopped ubuntu:22.04

# 查看所有容器：
# docker ps -a
# 停止容器：
# docker stop ubuntu22_dev
# 启动已停止的容器：
# docker start ubuntu22_dev
# 重新进入运行中的容器：
# docker exec -it ubuntu22_dev /bin/bash
# 在宿主机和容器间复制文件
# docker cp <宿主机路径> ubuntu22_dev:<容器路径>
