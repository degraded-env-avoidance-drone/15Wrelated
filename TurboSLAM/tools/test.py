#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import time
import sys
import random
import string

def serial_loopback_test(port='/dev/ttyTHS1', baudrate=115200, timeout=1, test_data=None):
    """
    串口回环测试函数

    Args:
        port: 串口设备名称
        baudrate: 波特率
        timeout: 超时时间（秒）
        test_data: 测试数据（字节串），如果为None则自动生成
    """

    try:
        # 打开串口
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            write_timeout=timeout
        )

        # 检查串口是否打开
        if not ser.is_open:
            print(f"错误：无法打开串口 {port}")
            return False

        print(f"串口 {port} 已打开，波特率: {baudrate}")
        print("开始回环测试...")
        print("请确保已将串口的TX和RX引脚短接（回环）")
        print("-" * 50)

        # 如果未提供测试数据，生成随机测试数据
        if test_data is None:
            # 生成包含多种字符的测试数据
            test_str = "Hello, UART Loopback Test! 1234567890!@#$%^&*()"
            test_data = test_str.encode('utf-8')
        elif isinstance(test_data, str):
            test_data = test_data.encode('utf-8')

        # 清空缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # 执行回环测试
        print(f"发送数据: {test_data}")
        print(f"数据长度: {len(test_data)} 字节")

        # 发送数据
        bytes_written = ser.write(test_data)
        print(f"已发送 {bytes_written} 字节")

        # 等待数据返回
        time.sleep(0.5)  # 等待数据传输完成

        # 读取回环数据
        received_data = ser.read(len(test_data))

        # 验证数据
        if received_data:
            print(f"接收数据: {received_data}")
            print(f"接收长度: {len(received_data)} 字节")

            # 比较发送和接收的数据
            if received_data == test_data:
                print("✓ 回环测试通过：发送和接收数据完全一致")
                return True
            else:
                print("✗ 回环测试失败：数据不一致")
                # 显示差异
                for i, (sent_byte, recv_byte) in enumerate(zip(test_data, received_data)):
                    if sent_byte != recv_byte:
                        print(f"  字节 {i}: 发送 0x{sent_byte:02X}, 接收 0x{recv_byte:02X}")
                return False
        else:
            print("✗ 回环测试失败：未接收到任何数据")
            print("请检查：")
            print("  1. 串口线是否连接正确")
            print("  2. TX和RX引脚是否已经短接")
            print("  3. 波特率设置是否正确")
            return False

    except serial.SerialException as e:
        print(f"串口错误: {e}")
        print(f"请检查串口 {port} 是否存在且具有读写权限")
        return False
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        return False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

def run_extensive_test(port='/dev/ttyTHS1', baudrate=115200):
    """运行多次测试，验证稳定性"""
    print("=" * 50)
    print("开始扩展回环测试（10次）")
    print("=" * 50)

    success_count = 0
    test_data_list = [
        b"Short test",
        b"Long test data with various characters: 1234567890!@#$%^&*()_+-=",
        bytes([0x00, 0x01, 0x02, 0x7F, 0x80, 0xFF]),  # 包含特殊字节
        "中文测试数据".encode('utf-8'),
        b"Mixed\nData\tWith\r\nNewlines",
        b"1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        bytes(range(50)),  # 0-49 连续数据
        b" \t\n\r\f\v",  # 空白字符
        b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F",
        b"Test #10 - Final test data"
    ]

    for i, test_data in enumerate(test_data_list, 1):
        print(f"\n测试 #{i}:")
        if serial_loopback_test(port, baudrate, timeout=1, test_data=test_data):
            success_count += 1
        time.sleep(0.5)  # 测试间隔

    print("\n" + "=" * 50)
    print(f"测试完成: 成功 {success_count}/{len(test_data_list)}")
    if success_count == len(test_data_list):
        print("✓ 所有测试通过！")
    else:
        print(f"✗ 有 {len(test_data_list) - success_count} 个测试失败")
    print("=" * 50)

    return success_count == len(test_data_list)

if __name__ == "__main__":
    # 配置参数
    PORT = '/dev/ttyTHS3'
    BAUDRATE = 115200

    # 支持命令行参数
    if len(sys.argv) > 1:
        PORT = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            BAUDRATE = int(sys.argv[2])
        except ValueError:
            print(f"警告：波特率参数无效，使用默认值 {BAUDRATE}")

    print(f"串口回环测试工具")
    print(f"设备: {PORT}")
    print(f"波特率: {BAUDRATE}")
    print()

    # 首先执行单次测试
    print("执行单次回环测试...")
    result = serial_loopback_test(PORT, BAUDRATE)

    if result:
        print("\n是否进行扩展测试？(y/n): ", end="")
        response = input().strip().lower()
        if response == 'y' or response == 'yes':
            run_extensive_test(PORT, BAUDRATE)

    sys.exit(0 if result else 1)

