"""示例 3：最简单的训练流程（在 COCO8 迷你数据集上训练）。

COCO8 只有 8 张图，训练 20 轮几分钟即可完成（CPU 也能跑），适合熟悉流程。
训练结果（权重、曲线、指标）保存到 runs/detect/train*/。

用法：
    python 03_train.py
"""

import os

from ultralytics import YOLO

model = YOLO("weights/yolo11n.pt")  # 从预训练权重开始训练（迁移学习）

model.train(
    data="datasets/coco8.yaml",  # 数据集配置（图片路径 + 类别名）
    epochs=20,
    imgsz=640,
    batch=8,
    device="cpu",  # 有 NVIDIA 显卡时可改为 device=0
    project=os.path.abspath("runs"),  # 绝对路径可避免结果跑到上级目录
    name="train",
    exist_ok=False,
)

# 训练结束后用验证集评估一次
metrics = model.val()
print(f"\nmAP50: {metrics.box.map50:.3f}  mAP50-95: {metrics.box.map:.3f}")
