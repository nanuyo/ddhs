from PIL import Image
import os

# 현재 디렉토리의 모든 파일 목록을 가져옵니다.
files = os.listdir('.')

# 이미지 파일만 필터링합니다.
image_files = [file for file in files if file.lower().endswith(('.jpg', '.jpeg', '.png'))]

# 각 이미지 파일에 대해 회전 작업을 수행합니다.
for image_file in image_files:
    try:
        # 이미지를 로드합니다.
        with Image.open(image_file) as img:
            # 이미지를 반시계 방향으로 90도 회전합니다.
            rotated_img = img.rotate(90, expand=True)
            # 회전된 이미지를 저장합니다.
            rotated_img.save(f'rotated_{image_file}')
        print(f"Successfully rotated image {image_file}")
    except Exception as e:
        print(f"Failed to process image {image_file}: {e}")

print("이미지 회전 작업이 완료되었습니다.")
