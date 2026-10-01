# FAST-LIO 2.0 参数调优指南

> 基于 TurboSLAM 项目的实践总结，覆盖 MID360 / Avia / Velodyne / Ouster 等主流雷达。

---

## 一、参数全景图

```
                               ┌─ common ───────── 话题 & 时间同步
                               │
config.yaml ── ros__parameters ─┤─ preprocess ────── 雷达类型 & 盲区
                               │
                               ├─ mapping ────────── IMU 协方差 & 外参
                               │
                               ├─ publish ─────────── 发布开关 (性能/调试)
                               │
                               ├─ pcd_save ────────── 地图保存
                               │
                               └─ 顶层参数 ─────────── max_iteration / filter / cube
```

---

## 二、核心参数详解

### 2.1 `max_iteration` — 迭代次数

| 场景 | 推荐值 | 效果 |
|------|--------|------|
| 室内/低动态 | 2 ~ 3 | 精度足够，处理更快 |
| 室外/高动态 | 4 | 收敛更充分 |
| 极低速扫描 | 5 | 点云稀疏时多迭代补偿 |

- MID360 在室内项目中使用 **3**（`mid360.yaml` 默认）
- 过大的值（>5）收益递减，徒增 CPU

---

### 2.2 降采样滤子（核心性能参数）

| 参数 | 作用 | 推荐值 |
|------|------|--------|
| `filter_size_surf` | 当前帧面点体素降采样 (m) | 0.2 ~ 1.0 |
| `filter_size_map` | 全局地图体素降采样 (m) | 0.2 ~ 1.0 |
| `point_filter_num` | 点云采样间隔（每隔 N 个点取一个） | 1 ~ 4 |
| `cube_side_length` | ikd-Tree 空间划分立方体边长 (m) | 100 ~ 2000 |

**调优策略**：

```
室内(小场景, <20m)  →  filter=0.2 ~ 0.3,  cube=200
室外(中场景, <100m) →  filter=0.5,         cube=1000   ← MID360 默认
大场景(>200m)       →  filter=0.8 ~ 1.0,  cube=2000
```

- **`filter_size`** 越小 → 更多特征点 → 精度更高但 CPU 翻倍
- **`cube_side_length`** 越小 → ikd-Tree 查找更快 → 但地图更新开销增大
- **`point_filter_num`** 是 raw point 级别的暴力降采样，CPU 敏感时优先调这个

---

### 2.3 IMU 噪声协方差 — 核心标定参数

| 参数 | 含义 | 默认 | 调参方向 |
|------|------|------|----------|
| `acc_cov` | 加速度计测量噪声方差 | 0.1 | 值越小 = 更信任 IMU 加速度 |
| `gyr_cov` | 陀螺仪测量噪声方差 | 0.1 | 值越小 = 更信任 IMU 角速度 |
| `b_acc_cov` | 加速度计 bias 随机游走 | 0.0001 | 值越小 = bias 估计变化越慢 |
| `b_gyr_cov` | 陀螺仪 bias 随机游走 | 0.0001 | 值越小 = bias 估计变化越慢 |

**实践准则**：

```
高质量 IMU (BMI088 / ICM-42688 等)：
  acc_cov=0.05,  gyr_cov=0.01,  b_acc_cov=1e-5,  b_gyr_cov=1e-5

普通 IMU (MPU6050 / ICM-20948 等)：
  acc_cov=0.2,   gyr_cov=0.1,   b_acc_cov=1e-4,  b_gyr_cov=1e-4

使用 LiDAR 内置 IMU (Livox)：
  acc_cov=0.1,   gyr_cov=0.1,   b_acc_cov=1e-4,  b_gyr_cov=1e-4  ← MID360 默认
```

**现象诊断**：

| 现象 | 原因 | 调整 |
|------|------|------|
| 位姿估计跳动大、不平滑 | IMU 噪声设太大 | 减小 `acc_cov` / `gyr_cov` |
| 轨迹漂移、累计误差大 | IMU 噪声设太小(过度信任) | 增大 `acc_cov` / `gyr_cov` |
| 静止时位姿在 "飘" | bias 协方差太小 | 增大 `b_*_cov` |
| bias 收敛过慢 | bias 协方差太大 | 减小 `b_*_cov` |

