import serial
import threading
import time

# Basic configuration
RECEIVE_PORT = '/dev/ttyTHS1'
BAUDRATE = 921600

def receive_data():
    try:
        # Setup serial port
        with serial.Serial(RECEIVE_PORT, BAUDRATE, timeout=1) as ser:
            print(f"Receiving on {RECEIVE_PORT}...")
            
            while True:
                # Read incoming data
                if ser.in_waiting:
                    data = ser.read_all()
                    print(f"Received: {data}")
                time.sleep(0.01)
                
    except Exception as e:
        print(f"Receive error: {e}")

if __name__ == "__main__":
    print("Simple Serial Communicator")
    print("Press Ctrl+C to stop\n")
    
    # Start communication threads
    threading.Thread(target=receive_data, daemon=True).start()
    
    # Keep program running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped")
