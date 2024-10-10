import serial
import json
import os
import threading
import time
import subprocess
import logging

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

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

### 공통 함수들 ###

def load_mapping_table(mapping_file):
    """매핑 테이블을 JSON 파일에서 불러옵니다."""
    if os.path.exists(mapping_file):
        logging.debug(f"File {mapping_file} exists.")
        try:
            with open(mapping_file, 'r') as file:
                content = file.read()  # 파일 내용을 읽어옴
                return json.loads(content)
        except json.JSONDecodeError as e:
            logging.error(f'JSON decoding error: {e}')
        except Exception as e:
            logging.error(f'Failed to load mapping table: {e}')
            return None
    else:
        logging.error(f"File {mapping_file} does not exist.")
        return None

def initialize_serial(port, baud_rate, timeout):
    """시리얼 포트를 초기화합니다."""
    try:
        ser = serial.Serial(port, baud_rate, timeout=timeout)
        if not ser.is_open:
            ser.open()
        logging.info(f"Serial port {port} initialized successfully.")
        return ser
    except Exception as e:
        logging.error(f'Failed to open serial port: {e}')
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

def execute_run_file(file_path):
    """지정된 .run 파일을 실행합니다."""
    try:
        subprocess.run([file_path], check=True)  # .run 파일 실행
        logging.info(f"Successfully executed: {file_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {file_path}: {e}")
    except FileNotFoundError as e:
        logging.error(f"File not found: {file_path}, Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error executing {file_path}: {e}")

### 수신 관련 함수 ###

def verify_checksum(data):
    """데이터의 체크섬을 확인합니다."""
    received_checksum = data[-1]
    calculated_checksum = calculate_checksum(data[:-1])
    if received_checksum != calculated_checksum:
        logging.error(f"Checksum error: Received {received_checksum:02X}, Calculated {calculated_checksum:02X}.")
        return False
    return True

def extract_data_fields(data, quantity):
    """수신된 데이터에서 필드를 추출하고 변환합니다."""
    extracted_data = []
    for i in range(quantity):
        id_addr = f"{data[3 + i*4]:02X}{data[4 + i*4]:02X}"  # ID_ADDR을 16진수 문자열로 변환
        hex_value = f"{data[5 + i*4]:02X}{data[6 + i*4]:02X}"  # VALUE를 16진수 문자열로 변환
        dec_value = int(hex_value, 16)  # 10진수로 변환
        extracted_data.append((id_addr, dec_value))
    return extracted_data

def save_data_to_file(file_path, key, value):
    """지정된 JSON 파일에 데이터를 저장합니다."""
    try:
        data = {}
        if os.path.exists(file_path):
            with open(file_path, 'r+') as json_file:
                try:
                    data = json.load(json_file)
                except json.JSONDecodeError:
                    logging.warning(f"Invalid JSON format in {file_path}, overwriting with new data.")
        
        data[key] = value

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        logging.info(f"Data successfully saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving data to {file_path}: {e}")

def process_received_data(data, mapping_table):
    """수신된 데이터 패킷을 처리하여 JSON 파일에 저장합니다."""
    startcode = data[0]
    set_info = data[1]
    quantity = data[2]
    
    if not verify_checksum(data):
        return False  # 체크섬이 맞지 않으면 처리 중단

    logging.debug(f"Start Code: {startcode:02X}")
    logging.debug(f"Set Info: {set_info:02X}")
    logging.debug(f"Quantity: {quantity:02X}")

    extracted_data = extract_data_fields(data, quantity)

    for id_addr, dec_value in extracted_data:
        # RUN SOFTAP when ID_ADDR is 0134 and dec_value is 1
        if id_addr == "0134" and dec_value == 1:
            run_file_path = '/usr/bin/ims/softap_restapi.run'
            logging.info(f"Executing .run file: {run_file_path} for id_addr {id_addr} and value {dec_value}")
            execute_run_file(run_file_path)
            continue  # softap 실행 후 다른 처리 건너뜀

        # 매핑 테이블 처리
        mapping = mapping_table.get(id_addr)
        if mapping:
            key = mapping["key"]
            file_name = mapping["file"]
            file_path = os.path.join(BASE_DIRECTORY, file_name)
            logging.info(f"Mapping found: {id_addr} -> {key}, saving to {file_path} with value {dec_value}")
            save_data_to_file(file_path, key, dec_value)
        else:
            logging.warning(f"Mapping for ID_ADDR {id_addr} not found.")

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
                
                if set_info != 0x40:
                    logging.warning(f"Invalid Set Info: {set_info:02X}. Expected 40. Discarding packet.")
                    continue
                
                data_length = 3 + quantity * 4 + 1  # 전체 패킷 길이 계산
                remaining_data = ser.read(data_length - 3)  # 나머지 데이터 읽기
                received_data = header_data + remaining_data
                logging.debug(f"Received raw data: {received_data}")

                process_received_data(received_data, mapping_table)

        except Exception as e:
            logging.error(f'Error receiving data: {e}')

