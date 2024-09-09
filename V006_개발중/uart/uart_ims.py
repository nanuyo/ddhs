import serial
import time
import json
import os

# 시리얼 포트 설정 (포트 이름과 통신 속도 설정)
SERIAL_PORT = 'COM18'
BAUD_RATE = 115200
TIMEOUT = 1
MAX_RETRIES = 3  # 재전송 시도 최대 횟수

# JSON 파일이 저장될 기본 디렉토리 설정
BASE_DIRECTORY = "./"

# 매핑 테이블을 외부 JSON 파일에서 불러오기
MAPPING_TABLE_FILE = './mapping_table.json'

def load_mapping_table(mapping_file):
    """매핑 테이블을 JSON 파일에서 불러옵니다."""
    try:
        with open(mapping_file, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f'Failed to load mapping table: {e}')
        return {}

def initialize_serial(port, baud_rate, timeout):
    """시리얼 포트를 초기화합니다."""
    try:
        ser = serial.Serial(port, baud_rate, timeout=timeout)
        if not ser.is_open:
            ser.open()
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

def verify_checksum(data):
    """데이터의 체크섬을 확인합니다."""
    received_checksum = data[-1]
    calculated_checksum = calculate_checksum(data[:-1])
    if received_checksum != calculated_checksum:
        print(f"Checksum error: Received {received_checksum:02X}, Calculated {calculated_checksum:02X}.")
        return False
    return True

def force_incorrect_crc(data):
    """강제로 체크섬을 틀리게 만듭니다."""
    print(f"Original checksum: {data[-1]:02X}")
    corrupted_data = bytearray(data)
    corrupted_data[-1] = corrupted_data[-1] ^ 0xFF  # XOR 연산으로 체크섬 값 변경
    print(f"Corrupted checksum: {corrupted_data[-1]:02X}")
    return corrupted_data

def extract_data_fields(data, quantity):
    """수신된 데이터에서 필드를 추출합니다."""
    extracted_data = []
    for i in range(quantity):
        id_addr = f"{data[3 + i*4]:02X}{data[4 + i*4]:02X}"  # ID_ADDR을 16진수 문자열로 변환
        hex_value = f"{data[5 + i*4]:02X}{data[6 + i*4]:02X}"   # VALUE를 16진수 문자열로 변환
        dec_value = str(int(hex_value, 16))  # 10진수로 변환
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
        return False  # 체크섬이 맞지 않으면 실패 반환

    print(f"Start Code: {startcode:02X}")
    print(f"Set Info: {set_info:02X}")
    print(f"Quantity: {quantity:02X}")

    # 데이터 필드 추출
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

def send_retransmission_request(ser):
    """데이터 재전송을 요청하는 함수"""
    retransmission_request = b'\xD1\x41\x01\x45\x00'  # 예시 프레임: 슬레이브 주소 D1, 요청 프레임
    ser.write(retransmission_request)
    print("Retransmission request sent.")

def receive_data(ser, mapping_table, force_crc_error=False):
    """시리얼 포트로부터 데이터를 수신하고 처리합니다."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            header_data = ser.read(3)  # Start Code, Set Info, Quantity 읽기
            if header_data:
                startcode = header_data[0]
                set_info = header_data[1]
                quantity = header_data[2]
                data_length = 3 + quantity * 4 + 1  # 전체 패킷 길이 계산
                remaining_data = ser.read(data_length - 3)  # 나머지 데이터 읽기
                received_data = header_data + remaining_data
                print(f"Received raw data: {received_data}")  # 디버깅용 출력 추가
                
                # CRC 강제로 틀리게 만들기 (테스트용)
                if force_crc_error:
                    received_data = force_incorrect_crc(received_data)

                # 데이터 처리 시도
                if process_received_data(received_data, mapping_table):
                    return  # 데이터가 올바르게 처리되면 종료
                else:
                    # 체크섬 오류 발생 시 재전송 요청
                    retries += 1
                    print(f"Retry {retries}/{MAX_RETRIES}: Requesting retransmission due to checksum error.")
                    send_retransmission_request(ser)

        except Exception as e:
            print(f'Error receiving data: {e}')
            retries += 1

    print("Max retries reached. Discarding transmission.")

def main():
    """메인 함수."""
    mapping_table = load_mapping_table(MAPPING_TABLE_FILE)
    ser = initialize_serial(SERIAL_PORT, BAUD_RATE, TIMEOUT)

    try:
        while True:
            # 데이터 수신, force_crc_error=True로 설정하여 CRC 오류를 테스트
            receive_data(ser, mapping_table, force_crc_error=True)  # 수동으로 CRC 오류 테스트

            # 1초 대기
            time.sleep(1)

    except KeyboardInterrupt:
        print("Keyboard interrupt received. Closing serial port.")
    finally:
        if ser.is_open:
            ser.close()
            print("Serial port closed.")


if __name__ == "__main__":
    main()
