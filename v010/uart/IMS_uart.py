import serial
import json
import os
import threading
import time
import subprocess
import logging
import queue

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 전역 변수 및 설정
SERIAL_PORT = '/dev/ttyS3'
BAUD_RATE = 115200
TIMEOUT = 1

MAPPING_TABLE_FILE = '/usr/bin/ims/uart/mapping_table.json'
SEND_MAPPING_TABLE_FILE = '/usr/bin/ims/uart/send_mapping_table.json'
SERVER_JSON_DIR = '/usr/bin/ims/uart/from_server/'
BASE_DIRECTORY = '/usr/bin/ims/uart/to_server'
CAM_REQUEST_DIR = '/usr/bin/ims/uart/from_server'
LED_SET_JSON_PATH = os.path.join(BASE_DIRECTORY, 'set.json')

ALARM_JSON_PATH = os.path.join(BASE_DIRECTORY, 'alarm.json')
ACTUATOR_JSON_PATH = os.path.join(BASE_DIRECTORY, 'actuator.json')

running = True
request_in_progress = False  # 요청 촬영 상태 플래그
task_queue = queue.Queue()  # 스케줄 작업 큐

### 유틸리티 함수 ###
def load_json_file(file_path):
    """JSON 파일을 읽고 내용을 반환합니다."""
    try:
        with open(file_path, 'r') as json_file:
            return json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read JSON file {file_path}: {e}")
        return {}

def save_data_to_file(file_path, key, value):
    """지정된 JSON 파일에 데이터를 저장합니다."""
    try:
        data = load_json_file(file_path)
        data[key] = value
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        logging.info(f"Data successfully saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving data to {file_path}: {e}")

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
    """주어진 값을 바이트로 변환합니다."""
    try:
        return int(value).to_bytes(length, byteorder='big')
    except ValueError as e:
        logger.error(f"Error converting value {value} to bytes: {e}")
        return None

