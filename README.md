# python-opencv-yolo

YOLO 新手学习环境（Windows + Python 3.13 + PyTorch CPU + Ultralytics）。

> 当前状态：**✅ 环境搭建完成并全部通过验证**
> 本 README 会随搭建进度实时更新，最后更新：2026-10-18 20:45

## 搭建进度

| 步骤 | 状态 | 说明 |
| --- | --- | --- |
| 检查本机 Python | ✅ 完成 | 3.11 / 3.13 / 3.14 均可用，选用 3.13.12 (64 位) |
| 创建虚拟环境 `.venv` | ✅ 完成 | 使用 Python 3.13，升级 pip 到 26.2.1 |
| 安装 PyTorch（CPU 版） | ✅ 完成 | torch 2.14.1+cpu、torchvision 0.29.1 |
| 安装 Ultralytics / OpenCV | ✅ 完成 | ultralytics 8.4.182、opencv-python 5.0.0、matplotlib、pandas |
| 准备示例图片 | ✅ 完成 | 4 张官方示例图，存放在 `assets/images/` |
| 下载预训练权重 | ✅ 完成 | `weights/yolo11n.pt`（约 5.6 MB） |
| 下载 COCO8 迷你数据集 | ✅ 完成 | 8 张图，用于练习训练流程，位于 `datasets/coco8/` |
| 编写示例代码与文档 | ✅ 完成 | `00`~`03` 四个脚本 + `requirements.txt` + `setup.bat` + 本 README |
| 配置 VS Code | ✅ 完成 | `.vscode/settings.json`、`launch.json`、`.env`、`.gitignore` |
| 冒烟测试（实际跑一遍） | ✅ 完成 | 00→03 全部运行通过，见下方“验证结果” |

## 验证结果（2026-10-18 20:45）

| 脚本 | 结果 |
| --- | --- |
| `00_check_env.py` | 环境自检通过，示例图片检测到 5 个目标 |
| `01_predict_image.py` | 识别出 1 辆 bus + 4 个 person，结果保存到 `runs/predict/` |
| `02_webcam.py` | 摄像头 0 可打开；读取→推理→绘图→保存流程已验证（约 120~150 ms/帧，CPU） |
| `03_train.py` | COCO8 上训练 20 轮完成，验证集 mAP50 = 0.942，结果在 `runs/train/` |

## 目录结构

```
python-opencv-yolo/
├── .venv/                 # Python 3.13 虚拟环境（不要提交）
├── .ultralytics/          # YOLO 配置（settings.json，目录已指向项目内）
├── .vscode/               # 解释器、调试、终端环境变量配置
├── assets/images/         # 示例图片
├── datasets/              # coco8/ 迷你数据集 + coco8.yaml 配置
├── weights/               # 预训练权重 yolo11n.pt
├── runs/                  # 检测/训练输出（predict、train、detect/val）
├── .env                   # 环境变量：SSL 证书、编码、配置目录
├── 00_check_env.py        # 步骤 0：环境自检
├── 01_predict_image.py    # 示例 1：图片检测
├── 02_webcam.py           # 示例 2：摄像头 / 视频实时检测
├── 03_train.py            # 示例 3：COCO8 上的简易训练
├── requirements.txt       # 固定版本依赖清单
└── setup.bat              # 一键重建环境脚本
```

## 开始使用（VS Code）

1. 用 VS Code 打开本文件夹：`code d:\VSCODE-LOCAL\yolo个人尝试\python-opencv-yolo`
2. 右下角选择解释器 → `.venv\Scripts\python.exe`（已写入 `settings.json`，通常会自动选中）
3. 新开一个终端（会自动加载 `.env`），按顺序运行：

```powershell
python 00_check_env.py                 # 环境自检
python 01_predict_image.py             # 检测 assets/images/bus.jpg
python 01_predict_image.py 你的图片.jpg # 检测自己的图片
python 02_webcam.py                    # 打开摄像头实时检测，按 q 退出
python 02_webcam.py 视频.mp4            # 检测视频文件
python 03_train.py                     # 在 COCO8 上训练 20 轮（CPU 约 1 分钟）
```

也可以在 VS Code 里按 `F5` 调试当前打开的脚本。

## 新手知识速览

- **模型文件**：`yolo11n.pt` 中的 `n` = nano，最小最快；依次还有 `s / m / l / x`，精度更高但更慢。
  换成 `yolo11s.pt` 只需改脚本里的模型名，首次会从官方仓库下载。
- **置信度 `conf`**：只保留分数高于阈值的框（默认 0.25）。误检多就调高，漏检多就调低。
- **图片尺寸 `imgsz`**：推理/训练时的输入边长（默认 640）。越大越准、越慢。
- **结果目录**：本次运行的 `runs/predict/`、`runs/train/`（重复运行会生成 `predict-2`、`train-2` 等）。
- **训练产物**：`best.pt` / `last.pt`（权重）、`results.csv` 与 `results.png`（损失和指标曲线）、
  `confusion_matrix.png`（混淆矩阵）、`val_batch0_pred.jpg`（验证集预测效果）。
