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
        annotated = frame.copy()

        #自己打框

        for box in result.boxes:
            rx,ry,lx,ly=box.xyxy[0].cpu().numpy()
            #[0]取第一个框，cpu()和numpy()使可读
            rx,ry,lx,ly=int(rx),int(ry),int(lx),int(ly)
            cOnf=float(box.conf)
            id=int(box.cls)

            cv2.rectangle(annotated,(rx,ry),(lx,ly),(0,0,0),2)

            class_name = model.names[id]
            label = f"{class_name} {cOnf:.2f}"
        
            # 6. 画文字
            # 计算文字大小，为了确定文字背景框的高度
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        
            # 为了让文字在复杂背景下看得清，先画一个实心的矩形作为文字背景
            # 文字放在框的左上角上方
            cv2.rectangle(annotated, (rx, ry - 20), (rx + w, ry),(0,0,0), -1)
        
            # 画文字 (文字颜色设为白色)
            cv2.putText(annotated, label, (rx, ry - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)



        # OpenCV 不支持在画面上绘制中文，这里用英文
        speed = result.speed.get("inference", 0)
        cv2.putText(annotated, f"{speed:.1f} ms/frame", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("YOLO11 - press q to quit", annotated)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()