#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import serial
import time
import sys
import threading

def echo_loopback_test(port='/dev/ttyTHS1', baudrate=115200, timeout=1):
    """
    串口回环测试 - 收到什么就发送什么
    
    Args:
        port: 串口设备名称
        baudrate: 波特率
        timeout: 超时时间（秒）
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
        
        if not ser.is_open:
            print(f"错误：无法打开串口 {port}")
            return False
        
        print(f"串口 {port} 已打开，波特率: {baudrate}")
        print("=" * 60)
        print("回环模式：收到什么就发送什么")
        print("按 Ctrl+C 退出程序")
        print("=" * 60)
        
        # 清空缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        total_received = 0
        total_sent = 0
        
        while True:
            try:
                # 读取数据（非阻塞）
                if ser.in_waiting > 0:
                    # 读取所有可用的数据
                    data = ser.read(ser.in_waiting)
                    
                    if data:
                        total_received += len(data)
                        
                        # 显示接收到的数据
                        print(f"\n[接收] ({len(data)} 字节): {data}", end="")
                       
                        # 发送相同的数据（回环）
                        bytes_written = ser.write(data)
                        total_sent += bytes_written
                        
                        if bytes_written > 0:
                            print(f"[发送] ({bytes_written} 字节): 已回环")
                            print(f"统计: 接收 {total_received} 字节, 发送 {total_sent} 字节")
                        
                        # 小延迟避免发送过快
                        time.sleep(0.01)
                
                # 空闲等待
                time.sleep(0.001)
                
            except KeyboardInterrupt:
                print("\n\n收到退出信号...")
                break
            except serial.SerialException as e:
                print(f"\n串口错误: {e}")
                break
            except Exception as e:
                print(f"\n错误: {e}")
                break
        
        print(f"\n总计: 接收 {total_received} 字节, 发送 {total_sent} 字节")
        return True
        
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        print(f"请检查串口 {port} 是否存在且具有读写权限")
        return False
    except Exception as e:
        print(f"发生错误: {e}")
        return False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

def echo_with_timeout(port='/dev/ttyTHS1', baudrate=115200, timeout=10):
    """
    带超时的回环测试 - 等待指定时间后退出
    
    Args:
        port: 串口设备名称
        baudrate: 波特率
        timeout: 运行时间（秒），0表示无限运行
    """
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5
        )
        
        if not ser.is_open:
            print(f"错误：无法打开串口 {port}")
            return False
        
        print(f"串口 {port} 已打开，波特率: {baudrate}")
        print(f"回环模式：收到什么就发送什么")
        if timeout > 0:
            print(f"运行时间: {timeout} 秒")
        print("按 Ctrl+C 提前退出")
        print("=" * 60)
        
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        start_time = time.time()
        total_received = 0
        total_sent = 0
        
        while True:
            # 检查超时
            if timeout > 0 and (time.time() - start_time) > timeout:
                print(f"\n运行时间已到 ({timeout} 秒)")
                break
            
            try:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    print(f"\n[接收] ({len(data)} 字节): {data}", end="")
                    
                    if data:
                        total_received += len(data)
                        
                        # 显示接收到的数据
                        timestamp = time.time() - start_time
                        print(f"[{timestamp:.2f}s] 接收 {len(data)} 字节: ", end="")
                        
                        # 显示数据内容
                        try:
                            text = data.decode('utf-8', errors='replace')
                            # 移除换行等特殊字符的显示
                            display_text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                            print(f"{display_text}")
                        except:
                            print(f"0x{data.hex()}")
                        
                        # 发送回环数据
                        bytes_written = ser.write(data)
                        total_sent += bytes_written
                        print(f"  已回环发送 {bytes_written} 字节")
                        
                        time.sleep(0.01)
                
                time.sleep(0.001)
                
            except KeyboardInterrupt:
                print("\n\n用户中断")
                break
            except serial.SerialException as e:
                print(f"\n串口错误: {e}")
                break
        
        print(f"\n统计: 接收 {total_received} 字节, 发送 {total_sent} 字节")
        print(f"运行时间: {time.time() - start_time:.2f} 秒")
        return True
        
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        return False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

def test_echo_once(port='/dev/ttyTHS1', baudrate=115200):
    """
    单次回环测试 - 发送预定义数据并验证回环
    """
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=2,
            write_timeout=2
        )
        
        if not ser.is_open:
            print(f"错误：无法打开串口 {port}")
            return False
        
        print(f"串口 {port} 已打开，波特率: {baudrate}")
        print("单次回环测试模式")
        print("请确保串口TX和RX已短接")
        print("=" * 60)
        
        # 清空缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # 准备测试数据
        test_data = b"Hello UART Echo Test 1234567890"
        print(f"发送测试数据: {test_data}")
        print(f"数据长度: {len(test_data)} 字节")
        
        # 发送数据
        bytes_written = ser.write(test_data)
        print(f"已发送 {bytes_written} 字节")
        
        # 等待数据返回
        time.sleep(0.5)
        
        # 读取回环数据
        received_data = ser.read(len(test_data))
        
        if received_data:
            print(f"接收到数据: {received_data}")
            print(f"接收长度: {len(received_data)} 字节")
            
            if received_data == test_data:
                print("✓ 回环测试通过！")
                return True
            else:
                print("✗ 回环测试失败：数据不一致")
                # 显示差异
                min_len = min(len(test_data), len(received_data))
                for i in range(min_len):
                    if test_data[i] != received_data[i]:
                        print(f"  字节 {i}: 发送 0x{test_data[i]:02X}, 接收 0x{received_data[i]:02X}")
                if len(test_data) != len(received_data):
                    print(f"  数据长度不匹配: 发送 {len(test_data)} 字节, 接收 {len(received_data)} 字节")
                return False
        else:
            print("✗ 未接收到任何数据")
            print("请检查:")
            print("  1. TX和RX引脚是否已短接")
            print("  2. 串口连接是否正常")
            return False
            
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

if __name__ == "__main__":
    # 配置参数
    PORT = '/dev/ttyTHS1'
    BAUDRATE = 115200
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        PORT = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            BAUDRATE = int(sys.argv[2])
        except ValueError:
            print(f"警告：波特率参数无效，使用默认值 {BAUDRATE}")
    
    print("串口回环测试工具 - 收到什么就发送什么")
    print(f"设备: {PORT}, 波特率: {BAUDRATE}")
    print()
    
    print("请选择测试模式:")
    print("1. 单次回环测试 (发送预设数据并验证)")
    print("2. 持续回环模式 (无限运行，收到数据就回环)")
    print("3. 定时回环模式 (运行指定时间后自动退出)")
    print("4. 全部测试")
    
    choice = input("请选择 (1-4): ").strip()
    
    if choice == '1':
        test_echo_once(PORT, BAUDRATE)
    elif choice == '2':
        echo_loopback_test(PORT, BAUDRATE)
    elif choice == '3':
        try:
            seconds = input("请输入运行时间（秒）[默认10秒]: ").strip()
            timeout = int(seconds) if seconds else 10
            echo_with_timeout(PORT, BAUDRATE, timeout)
        except ValueError:
            print("输入无效，使用默认10秒")
            echo_with_timeout(PORT, BAUDRATE, 10)
    elif choice == '4':
        print("\n执行单次测试...")
        test_echo_once(PORT, BAUDRATE)
        time.sleep(1)
        print("\n执行持续回环测试（5秒后自动停止）...")
        echo_with_timeout(PORT, BAUDRATE, 5)
    else:
        print("无效选择，执行单次测试")
        test_echo_once(PORT, BAUDRATE)