---

### 2.4 检测范围与 FOV

| 参数 | MID360 默认 | 说明 |
|------|-------------|------|
| `det_range` | 100.0 (m) | 超过此距离的点不参与匹配 |
| `fov_degree` | 360.0 | 有效 FOV 角度 |
| `blind` | 0.5 (m) | 盲区，小于此距离的点被丢弃 |

- **`det_range`** 减小 → 更少远处噪声点 → 精度提升但退化时更难恢复
- **`blind`** 增大 → 滤掉近距离自干扰（如机架反射），建议 0.3~1.0m
- **`fov_degree`** 建议填满雷达实际 FOV

---

### 2.5 外参估计

```yaml
extrinsic_est_en: true         # 开启在线外参估计
extrinsic_T: [x, y, z]         # LiDAR → IMU 平移 (在IMU系下)
extrinsic_R: [9个元素]          # LiDAR → IMU 旋转矩阵 (行主序)
```

| external_est_en | 适用场景 |
|-----------------|----------|
| `true` | 外参不精确、振动导致偏移、首次测试 |
| `false` | 外参已通过 LI_Init 精确标定、减少计算量 |

> **推荐**：先用 `true` 跑一两次收集收敛值，再固定为 `false`。

---

### 2.6 LiDAR 类型 (`preprocess.lidar_type`)

| 值 | 雷达厂商 | 配置要点 |
|----|---------|----------|
| 1 | Livox (Avia/MID360/Horizon) | `scan_line` 填 4/6，`timestamp_unit` 填 3 (ns) |
| 2 | Velodyne (VLP-16/HDL-32/HDL-64) | `scan_line` 填 16/32/64，`timestamp_unit` 填 2 (µs) |
| 3 | Ouster (OS1/OS2) | `scan_line` 填 64/128，`timestamp_unit` 填 3 (ns) |
| 4 | 通用点云 | 自行指定扫描线数 |

---

### 2.7 发布开关 (`publish.*`)

| 参数 | 推荐默认 | 说明 |
|------|----------|------|
| `path_en` | `true` | 发布轨迹 Path 消息 |
| `scan_publish_en` | `true` | 发布当前帧点云 |
| `scan_bodyframe_pub_en` | `true` | 发布 IMU 系下的点云 |
| `dense_publish_en` | `false` | 发布稠密全局点云（**带宽杀手**） |
| `map_en` | `true` | 发布地图点云 |
| `effect_map_en` | `false` | 发布有效性标记地图 |

**资源敏感场景**（Jetson/TX2）全关 `dense_publish_en` 和 `effect_map_en` 可省 30%~50% 网络和序列化开销。

---

### 2.8 PCD 保存

```yaml
pcd_save_en: true               # 开启
interval: -1                    # -1 = 全部帧合并成单个 PCD
map_file_path: "./map.pcd"      # 保存路径
```

- `interval: 100` = 每 100 帧存一个文件（适合长距离建图）
- `interval: -1` = 一个大文件（适合短程，注意内存溢出）

---

## 三、分场景调参速查

### 3.1 Livox MID360 + 室内 → 高精度

```yaml
feature_extract_enable: false     # FAST-LIO 2.0 直接处理 raw 点云
point_filter_num: 2               # 保留更多点
max_iteration: 3
filter_size_surf: 0.3             # 更细的体素
filter_size_map: 0.3
cube_side_length: 200.0           # 室内场景小
acc_cov: 0.05
gyr_cov: 0.01
b_acc_cov: 0.00001
b_gyr_cov: 0.00001
det_range: 50.0                   # 室内不需要远距离
blind: 0.3
extrinsic_est_en: false           # 外参确定后关闭
```

### 3.2 Livox MID360 + 室外 → 鲁棒

