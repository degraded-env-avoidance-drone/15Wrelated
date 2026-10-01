# 解决 内存不足的问题，避免编译过程中出现类似如下错误：
# c++: fatal error: Killed signal terminated program cc1plus

# 创建分区路径
sudo mkdir -p /var/cache/swap/
# 设置分区的大小
# bs=64M是块大小，count=64是块数量，所以swap空间大小是bs*count
sudo dd if=/dev/zero of=/var/cache/swap/swap0 bs=64M count=128
# 设置该目录权限
sudo chmod 0600 /var/cache/swap/swap0
# 创建SWAP文件
sudo mkswap /var/cache/swap/swap0
# 激活SWAP文件
sudo swapon /var/cache/swap/swap0
# 查看SWAP信息是否正确
sudo swapon -s
