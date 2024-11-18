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

SERIAL_PORT = '/dev/ttyS3'
BAUD_RATE = 115200
TIMEOUT = 1

MAPPING_TABLE_FILE = '/usr/bin/ims/uart/mapping_table.json'
SEND_MAPPING_TABLE_FILE = '/usr/bin/ims/uart/send_mapping_table.json'
SERVER_JSON_DIR = '/usr/bin/ims/uart/from_server/'
BASE_DIRECTORY = '/usr/bin/ims/uart/to_server'
CAM_REQUEST_DIR = '/usr/bin/ims/uart/from_server'
LED_SET_JSON_PATH = os.path.join(BASE_DIRECTORY, 'set.json')

running = True

def load_mapping_table(mapping_file):
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

def check_and_process_server_json(ser, send_mapping_table):
    try:
        for file_name in os.listdir(SERVER_JSON_DIR):
            if file_name == "setting.json":
                file_path = os.path.join(SERVER_JSON_DIR, file_name)
                try:
                    json_data = load_json_file(file_path)
                    logging.info(f"Processing server JSON file: {file_name}")
                    process_json_and_send(ser, send_mapping_table, json_data)
                    os.remove(file_path)
                    logging.info(f"Server JSON file {file_name} deleted after processing.")
                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")
    except Exception as e:
        logging.error(f"Error accessing server JSON directory: {e}")

def control_led_for_capture(room_no, ser):
    rooms = [int(r.strip()) for r in room_no.split(",") if r.strip().isdigit()]
    setting_json_path = os.path.join(SERVER_JSON_DIR, 'setting.json')
    
    if not os.path.exists(setting_json_path):
        with open(setting_json_path, 'w') as f:
            json.dump({}, f)
            logger.info(f"{setting_json_path} created.")

    led_data = load_json_file(setting_json_path) or {}

    for room in rooms:
        led_key = f"led_room{room}_a/m"
        control_key = f"led_control_room{room}"
        
        led_data[led_key] = 1
        logging.info(f"LED ON for ROOM {room}")
        led_data[control_key] = 100
        logging.info(f"Control signal set for Room {room}")
        save_data_to_file(setting_json_path, led_key, 1)
        save_data_to_file(setting_json_path, control_key, 100)
    
    check_and_process_server_json(ser, load_mapping_table(SEND_MAPPING_TABLE_FILE))
    
    time.sleep(3)
    subprocess.run(['python3', '/usr/bin/ims/cam/IMS_cam.py'] + [str(room) for room in rooms], check=True)
    logging.info(f"Camera script executed for rooms: {', '.join(map(str, rooms))}")
    
    time.sleep(15)
    for room in rooms:
        led_key = f"led_room{room}_a/m"
        led_data[led_key] = 0
        logging.info(f"LED OFF for Room {room}")
        save_data_to_file(setting_json_path, led_key, 0)
    check_and_process_server_json(ser, load_mapping_table(SEND_MAPPING_TABLE_FILE))

def check_for_requests(ser):
    try:
        file_path = os.path.join(CAM_REQUEST_DIR, "request.json")
        if os.path.exists(file_path):
            request_data = load_json_file(file_path)
            if request_data and "room_no" in request_data:
                room_no = request_data["room_no"]
                control_led_for_capture(room_no, ser)
            logging.info(f"Processed request file: request.json")
            os.remove(file_path)
            logging.info(f"Request file request.json deleted after processing.")
    except Exception as e:
        logging.error(f"Error processing request file request.json: {e}")

def main():
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE, TIMEOUT)
    mapping_table = load_mapping_table(MAPPING_TABLE_FILE)
    send_mapping_table = load_mapping_table(SEND_MAPPING_TABLE_FILE)
    
    schedule.every(1).hours.do(lambda: control_led_for_capture("1,2,3", ser))

    try:
        while True:
            check_for_requests(ser)
            check_and_process_server_json(ser, send_mapping_table)
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
