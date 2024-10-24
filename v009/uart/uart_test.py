import serial
import time
import threading

# 시리얼 포트 설정 (포트 이름과 통신 속도 설정)
try:
    ser = serial.Serial('COM13', 115200, timeout=1)
    if not ser.is_open:
        ser.open()
except Exception as e:
    print(f'Failed to open serial port: {e}')
    exit(1)

def send_data(data):
    if ser.is_open:
        try:
            data_with_delimiter = f"<DATA>{data}</DATA>\n"  # 데이터에 구분자 추가
            ser.write(data_with_delimiter.encode('utf-8'))  # 데이터 전송
            print(f"Data sent: {data}")
        except Exception as e:
            print(f'Error sending data: {e}')

def receive_data():
    if ser.is_open:
        try:
            received_data = ser.readline()  # '\n'으로 끝나는 한 줄 수신
            if received_data:
                try:
                    decoded_data = received_data.decode('utf-8').strip()  # 수신된 데이터 디코딩
                    return decoded_data
                except UnicodeDecodeError:
                    print(f"Decoding error: Received raw data: {received_data}")
                    return None
            else:
                return None
        except Exception as e:
            print(f'Error receiving data: {e}')
            return None

def sender():
    while True:
        data_to_send = bytes.fromhex("D140010086000117")
        ser.write(data_to_send)
        print(f"Data sent: {data_to_send.hex().upper()}")
        time.sleep(10)

def receiver():
    
    while True:
        # 데이터 수신
        received = receive_data()
        if received:
            print(f'received: {received}')
        else:
            print('received: No valid data received')
        time.sleep(1)

try:
    # 송신과 수신을 동시에 처리하기 위한 스레드 생성
    sender_thread = threading.Thread(target=sender)
    receiver_thread = threading.Thread(target=receiver)

    # 두 스레드를 데몬 스레드로 설정하여 메인 프로그램 종료 시 함께 종료되도록 함
    sender_thread.daemon = True
    receiver_thread.daemon = True

    # 스레드 실행
    sender_thread.start()
    receiver_thread.start()

    # 메인 스레드는 계속 실행되도록 유지
    while True:
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Keyboard interrupt received. Closing serial port.")
finally:
    if ser.is_open:
        ser.close()
        print("Serial port closed.")
