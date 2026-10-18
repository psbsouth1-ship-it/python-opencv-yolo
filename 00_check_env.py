"""环境自检：确认 YOLO 学习环境已经就绪。

用法（在 VS Code 终端里）：
    python 00_check_env.py
"""

import sys

import cv2
import torch
import ultralytics
from ultralytics import YOLO
from ultralytics.utils import SETTINGS, WEIGHTS_DIR

print("Python      :", sys.version.split()[0])
print("torch       :", torch.__version__, "| CUDA 可用:", torch.cuda.is_available())
print("ultralytics :", ultralytics.__version__)
print("OpenCV      :", cv2.__version__)
print("权重目录     :", WEIGHTS_DIR)
print("数据集目录   :", SETTINGS["datasets_dir"])

model = YOLO("weights/yolo11n.pt")
result = model.predict("assets/images/bus.jpg", verbose=False)[0]
print(f"\n示例图片检测到 {len(result.boxes)} 个目标 ✅")
print("环境检查完成 ✅")
