import serial
import json
import os
import threading
import time
import subprocess
import logging
import schedule

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_json_file(file_path):
    """JSON 파일을 읽고 내용을 반환합니다."""
    try:
        with open(file_path, 'r') as json_file:
            return json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read JSON file {file_path}: {e}")
        return {}

def load_mapping_table(mapping_file):
    """매핑 테이블 JSON 파일을 로드합니다."""
    if os.path.exists(mapping_file):
        logging.debug(f"File {mapping_file} exists.")
        try:
            with open(mapping_file, 'r') as file:
                content = file.read()
                return json.loads(content)
        except json.JSONDecodeError as e:
            logging.error(f'JSON decoding error: {e}')
        except Exception as e:
            logging.error(f'Failed to load mapping table: {e}')
            return None
    else:
        logging.error(f"File {mapping_file} does not exist.")
        return None

SERIAL_PORT = '/dev/ttyS3'
BAUD_RATE = 115200
TIMEOUT = 1

MAPPING_TABLE_FILE = '/usr/bin/ims/uart/mapping_table.json'
SEND_MAPPING_TABLE_FILE = '/usr/bin/ims/uart/send_mapping_table.json'
SERVER_JSON_DIR = '/usr/bin/ims/uart/from_server/'
BASE_DIRECTORY = '/usr/bin/ims/uart/to_server'
CAM_REQUEST_DIR = '/usr/bin/ims/uart/from_server'
LED_SET_JSON_PATH = os.path.join(BASE_DIRECTORY, 'set.json')

# 매핑 테이블 로드 (캐싱)
mapping_table = load_mapping_table(MAPPING_TABLE_FILE)
send_mapping_table = load_mapping_table(SEND_MAPPING_TABLE_FILE)

def initialize_serial(port, baud_rate, timeout):
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
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

def convert_value_to_bytes(value, length=2):
    return int(value).to_bytes(length, byteorder='big')

def save_data_to_file(file_path, key, value):
    try:
        data = load_json_file(file_path)
        data[key] = value
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        logging.info(f"Data successfully saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving data to {file_path}: {e}")

def send_data_to_mcu(ser, register, value_bytes):
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
    send_data_list = []

    for address, mapping in send_mapping_table.items():
        key_name = mapping.get('key')
        if key_name and key_name in json_data:
            value = json_data[key_name]
            value_bytes = convert_value_to_bytes(value, 2)
            if value_bytes:
                send_data_list.append((address, value_bytes))

    quantity = len(send_data_list)

    if quantity > 0:
        startcode = bytes.fromhex('D1')
        set_info = bytes.fromhex('10')
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
        logging.info("No data to send from JSON file")

def process_json_file(file_path, process_function, ser):
    """JSON 파일을 읽고 처리한 후 삭제합니다."""
    if os.path.exists(file_path):
        json_data = load_json_file(file_path)
        process_function(ser, json_data)
        os.remove(file_path)
        logging.info(f"Processed and deleted JSON file: {file_path}")

def set_led_state(room, state, setting_json_path):
    """LED 상태를 설정하고 JSON 파일을 업데이트합니다."""
    led_key = f"led_room{room}_a/m"
    control_key = f"led_control_room{room}"
    save_data_to_file(setting_json_path, led_key, state)
    save_data_to_file(setting_json_path, control_key, 100 if state else 0)
    logging.info(f"LED {'ON' if state else 'OFF'} for Room {room}")

def capture_room_image(rooms):
    """지정된 방의 이미지를 촬영합니다."""
    subprocess.run(['python3', '/usr/bin/ims/cam/IMS_cam.py'] + [str(room) for room in rooms], check=True)
    logging.info(f"Captured images for rooms: {', '.join(map(str, rooms))}")

def control_led_for_capture(room_no, ser):
    rooms = [int(r.strip()) for r in room_no.split(",") if r.strip().isdigit()]
    setting_json_path = os.path.join(SERVER_JSON_DIR, 'setting.json')

    if not os.path.exists(setting_json_path):
        with open(setting_json_path, 'w') as f:
            json.dump({}, f)
            logger.info(f"{setting_json_path} created.")

    for room in rooms:
        set_led_state(room, 1, setting_json_path)  # LED ON
    check_and_process_server_json(ser)  # MCU에 데이터 전송

    time.sleep(3)
    capture_room_image(rooms)  # 카메라 촬영

    time.sleep(15)
    for room in rooms:
        set_led_state(room, 0, setting_json_path)  # LED OFF
    check_and_process_server_json(ser)  # MCU에 데이터 전송

def check_for_requests(ser):
    file_path = os.path.join(CAM_REQUEST_DIR, "request.json")
    process_json_file(file_path, lambda s, d: control_led_for_capture(d.get("room_no", ""), s), ser)

def check_and_process_server_json(ser):
    file_path = os.path.join(SERVER_JSON_DIR, "setting.json")
    process_json_file(file_path, lambda s, d: process_json_and_send(s, send_mapping_table, d), ser)

def main():
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE, TIMEOUT)
    
    # 매시간 실행되는 스케줄 설정
    schedule.every(1).hours.do(lambda: control_led_for_capture("1,2,3", ser))
    
    # 프로그램 시작 직후 한 번 실행
    control_led_for_capture("1,2,3", ser)

    try:
        while True:
            check_for_requests(ser)
            check_and_process_server_json(ser)
            schedule.run_pending()
            time.sleep(2)

    except KeyboardInterrupt:
        logging.info("Program interrupted. Exiting...")

    finally:
        if ser.is_open:
            ser.close()
        logging.info("Serial port closed")

if __name__ == "__main__":
    main()
