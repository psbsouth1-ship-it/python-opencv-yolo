import cv2

# 尝试扫描索引 0 到 4，打印出摄像头名称
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Windows下建议加 CAP_DSHOW
    if cap.isOpened():
        print(f"索引 {i}: {cap.read()[1].shape if cap.read()[0] else '无画面'}")
    cap.release()