```yaml
point_filter_num: 3               # MID360 默认
max_iteration: 4
filter_size_surf: 0.5
filter_size_map: 0.5
cube_side_length: 1000.0
det_range: 100.0
blind: 0.5
extrinsic_est_en: true            # 室外振动多，持续估计
```

### 3.3 Velodyne HDL-32 + 室外建图

```yaml
lidar_type: 2
scan_line: 32
timestamp_unit: 2                 # 微秒
scan_rate: 10
max_iteration: 4
filter_size_surf: 0.5
filter_size_map: 0.8
cube_side_length: 2000.0
det_range: 150.0
blind: 2.0                        # Velodyne 有支架盲区
```

### 3.4 Ouster + 大场景

```yaml
lidar_type: 3
scan_line: 64
timestamp_unit: 3
cube_side_length: 3000.0
det_range: 200.0
filter_size_surf: 0.8
filter_size_map: 1.0
```

---

## 四、性能优化清单

| 操作 | 预期 CPU 降幅 | 副作用 |
|------|--------------|--------|
| `point_filter_num: 3 → 4` | ~20% | 特征点减少 |
| `filter_size_surf: 0.3 → 0.5` | ~15% | 地平面可能欠匹配 |
| `max_iteration: 4 → 3` | ~25% | 高动态精度略降 |
| `dense_publish_en: true → false` | ~10% | 无全局点云可视化 |
| `map_en: true → false` | ~5% | 无法看地图 |
| `extrinsic_est_en: true → false` | ~5% | 外参固定 |
| `cube_side_length: 200 → 1000` | ~10% | 大场景查找略慢 |

> **Jetson Orin NX / Xavier NX** 建议整套配置跑在 `point_filter_num=3, filter=0.5, max_iter=3` ，一般可到 30~50Hz。

---

## 五、常见问题排查

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| 启动后轨迹不更新 | IMU/LiDAR 话题不匹配 | 检查 `lid_topic` / `imu_topic` 是否与 ros2 topic list 一致 |
| 轨迹旋转/跳动 | 外参初始值错误 | 先用 LI_Init 标定，或开启 `extrinsic_est_en` |
| 建图"分层"或重影 | 时间同步问题 | 开启 `time_sync_en` 或硬件同步 |
| 轨迹逐渐漂移 | IMU 噪声协方差太小 | 增大 `acc_cov` / `gyr_cov` |
| 高速运动时丢失定位 | 迭代不收敛 | 增大 `max_iteration` (4→5) |
| CPU 100% 且丢帧 | 计算负载过大 | 执行上方性能优化清单 |
| 室内墙体重影 | `blind` 太小 | 增大 `blind` 到 0.8~1.0m |
| PCD 保存内存溢出 | `interval: -1` 单文件太大 | 设为 100~500 |
| Jetson 上 pts 时间戳全 0 | livox_ros_driver2 未用 CustomMsg | 改用 `msg_MID360_launch.py` 启动 |

---

## 六、标定工作流

```
1. 硬件安装 → 2. 初始外参 (手册值) → 3. LI_Init 精标定
                                            ↓
4. extrinsic_est_en=true 跑一次 → 5. 抄录收敛值 → 6. 固定外参
                                            ↓
7. 调整 IMU 协方差 (观察 Z 轴偏差) → 8. 调 filter 平衡精度/速度
                                            ↓
9. 固定所有参数 → 10. 部署到 systemd 自动启动
```

---

## 七、当前项目配置对照

| 参数 | MID360 生产配置 | 说明 |
|------|----------------|------|
| `max_iteration` | 3 | 室内场景，精度-速度平衡 |
| `point_filter_num` | 3 | 保留较多特征点 |
| `filter_size_surf` | 0.5 | 中等体素 |
| `filter_size_map` | 0.5 | |
| `cube_side_length` | 1000.0 | 覆盖室内外中等场景 |
| `acc_cov` / `gyr_cov` | 0.1 | MID360 内置 IMU |
| `det_range` | 100.0 | |
| `blind` | 0.5 | |
| `extrinsic_est_en` | true | 持续在线校正 |