### 송신 관련 함수 ###

def send_data_to_mcu(ser, register, value_bytes):
    """UART로 데이터를 MCU에 전송합니다."""
    try:
        startcode = bytes.fromhex('D1')
        set_info = bytes.fromhex('10')
        quantity = (1).to_bytes(1, byteorder='big')
        id_addr = bytes.fromhex(register)
        
        data_to_send = startcode + set_info + quantity + id_addr + value_bytes
        
        checksum = calculate_checksum(data_to_send)
        data_to_send += checksum.to_bytes(1, byteorder='big')
        
        ser.write(data_to_send)
        logging.info(f"Sent data to MCU: {data_to_send.hex()}")
    except Exception as e:
        logging.error(f"Error sending data to MCU: {e}")


def process_json_and_send(ser, send_mapping_table, json_data):
    """송신용 매핑 테이블을 참조하여 JSON 데이터를 UART로 전송."""
    send_data_list = []  # 전송할 데이터 목록을 저장하는 리스트

    for address, mapping in send_mapping_table.items():
        key_name = mapping.get('key')
        if key_name is None:
            continue

        if key_name in json_data:
            value = json_data[key_name]
            value_bytes = convert_value_to_bytes(value, 2)

            if value_bytes:
                send_data_list.append((address, value_bytes))

    quantity = len(send_data_list)

    if quantity > 0:
        startcode = bytes.fromhex('D1')  # Start Code
        set_info = bytes.fromhex('10')  # 세트 정보
        quantity_bytes = quantity.to_bytes(1, byteorder='big')

        data_to_send = startcode + set_info + quantity_bytes

        for address, value_bytes in send_data_list:
            id_addr = bytes.fromhex(address)
            data_to_send += id_addr + value_bytes

        checksum = calculate_checksum(data_to_send)
        data_to_send += checksum.to_bytes(1, byteorder='big')

        ser.write(data_to_send)
        logging.info(f"Sent data to MCU: {data_to_send.hex()}")
    else:
        logging.info("No data to send from JSON file {json_data}.")
        

def check_and_process_server_json(ser, send_mapping_table):
    """서버에서 받은 JSON 파일을 확인하고 처리."""
    try:
        for file_name in os.listdir(SERVER_JSON_DIR):
            if file_name.endswith('.json'):
                file_path = os.path.join(SERVER_JSON_DIR, file_name)
                try:
                    with open(file_path, 'r') as json_file:
                        json_data = json.load(json_file)
                        logging.info(f"Processing server JSON file: {file_name}")
                        process_json_and_send(ser, send_mapping_table, json_data)
                    
                    os.remove(file_path)
                    logging.info(f"Server JSON file {file_name} processed and removed.")
                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")
    except Exception as e:
        logging.error(f"Error accessing server JSON directory: {e}")

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
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE, TIMEOUT)
    
    mapping_table = load_mapping_table(MAPPING_TABLE_FILE)
    send_mapping_table = load_mapping_table(SEND_MAPPING_TABLE_FILE)
    
    uart_thread = start_uart_listener(ser, mapping_table)

    try:
        while True:
            check_and_process_server_json(ser, send_mapping_table)
            time.sleep(2)  # 매 2초마다 파일을 확인

    except KeyboardInterrupt:
        logging.info("Program interrupted. Exiting...")

    finally:
        stop_uart_listener()
        uart_thread.join(timeout=5)  # 스레드 종료를 위해 5초 대기
        if ser.is_open:
            ser.close()
        logging.info("Serial port closed.")

if __name__ == "__main__":
    main()