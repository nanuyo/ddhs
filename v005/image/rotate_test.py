import cv2
import os

# 현재 디렉토리 확인
current_directory = os.getcwd()
print(f"Current directory: {current_directory}")

# 테스트할 이미지 파일 경로
test_image_path = os.path.join(current_directory, 'image1.jpg')

# 파일 존재 여부 확인
if not os.path.isfile(test_image_path):
    print(f"File does not exist: {test_image_path}")
else:
    print(f"File exists: {test_image_path}")

# 파일 권한 확인
if not os.access(test_image_path, os.R_OK):
    print(f"File is not readable: {test_image_path}")
else:
    print(f"File is readable: {test_image_path}")

# 이미지를 로드합니다.
image = cv2.imread(test_image_path)

# 이미지를 제대로 로드했는지 확인합니다.
if image is None:
    print(f"Failed to load image at path {test_image_path}")
else:
    print(f"Image loaded successfully: {test_image_path}")
    print(f"Image shape: {image.shape}")
