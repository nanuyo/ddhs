import serial
import json
import os
import threading
import time

# 시리얼 포트 설정 (포트 이름과 통신 속도 설정)
SERIAL_PORT = '/dev/ttyS3'
BAUD_RATE = 115200
TIMEOUT = 1

# JSON 파일 경로와 매핑 테이블 파일 경로
MAPPING_TABLE_FILE = './mapping_table.json'  # 수신용 mapping table
SEND_MAPPING_TABLE_FILE = './send_mapping_table.json'  # 송신용 mapping table
SERVER_JSON_DIR = './send_data/'  # 서버에서 받은 JSON 파일이 저장되는 디렉토리
BASE_DIRECTORY = './'  # 수신 데이터 저장 기본 디렉토리

# UART 수신 상태 플래그
running = True

### 공통 함수들 ###

def load_mapping_table(mapping_file):
    """매핑 테이블을 JSON 파일에서 불러옵니다."""
    if os.path.exists(mapping_file):
        print(f"File {mapping_file} exists.")
        try:
            with open(mapping_file, 'r') as file:
                content = file.read()  # 파일 내용을 읽어옴
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f'JSON decoding error: {e}')
        except Exception as e:
            print(f'Failed to load mapping table: {e}')
            return None
    else:
        print(f"File {mapping_file} does not exist.")
        return None

def initialize_serial(port, baud_rate, timeout):
    """시리얼 포트를 초기화합니다."""
    try:
        ser = serial.Serial(port, baud_rate, timeout=timeout)
        if not ser.is_open:
            ser.open()
        print(f"Serial port {port} initialized successfully.")
        return ser
    except Exception as e:
        print(f'Failed to open serial port: {e}')
        exit(1)

def calculate_checksum(data):
    """체크섬 계산 (XOR 연산)"""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def convert_value_to_bytes(value, length=2):
    """주어진 값을 2바이트로 변환합니다."""
    return int(value).to_bytes(length, byteorder='big')

### 수신 관련 함수 ###

def verify_checksum(data):
    """데이터의 체크섬을 확인합니다."""
    received_checksum = data[-1]
    calculated_checksum = calculate_checksum(data[:-1])
    if received_checksum != calculated_checksum:
        print(f"Checksum error: Received {received_checksum:02X}, Calculated {calculated_checksum:02X}.")
        return False
    return True

def extract_data_fields(data, quantity):
    """수신된 데이터에서 필드를 추출하고 변환합니다."""
    extracted_data = []
    for i in range(quantity):
        id_addr = f"{data[3 + i*4]:02X}{data[4 + i*4]:02X}"  # ID_ADDR을 16진수 문자열로 변환
        hex_value = f"{data[5 + i*4]:02X}{data[6 + i*4]:02X}"  # VALUE를 16진수 문자열로 변환
        
        # 변환 작업 (16진수를 10진수로 변환하여 처리)
        dec_value = int(hex_value, 16)  # 10진수로 변환

        extracted_data.append((id_addr, dec_value))
    return extracted_data

