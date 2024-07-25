from PIL import Image

# 이미지 열기
image_path = 'image1.jpg'  # 이미지 파일 경로를 입력하세요
image = Image.open(image_path)

# 이미지 회전 (시계 반대 방향으로 90도)
rotated_image = image.rotate(90, expand=True)

# 회전된 이미지 저장
rotated_image_path = 'rotated_image.jpg'  # 저장할 파일 경로를 입력하세요
rotated_image.save(rotated_image_path)

# 회전된 이미지 표시 (옵션)
rotated_image.show()
