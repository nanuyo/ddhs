import sys
import time
import logging
import cv2
import numpy as np
import os
import json
import subprocess

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 경로 설정
OUTPUT_DIR = "/usr/bin/ims/aws/toS3"  # 결과 이미지가 저장될 디렉토리
CAM_ERROR_FILE_PATH = "/usr/bin/ims/uart/to_server/cam_error.json"

# 방 번호에 따른 촬영 설정을 딕셔너리로 정의
room_settings = {
    '1': {"name": "Room1", "device": "/dev/video6"},
    '2': {"name": "Room2", "device": "/dev/video8"},
    '3': {"name": "Room3", "device": "/dev/video10"},
}

# 왜곡 보정 파라미터 값 설정
k1, k2, k3, p1, p2 = -0.2, 0.04, 0.0, 0.0, 0.0
cx, cy = 1082, 812
angle = 0

def undistort_image(img, camera_matrix, dist_coeffs):
    h, w = img.shape[:2]
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, (w, h), 1, (w, h))
    mapx, mapy = cv2.initUndistortRectifyMap(camera_matrix, dist_coeffs, None, new_camera_matrix, (w, h), 5)
    dst = cv2.remap(img, mapx, mapy, cv2.INTER_LANCZOS4)
    x, y, w, h = roi
    return dst[y:y+h, x:x+w]

def rotate_image(img, angle):
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR)

def update_camera_error(room_number):
    error_data = {
        "main_camera_uart_error": 0,
        "camera_room1_error": 0,
        "camera_room2_error": 0,
        "camera_room3_error": 0
    }

    # 파일이 존재하면 로드하여 현재 상태 유지
    if os.path.exists(CAM_ERROR_FILE_PATH):
        with open(CAM_ERROR_FILE_PATH, 'r') as f:
            try:
                error_data.update(json.load(f))
            except json.JSONDecodeError:
                logger.error("cam_error.json 파일이 손상되었습니다. 기본 상태로 재설정합니다.")

    # 해당 방의 오류 플래그를 1로 설정
    error_key = f"camera_room{room_number}_error"
    if error_key in error_data:
        error_data[error_key] = 1
    else:
        logger.warning(f"Invalid room number: {room_number}")

    with open(CAM_ERROR_FILE_PATH, 'w') as f:
        json.dump(error_data, f, indent=4)
    logger.info(f"cam_error.json 업데이트 완료: {error_key} = 1")

def capture_and_correct(room_number):
    room = room_settings.get(room_number)
    if room is None:
        logger.error(f"Invalid room number {room_number}. Cannot capture image.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)  # 출력 디렉토리 생성

    cap = cv2.VideoCapture(room["device"], cv2.CAP_V4L2)
    if not cap.isOpened():
        logger.error(f"Failed to open camera device for {room['name']}.")
        update_camera_error(room_number)  # 오류 업데이트
        return

    # 해상도 설정: 2164x1624
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2164)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1624)
    
    # AE 및 AWB 안정화를 위해 3초 대기
    time.sleep(3)
    
    ret, frame = cap.read()
    if not ret:
        logger.error(f"Failed to capture image for {room['name']}.")
        update_camera_error(room_number)  # 오류 업데이트
        cap.release()
        return

    # 자원 해제
    cap.release()

    # 왜곡 보정 및 회전 처리
    camera_matrix = np.array([[1000, 0, cx], [0, 1000, cy], [0, 0, 1]])
    dist_coeffs = np.array([k1, k2, p1, p2, k3])
    undistorted_img = undistort_image(frame, camera_matrix, dist_coeffs)
    final_img = rotate_image(undistorted_img, angle)
    
    # 파일 저장 (Room#_timestamp 형식)
    timestamp = time.strftime("%y%m%d%H%M")
    output_filename = os.path.join(OUTPUT_DIR, f"{room['name']}_{timestamp}.jpg")
    cv2.imwrite(output_filename, final_img)
    logger.info(f"Corrected image saved as {output_filename} for {room['name']}")

if __name__ == "__main__":
    # 인자가 없는 경우 방 1, 2, 3 모두 촬영, 있는 경우 해당 인자를 우선 촬영
    if len(sys.argv) < 2:
        logger.info("No specific room numbers provided. Capturing all rooms (1, 2, 3).")
        room_numbers = ["1", "2", "3"]
    else:
        room_numbers = sys.argv[1:]

    for room_number in room_numbers:
        capture_and_correct(room_number)

    try:
        logger.info("Starting IMS_S3.py for S3 upload...")
        subprocess.run(["python", "/usr/bin/ims/aws/IMS_S3.py"], check=True)
        logger.info("IMS_S3.py executed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute IMS_S3.py: {e}")

    sys.exit(0)
