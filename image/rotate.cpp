#include <opencv2/opencv.hpp>
#include <iostream>

int main(int argc, char** argv) {
    // 이미지 파일 경로
    const std::string imagePath = "path/to/your/image.jpg";  // 이미지 파일 경로를 입력하세요
    const std::string outputPath = "path/to/save/rotated_image.jpg";  // 저장할 파일 경로를 입력하세요

    // 이미지 로드
    cv::Mat image = cv::imread(imagePath);
    if (image.empty()) {
        std::cerr << "Error: Unable to load the image." << std::endl;
        return -1;
    }

    // 이미지 회전 (시계 반대 방향으로 90도)
    cv::Mat rotatedImage;
    cv::transpose(image, rotatedImage);
    cv::flip(rotatedImage, rotatedImage, 1);  // 1은 수평으로 flip

    // 회전된 이미지 저장
    if (!cv::imwrite(outputPath, rotatedImage)) {
        std::cerr << "Error: Unable to save the rotated image." << std::endl;
        return -1;
    }

    // 원본 이미지와 회전된 이미지 표시
    cv::imshow("Original Image", image);
    cv::imshow("Rotated Image", rotatedImage);
    cv::waitKey(0);

    return 0;
}
