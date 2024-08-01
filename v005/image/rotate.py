import cv2
import os

# 현재 디렉토리 확인
current_directory = os.getcwd()
print(f"Current directory: {current_directory}")

# 현재 디렉토리의 모든 파일 목록을 가져옵니다.
files = os.listdir(current_directory)

# 이미지 파일만 필터링합니다.
image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

# 각 이미지 파일에 대해 회전 작업을 수행합니다.
for image_file in image_files:
    # 이미지 파일의 절대 경로 생성
    image_path = os.path.join(current_directory, image_file)
    
    # 이미지를 로드합니다.
    image = cv2.imread(image_path)
    
    # 이미지를 제대로 로드했는지 확인합니다.
    if image is None:
        print(f"Failed to load image {image_file} at path {image_path}")
        continue
    
    # 이미지를 반시계 방향으로 90도 회전합니다.
    rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    # 회전된 이미지를 저장합니다.
    rotated_image_path = os.path.join(current_directory, f'rotated_{image_file}')
    result = cv2.imwrite(rotated_image_path, rotated_image)
    
    # 이미지 저장에 실패했는지 확인합니다.
    if not result:
        print(f"Failed to save rotated image {image_file}")
    
print("이미지 회전 작업이 완료되었습니다.")
