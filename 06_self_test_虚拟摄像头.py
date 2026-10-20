import os
import cv2
import sys
from ultralytics import YOLO

model = YOLO("yolo11n.pt")

cap = cv2.VideoCapture(1)

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    result = model.predict(frame, conf=0.25, verbose=False)[0]
    annotated = result.plot()
    cv2.imshow("OBS Virtual Camera + YOLO", annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()