def load_mapping_table(mapping_file):
    """매핑 테이블 JSON 파일을 로드합니다."""
    try:
        with open(mapping_file, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load mapping table {mapping_file}: {e}")
        return {}

### UART 데이터 송수신 ###
def process_received_data(data, mapping_table):
    """수신된 데이터를 처리하고 매핑 테이블에 따라 필요한 작업을 수행합니다."""
    try:
        startcode = data[0]
        set_info = data[1]
        quantity = data[2]

        if startcode != 0xD1 or set_info != 0x40:
            logger.warning(f"Invalid packet header: {startcode:02X}, {set_info:02X}")
            return False

        extracted_data = []
        for i in range(quantity):
            id_addr = f"{data[3 + i * 4]:02X}{data[4 + i * 4]:02X}"
            hex_value = f"{data[5 + i * 4]:02X}{data[6 + i * 4]:02X}"
            dec_value = int(hex_value, 16)
            extracted_data.append((id_addr, dec_value))

        for id_addr, dec_value in extracted_data:
            mapping = mapping_table.get(id_addr)
            if mapping:
                key = mapping.get("key")
                file_name = mapping.get("file")
                file_path = os.path.join(BASE_DIRECTORY, file_name)
                save_data_to_file(file_path, key, dec_value)
                logger.info(f"Processed ID_ADDR {id_addr} with value {dec_value}")
            else:
                logger.warning(f"No mapping found for ID_ADDR {id_addr}")
        return True
    except Exception as e:
        logger.error(f"Error processing received data: {e}")
        return False

def receive_data_and_save(ser, mapping_table):
    """시리얼 포트로부터 데이터를 수신하고 처리합니다."""
    global running
    while running:
        try:
            header_data = ser.read(3)
            if header_data:
                quantity = header_data[2]
                data_length = 3 + quantity * 4 + 1
                remaining_data = ser.read(data_length - 3)
                received_data = header_data + remaining_data
                process_received_data(received_data, mapping_table)
        except Exception as e:
            logger.error(f"Error receiving data: {e}")

### LED 제어 및 촬영 ###
def set_led_state(room, state, setting_json_path):
    """LED 상태를 설정하고 JSON 파일을 업데이트합니다."""
    led_key = f"led_room{room}_a/m"
    control_key = f"led_control_room{room}"
    save_data_to_file(setting_json_path, led_key, state)
    save_data_to_file(setting_json_path, control_key, 100 if state else 0)
    logger.info(f"LED {'ON' if state else 'OFF'} for Room {room}")

def capture_room_image(rooms):
    """지정된 방의 이미지를 촬영합니다."""
    subprocess.run(['python3', '/usr/bin/ims/cam/IMS_cam.py'] + [str(room) for room in rooms], check=True)
    logger.info(f"Captured images for rooms: {', '.join(map(str, rooms))}")

def control_led_for_capture(room):
    """LED를 제어하고 지정된 방의 이미지를 촬영합니다."""
    setting_json_path = os.path.join(SERVER_JSON_DIR, 'setting.json')
    if not os.path.exists(setting_json_path):
        with open(setting_json_path, 'w') as f:
            json.dump({}, f)
    set_led_state(room, 1, setting_json_path)
    time.sleep(3)
    capture_room_image([room])
    time.sleep(15)
    set_led_state(room, 0, setting_json_path)

### 요청 처리 ###
def check_for_requests(ser):
    """request.json 파일을 처리하여 요청 촬영을 수행."""
    global request_in_progress
    request_file = os.path.join(SERVER_JSON_DIR, "request.json")
    if os.path.exists(request_file):
        request_in_progress = True  # 요청 촬영 시작
        try:
            request_data = load_json_file(request_file)
            if "camera_no" in request_data:
                rooms = [int(r.strip()) for r in request_data["camera_no"].split(",") if r.strip().isdigit()]
                for room in rooms:
                    control_led_for_capture(room)  # 요청은 조건 무시하고 즉시 촬영
            os.remove(request_file)
            logger.info(f"Processed request.json")
        finally:
            request_in_progress = False  # 요청 촬영 완료

            # 요청 촬영 완료 후, 큐에서 보류된 작업 처리
            while not task_queue.empty():
                room = task_queue.get()
                logger.info(f"Resuming scheduled capture for Room {room}")
                check_conditions_and_capture(room)

### 스케줄 촬영 ###
def check_conditions_and_capture(room):
    """
    스케줄 작업 시 조건 확인:
    - 요청 촬영 중이면 작업을 큐에 보관.
    - 요청 촬영 완료 후 순차적으로 처리.
    """
    global request_in_progress
    if request_in_progress:
        logger.info(f"Request in progress. Adding Room {room} to task queue.")
        task_queue.put(room)  # 요청 중일 경우 큐에 작업 추가
        return

    # 조건 확인
    alarm_data = load_json_file(ALARM_JSON_PATH)
    if alarm_data.get("door_open_alarm") == 1:
        logger.info(f"door_open_alarm is 1. Skipping scheduled capture for Room {room}.")
        return

    actuator_data = load_json_file(ACTUATOR_JSON_PATH)
    led_key = f"led_room{room}"
    if actuator_data.get(led_key) == 0:
        logger.info(f"{led_key} is 0. Skipping scheduled capture for Room {room}.")
        return

    # 조건 충족 시 촬영 진행
    control_led_for_capture(room)

def setup_room_capture_schedule():
    """set.json 파일을 확인하여 스케줄을 설정."""
    set_data = load_json_file(LED_SET_JSON_PATH)
    for room in range(1, 4):  # Room 1, 2, 3
        mode_key = f"mode_set_room{room}"
        if set_data.get(mode_key) == 1:
            logger.info(f"Scheduling capture for Room {room} every hour.")
            threading.Timer(3600, lambda: check_conditions_and_capture(room)).start()

### 메인 ###
def main():
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE, TIMEOUT)
    mapping_table = load_mapping_table(MAPPING_TABLE_FILE)
    send_mapping_table = load_mapping_table(SEND_MAPPING_TABLE_FILE)
    uart_thread = threading.Thread(target=receive_data_and_save, args=(ser, mapping_table))
    uart_thread.start()
    try:
        setup_room_capture_schedule()  # 스케줄 설정
        while True:
            check_for_requests(ser)
            time.sleep(2)
    except KeyboardInterrupt:
        global running
        running = False
        uart_thread.join(timeout=5)
    finally:
        if ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