def save_data_to_file(file_path, key, value):
    """지정된 JSON 파일에 데이터를 저장합니다."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r+') as json_file:
                try:
                    data = json.load(json_file)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # 데이터에 새로운 값을 추가 또는 기존 값을 업데이트
        data[key] = value

        # JSON 파일에 전체 데이터를 다시 저장
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Data successfully saved to {file_path}")
    except Exception as e:
        print(f"Error saving data to {file_path}: {e}")

def process_received_data(data, mapping_table):
    """수신된 데이터 패킷을 처리하여 JSON 파일에 저장합니다."""
    startcode = data[0]
    set_info = data[1]
    quantity = data[2]
    
    # 체크섬 검증
    if not verify_checksum(data):
        return False  # 체크섬이 맞지 않으면 처리 중단

    print(f"Start Code: {startcode:02X}")
    print(f"Set Info: {set_info:02X}")
    print(f"Quantity: {quantity:02X}")

    # 데이터 필드 추출 및 변환
    extracted_data = extract_data_fields(data, quantity)

    # 매핑 테이블을 참조하여 데이터를 저장
    for id_addr, dec_value in extracted_data:
        mapping = mapping_table.get(id_addr)
        if mapping:
            key = mapping["key"]
            file_name = mapping["file"]
            file_path = os.path.join(BASE_DIRECTORY, file_name)
            print(f"Mapping found: {id_addr} -> {key}, saving to {file_path} with value {dec_value}")
            save_data_to_file(file_path, key, dec_value)
        else:
            print(f"Mapping for ID_ADDR {id_addr} not found.")

    return True  # 처리 성공

def receive_data_and_save(ser, mapping_table):
    """시리얼 포트로부터 데이터를 수신하고 처리합니다."""
    while running:
        try:
            header_data = ser.read(3)  # Start Code, Set Info, Quantity 읽기
            if header_data:
                startcode = header_data[0]
                set_info = header_data[1]
                quantity = header_data[2]
                
                # Set Info 값 40 확인
                if set_info != 0x40:
                    print(f"Invalid Set Info: {set_info:02X}. Expected 40. Discarding packet.")
                    continue
                
                data_length = 3 + quantity * 4 + 1  # 전체 패킷 길이 계산
                remaining_data = ser.read(data_length - 3)  # 나머지 데이터 읽기
                received_data = header_data + remaining_data
                print(f"Received raw data: {received_data}")  # 디버깅용 출력 추가

                # 데이터 처리
                process_received_data(received_data, mapping_table)

        except Exception as e:
            print(f'Error receiving data: {e}')

### 송신 관련 함수 ###

def send_data_to_mcu(ser, register, value_bytes):
    """UART로 데이터를 MCU에 전송합니다."""
    try:
        # 데이터 구조 생성
        startcode = bytes.fromhex('D1')  # Start Code
        set_info = bytes.fromhex('10')  # 세트 정보
        quantity = (1).to_bytes(1, byteorder='big')  # 수량 (이 예시에서는 1)
        id_addr = bytes.fromhex(register)  # ID Addr (레지스터 값)
        
        # 데이터 조합
        data_to_send = startcode + set_info + quantity + id_addr + value_bytes
        
        # 체크섬 계산 (XOR)
        checksum = calculate_checksum(data_to_send)
        data_to_send += checksum.to_bytes(1, byteorder='big')  # 체크섬 추가
        
        # UART로 데이터 전송
        ser.write(data_to_send)
        print(f"Sent data to MCU: {data_to_send.hex()}")
    except Exception as e:
        print(f"Error sending data to MCU: {e}")

def process_json_and_send(ser, send_mapping_table, json_data):
    """송신용 매핑 테이블을 참조하여 JSON 데이터를 UART로 전송."""
    send_data_list = []  # 전송할 데이터 목록을 저장하는 리스트

    for address, mapping in send_mapping_table.items():  # address가 키 역할
        key_name = mapping.get('key')  # 매핑 테이블에서 key 가져오기
        if key_name is None:
            # print(f"Key is missing for address {address}, skipping.")
            continue

        # 디버깅용 출력 추가: key가 제대로 있는지 확인
        # print(f"Checking if key '{key_name}' exists in JSON data...")

        if key_name in json_data:  # JSON 데이터에 해당 키가 있는 경우에만 처리
            value = json_data[key_name]  # JSON 데이터에서 값을 가져옴
            # print(f"Key '{key_name}' found in JSON data with value: {value}")

            value_bytes = convert_value_to_bytes(value, 2)  # 값을 2바이트로 변환

            if value_bytes:
                send_data_list.append((address, value_bytes))
        else:
            # print(f"Key '{key_name}' not found in JSON data, skipping.")
            pass

    quantity = len(send_data_list)

    if quantity > 0:
        startcode = bytes.fromhex('D1')  # Start Code
        set_info = bytes.fromhex('10')  # 세트 정보
        quantity_bytes = quantity.to_bytes(1, byteorder='big')  # 수량(전송할 레지스터 개수)

        data_to_send = startcode + set_info + quantity_bytes

        for address, value_bytes in send_data_list:
            id_addr = bytes.fromhex(address)  # 레지스터 주소 (address는 16진수 문자열)
            data_to_send += id_addr + value_bytes  # 주소와 값 결합

        checksum = calculate_checksum(data_to_send)
        data_to_send += checksum.to_bytes(1, byteorder='big')

        ser.write(data_to_send)
        print(f"Sent data to MCU: {data_to_send.hex()}")
    else:
        print("No data to send.")

def check_and_process_server_json(ser, send_mapping_table):
    """서버에서 받은 JSON 파일을 확인하고 처리."""
    try:
        for file_name in os.listdir(SERVER_JSON_DIR):
            if file_name.endswith('.json'):
                file_path = os.path.join(SERVER_JSON_DIR, file_name)
                try:
                    with open(file_path, 'r') as json_file:
                        json_data = json.load(json_file)
                        print(f"Processing server JSON file: {file_name}")
                        process_json_and_send(ser, send_mapping_table, json_data)
                    
                    # 전송이 완료되면 파일 삭제
                    # os.remove(file_path)
                    # print(f"Server JSON file {file_name} processed and removed.")
                except Exception as e:
                    print(f"Error processing file {file_name}: {e}")
    except Exception as e:
        print(f"Error accessing server JSON directory: {e}")

### UART 수신 스레드 ###

def start_uart_listener(ser, mapping_table):
    """UART 수신을 별도의 스레드로 실행"""
    uart_thread = threading.Thread(target=receive_data_and_save, args=(ser, mapping_table))
    uart_thread.start()
    return uart_thread

def stop_uart_listener():
    """UART 수신 스레드 종료"""
    global running
    running = False

### 메인 함수 ###

def main():
    # UART 초기화
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE, TIMEOUT)
    
    # 매핑 테이블 로드
    mapping_table = load_mapping_table(MAPPING_TABLE_FILE)
    send_mapping_table = load_mapping_table(SEND_MAPPING_TABLE_FILE)
    
    # UART 수신 시작 (별도의 스레드에서)
    uart_thread = start_uart_listener(ser, mapping_table)

    try:
        while True:
            # 서버에서 받은 JSON 파일을 주기적으로 확인하고 처리
            check_and_process_server_json(ser, send_mapping_table)  # 여기서 send_mapping_table을 사용
            time.sleep(2)  # 매 2초마다 파일을 확인

    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")

    finally:
        # UART 수신 종료
        stop_uart_listener()
        uart_thread.join()
        if ser.is_open:
            ser.close()
        print("Serial port closed.")

if __name__ == "__main__":
    main()
