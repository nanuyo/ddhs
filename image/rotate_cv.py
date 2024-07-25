import cv2

# 이미지 열기
image_path = 'image1.jpg'  # 이미지 파일 경로를 입력하세요
image = cv2.imread(image_path)

# 이미지가 제대로 로드되었는지 확인
if image is None:
    raise ValueError(f"Failed to load the image from {image_path}.")
    
# 이미지 회전 (시계 반대 방향으로 90도)
rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

# 회전된 이미지 저장
rotated_image_path = 'rotated_cv_image.jpg'  # 저장할 파일 경로를 입력하세요
cv2.imwrite(rotated_image_path, rotated_image)

# 회전된 이미지 표시 (옵션)
cv2.imshow('Rotated Image', rotated_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
