import sys
import cv2
from ultralytics import YOLO
import os

modle = YOLO("yolo11n.pt")

source = r"D:\HuaweiMoveData\Users\psb20\Desktop\素素的材\2026-9-26-1.mp4"
#source = r"D:\HuaweiMoveData\Users\psb20\Desktop\素素的材\【熟肉】当邪教盯上早期互联网 [BV1YhHL6XEJo].f30080.mp4"

results = modle.predict(source = source, stream = True, conf = 0.25)

for result in results:

    annotated_frame = result.plot()

    cv2.imshow("YOLO stream", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()