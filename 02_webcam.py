"""示例 2：打开摄像头做实时检测（OpenCV 读取帧 + YOLO 推理）。

用法：
    python 02_webcam.py              # 默认摄像头 0
    python 02_webcam.py 1            # 第二个摄像头
    python 02_webcam.py 视频.mp4      # 也可以检测视频文件

按 q 或 Esc 退出窗口。
"""

import sys

import cv2
from ultralytics import YOLO

MODEL_PATH = "weights/yolo11n.pt"
CONF = 0.25


def open_source(arg: str):
    if arg.isdigit():
        cam = cv2.VideoCapture(int(arg))
        if not cam.isOpened():
            raise RuntimeError(f"无法打开摄像头 {arg}，请检查摄像头是否被其他程序占用。")
        return cam
    cap = cv2.VideoCapture(arg)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频文件：{arg}")
    return cap


source_arg = sys.argv[1] if len(sys.argv) > 1 else "0"
cap = open_source(source_arg)
model = YOLO(MODEL_PATH)

print("按 q 或 Esc 退出。")
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("无法读取画面，已退出。")
            break

        result = model.predict(frame, conf=CONF, verbose=False)[0]
        annotated = result.plot()  # 自动画框、类别和置信度

        # OpenCV 不支持在画面上绘制中文，这里用英文
        speed = result.speed.get("inference", 0)
        cv2.putText(annotated, f"{speed:.1f} ms/frame", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("YOLO11 - press q to quit", annotated)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
