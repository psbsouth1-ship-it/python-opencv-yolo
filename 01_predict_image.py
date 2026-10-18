"""示例 1：用预训练模型做图片目标检测。

用法：
    python 01_predict_image.py                       # 检测 assets/images/bus.jpg
    python 01_predict_image.py 你的图片.jpg           # 检测自己的图片
    python 01_predict_image.py 图片目录               # 批量检测整个目录

检测结果图片保存在 runs/detect/predict*/ 下。
"""

import os
import sys
from pathlib import Path

from ultralytics import YOLO

MODEL_PATH = "weights/yolo11n.pt"  # 首次运行会自动下载（约 5.6 MB）
SOURCE = sys.argv[1] if len(sys.argv) > 1 else "assets/images/bus.jpg"

if not Path(MODEL_PATH).exists():
    raise FileNotFoundError(f"找不到 {MODEL_PATH}，请先按 README 的说明下载预训练权重。")

model = YOLO(MODEL_PATH)
results = model.predict(SOURCE, conf=0.25, save=True, project=os.path.abspath("runs"), name="predict")

for result in results:
    print(f"\n图片: {result.path}")
    for box in result.boxes:
        cls = result.names[int(box.cls)]
        conf = float(box.conf)
        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
        print(f"  {cls:<12} 置信度 {conf:.2f}  位置 ({x1}, {y1}) - ({x2}, {y2})")

print(f"\n标注结果已保存到: {results[0].save_dir}")
