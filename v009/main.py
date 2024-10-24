import subprocess
import os
import logging
import urllib.request
import time

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 인터넷 연결 확인 함수
def is_internet_connected():
    try:
        # 구글에 요청을 보내 인터넷 연결 확인
        urllib.request.urlopen("http://www.google.com", timeout=1)
        return True
    except urllib.request.URLError as e:
        logger.warning(f"Internet connection error: {e}")
        return False

def main():
    # UART 실행
    uart_process = subprocess.Popen(['python3', '/usr/bin/ims/uart/IMS_uart.py'])
    logger.info("UART process started.")
    
    internet_connected = False
    provisioning_process = None  # 초기화
    mqtt_process = None  # 초기화

    while not internet_connected:
        # 인터넷 연결 확인
        if is_internet_connected():
            logger.info("Internet connection established.")
            internet_connected = True  # 연결이 되면 플래그를 True로 설정

            # 플릿 프로비저닝 실행
            provisioning_process = subprocess.Popen(['python3', '/usr/bin/ims/aws/IMS_fleet_provisioning.py'])
            provisioning_process.wait()  # 플릿 프로비저닝이 완료될 때까지 대기

            # 플릿 프로비저닝이 완료되면 MQTT 실행
            if provisioning_process.returncode == 0:  # 0이면 성공적으로 완료됨
                mqtt_process = subprocess.Popen(['python3', '/usr/bin/ims/aws/IMS_mqtt.py'])
                logger.info("MQTT process started.")
            else:
                logger.error("Fleet provisioning failed. MQTT process will not start.")
        else:
            logger.info("No internet connection. Retrying in 30 seconds...")
            time.sleep(30)  # 30초 대기

    try:
        # 모든 프로세스가 종료될 때까지 대기
        while True:
            if uart_process.poll() is not None:
                logger.info("UART process has ended.")
                break
            time.sleep(1)  # CPU 사용량을 줄이기 위해 대기
    except KeyboardInterrupt:
        logger.info("Program interrupted by user.")
    finally:
        uart_process.terminate()  # UART 프로세스를 종료
        if provisioning_process:
            provisioning_process.terminate()  # 플릿 프로비저닝 프로세스를 종료
        if mqtt_process:
            mqtt_process.terminate()  # MQTT 프로세스를 종료
        logger.info("All processes terminated.")

if __name__ == "__main__":
    main()
