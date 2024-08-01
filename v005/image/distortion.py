import cv2
import numpy as np

# 이미지 보정 함수 (확대 및 자르기 포함)
def undistort_image(img, camera_matrix, dist_coeffs):
    h, w = img.shape[:2]
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, (w, h), 1, (w, h))
    dst = cv2.undistort(img, camera_matrix, dist_coeffs, None, new_camera_matrix)
    
    # 잘린 영역(ROI) 적용
    x, y, w, h = roi
    dst = dst[y:y+h, x:x+w]
    
    return dst

# 격자 그리기 함수
def draw_grid(img, grid_size=20):
    h, w = img.shape[:2]
    for i in range(0, w, grid_size):
        cv2.line(img, (i, 0), (i, h), (255, 255, 255), 1)
    for j in range(0, h, grid_size):
        cv2.line(img, (0, j), (w, j), (255, 255, 255), 1)
    return img

# 텍스트 그리기 함수
def draw_text(img, text, position=(30, 30), font_scale=1, color=(0, 0, 255), thickness=2):
    cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

# 트랙바 콜백 함수
def update(val):
    # 트랙바에서 현재 값을 읽어옴
    k1 = cv2.getTrackbarPos('k1', 'Trackbars') / 1000.0 - 1.0
    k2 = cv2.getTrackbarPos('k2', 'Trackbars') / 1000.0 - 1.0
    k3 = cv2.getTrackbarPos('k3', 'Trackbars') / 1000.0 - 1.0
    p1 = cv2.getTrackbarPos('p1', 'Trackbars') / 1000.0 - 0.5
    p2 = cv2.getTrackbarPos('p2', 'Trackbars') / 1000.0 - 0.5
    cx = cv2.getTrackbarPos('cx', 'Trackbars')
    cy = cv2.getTrackbarPos('cy', 'Trackbars')
    grid_on = cv2.getTrackbarPos('Grid ON/OFF', 'Trackbars')
    
    # 카메라 매트릭스 업데이트
    camera_matrix[0, 2] = cx
    camera_matrix[1, 2] = cy
    
    # 왜곡 계수 업데이트
    dist_coeffs = np.array([k1, k2, p1, p2, k3])
    undistorted_img = undistort_image(img, camera_matrix, dist_coeffs)
    
    if undistorted_img is None or undistorted_img.size == 0:
        print("Error: Undistorted image is empty.")
        return
    
    # 이미지 크기 조정 (예: 가로 800픽셀)
    resized_img = cv2.resize(undistorted_img, (800, int(800 * undistorted_img.shape[0] / undistorted_img.shape[1])))
    
    # 격자 ON/OFF
    if grid_on:
        resized_img = draw_grid(resized_img)
    
    # 왜곡 계수 및 카메라 중심 텍스트 표시
    draw_text(resized_img, f'k1: {k1:.4f}', (10, 20))
    draw_text(resized_img, f'k2: {k2:.4f}', (10, 50))
    draw_text(resized_img, f'k3: {k3:.4f}', (10, 80))
    draw_text(resized_img, f'p1: {p1:.4f}', (10, 110))
    draw_text(resized_img, f'p2: {p2:.4f}', (10, 140))
    draw_text(resized_img, f'cx: {cx}', (10, 170))
    draw_text(resized_img, f'cy: {cy}', (10, 200))
    
    # 이미지 표시
    cv2.imshow('Image', resized_img)
    
    # 트랙바 값 출력
    print(f"Distortion coefficients: k1={k1:.4f}, k2={k2:.4f}, k3={k3:.4f}, p1={p1:.4f}, p2={p2:.4f}, cx={cx}, cy={cy}, grid_on={grid_on}")

# 원본 이미지 로드
img = cv2.imread('rotated_distortion.jpg')
if img is None:
    print("Error: Failed to load image.")
    exit()

h, w = img.shape[:2]

# 초기 카메라 매트릭스와 왜곡 계수 (예시 값 사용)
camera_matrix = np.array([[1000, 0, w / 2],
                          [0, 1000, h / 2],
                          [0, 0, 1]])
dist_coeffs = np.array([-0.2, 0.1, 0, 0, 0])

# 창 생성
cv2.namedWindow('Trackbars')
cv2.namedWindow('Image')

# 창 크기와 위치 조정
cv2.resizeWindow('Trackbars', 400, 400)
cv2.moveWindow('Trackbars', 0, 0)
cv2.resizeWindow('Image', 800, 600)
cv2.moveWindow('Image', 400, 0)

# 트랙바 생성 (기본값을 초기값으로 설정)
cv2.createTrackbar('k1', 'Trackbars', 800, 2000, update)  # 기본값: 800 -> -0.2
cv2.createTrackbar('k2', 'Trackbars', 1100, 2000, update)  # 기본값: 1100 -> 0.1
cv2.createTrackbar('k3', 'Trackbars', 1000, 2000, update)  # 기본값: 1000 -> 0.0
cv2.createTrackbar('p1', 'Trackbars', 500, 1000, update)   # 기본값: 500 -> 0.0
cv2.createTrackbar('p2', 'Trackbars', 500, 1000, update)   # 기본값: 500 -> 0.0
cv2.createTrackbar('cx', 'Trackbars', w // 2, w, update)   # 기본값: w / 2
cv2.createTrackbar('cy', 'Trackbars', h // 2, h, update)   # 기본값: h / 2
cv2.createTrackbar('Grid ON/OFF', 'Trackbars', 0, 1, update)  # 기본값: OFF (0)

# 초기 이미지 보여주기
update(0)

# ESC 키를 눌러 종료
while True:
    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()