- **换成自己的数据集**：按 YOLO 格式准备 `images/train`、`labels/train`（每行 `类别 x y w h`，均归一化），
  复制 `datasets/coco8.yaml` 改 `path` 和 `names`，再把 `03_train.py` 的 `data` 指向新 yaml。
- **有 NVIDIA 显卡时**：重装 CUDA 版 PyTorch（`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`），
  并把 `device="cpu"` 改为 `device=0`。

## 已选环境方案

- Python 3.13（64 位），虚拟环境位于 `.venv/`
- PyTorch CPU 版本（本机无 NVIDIA 显卡，13 代 i5，CPU 推理约 120 ms/帧）
- 下载源：清华 PyPI 镜像
- YOLO 配置目录指向项目内 `.ultralytics/`，数据集/权重/结果目录均在项目内

## 常见问题

- **自动下载权重报 `CERTIFICATE_VERIFY_FAILED`**：本机 Python 缺少中间证书。`.env` 里已设置
  `SSL_CERT_FILE` 指向 certifi 证书包；如果仍失败，可用 `curl --ssl-no-revoke -L -o weights\yolo11n.pt <下载地址>` 手动下载。
- **终端中文乱码**：`.env` 和 `.vscode/settings.json` 已设置 `PYTHONIOENCODING=utf-8`；
  若在外部终端运行，可先执行 `$env:PYTHONIOENCODING="utf-8"`。
- **结果目录出现 `runs\detect\runs\...`**：这是 Ultralytics 把相对路径 `project="runs"` 再拼一次导致的。
  脚本里已改用 `os.path.abspath("runs")`；自己写代码时也建议给 `project` 传绝对路径。
- **摄像头打不开**：关闭其他占用摄像头的程序（腾讯会议、微信等），或换 `python 02_webcam.py 1`。
- **`ultralytics` 每次导入都说 `Creating new Ultralytics Settings`**：说明 `.ultralytics` 设置文件损坏，
  删掉 `.ultralytics` 文件夹后重新运行一次即可。

## 搭建记录（时间倒序）

- 20:45 最终验收：删除 `runs/` 后重跑 00→03，全部通过；输出只落在项目内，上级目录无残留。
  修正 `project` 为绝对路径、补充 `PYTHONIOENCODING=utf-8`、新增 `requirements.txt` 与 `setup.bat`。
- 20:19 冒烟测试进度：`00_check_env.py` ✅（检测到 5 个目标）；
  `01_predict_image.py` ✅（识别 1 辆 bus + 4 个 person）；
  `02_webcam.py` 的读取/推理/绘图逻辑 ✅（摄像头 0 可打开，画面绘制与保存已验证）。
  期间修复：`model.speed` 改为 `result.speed`；数据集 `path` 改为相对 yaml 位置；
  把 `.ultralytics` 设置里的数据集/权重/结果目录都改到项目内，避免跑到上级目录。
- 20:12 开始冒烟测试：先跑 `00_check_env.py`，再依次跑图片检测、视频检测与一次小训练。
- 20:11 首次 `03_train.py` 失败：数据集路径被解析到上级目录，已修正（见 20:19）。
- 20:10 写好 4 个示例脚本；新增 `.env`（设置 `SSL_CERT_FILE` 指向 certifi 证书，已实测可修复自动下载报错）。
- 20:08 下载并解压 COCO8 迷你数据集，编写 `datasets/coco8.yaml`。
- 20:06 用 `weights/yolo11n.pt` 检测 `bus.jpg`，识别出 5 个目标，推理链路正常。
- 20:05 下载 `yolo11n.pt` 成功（5613764 字节）。注意：本机 Python 的 SSL 证书链校验失败，
  自动下载权重会报 `CERTIFICATE_VERIFY_FAILED`，因此改用 `curl --ssl-no-revoke` 手动下载。
- 19:59 安装 ultralytics / opencv-python / matplotlib / pandas；导入验证通过（CUDA 不可用，确认走 CPU）。
- 19:58 安装 CPU 版 PyTorch。
- 19:57 创建 `.venv` 虚拟环境。
- 19:54 检查本机环境：Python 3.13.12 可用，未检测到 NVIDIA 显卡（无 nvidia-smi）。

## 已选环境方案

- Python 3.13（64 位），虚拟环境位于 `.venv/`
- PyTorch CPU 版本（本机无 NVIDIA 显卡）
- 下载源：清华 PyPI 镜像
- YOLO 配置目录指向项目内 `.ultralytics/`，权重目录 `weights/`
