import serial
import time

# 시리얼 포트 설정 (포트 이름과 통신 속도 설정)
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    if not ser.is_open:
        ser.open()
except Exception as e:
    print(f'Failed to open serial port: {e}')
    exit(1)

def send_data(data):
    if ser.is_open:
        try:
            ser.write(data.encode()) 
        except Exception as e:
            print(f'Error sending data: {e}')

def receive_data():
    if ser.is_open:
        try:
            received_data = ser.readline()
            if received_data:
                decoded_data = received_data.decode().strip()
                return decoded_data
            else:
                return None
        except Exception as e:
            print(f'Error receiving data: {e}')
            return None

try:
    while True:
        # 데이터 전송
        data_to_send = 'APPLE'
        send_data(data_to_send)
        print(f'send: {data_to_send}')

        # 데이터 수신
        received = receive_data()
        if received:
            print(f'received: {received}')
        else:
            print('received: No data received')

        # 1초 대기
        time.sleep(1)
        
except KeyboardInterrupt:
    print("Keyboard interrupt received. Closing serial port.")
finally:
    if ser.is_open:
        ser.close()
        print("Serial port closed.")
