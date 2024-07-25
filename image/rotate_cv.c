#include <opencv4/opencv.h>
#include <stdio.h>

int main(int argc, char** argv) {
    // 이미지 파일 경로
    const char* imagePath = "image.jpg";  // 이미지 파일 경로를 입력하세요
    const char* outputPath = "rotated_image.jpg";  // 저장할 파일 경로를 입력하세요

    // 이미지 로드
    IplImage* image = cvLoadImage(imagePath, CV_LOAD_IMAGE_COLOR);
    if (!image) {
        fprintf(stderr, "Error: Unable to load the image.\n");
        return -1;
    }

    // 이미지 회전 (시계 반대 방향으로 90도)
    IplImage* rotatedImage = cvCreateImage(cvSize(image->height, image->width), IPL_DEPTH_8U, image->nChannels);
    cvTranspose(image, rotatedImage);
    cvFlip(rotatedImage, rotatedImage, 1);  // 1은 수평으로 flip

    // 회전된 이미지 저장
    if (!cvSaveImage(outputPath, rotatedImage, 0)) {
        fprintf(stderr, "Error: Unable to save the rotated image.\n");
        cvReleaseImage(&image);
        cvReleaseImage(&rotatedImage);
        return -1;
    }

    // 이미지 해제
    cvReleaseImage(&image);
    cvReleaseImage(&rotatedImage);

    printf("Image rotated and saved successfully.\n");
    return 0;
}
