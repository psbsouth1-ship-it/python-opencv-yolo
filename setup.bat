@echo off
rem 一键创建 YOLO 学习环境（Windows）
rem 用法：双击运行，或在终端执行 setup.bat

cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo [!] 未找到 py 启动器，请先安装 Python 3.13: https://www.python.org/downloads/
    exit /b 1
)

echo [1/4] 创建虚拟环境 .venv ...
py -3.13 -m venv .venv
if errorlevel 1 (
    echo [!] 创建虚拟环境失败，请确认已安装 64 位 Python 3.13
    exit /b 1
)

set "PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"

echo [2/4] 升级 pip ...
.venv\Scripts\python.exe -m pip install --upgrade pip -i %PIP_INDEX%
if errorlevel 1 exit /b 1

echo [3/4] 安装 CPU 版 PyTorch ...
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu -i %PIP_INDEX%
if errorlevel 1 exit /b 1

echo [4/4] 安装 YOLO 与其余依赖 ...
.venv\Scripts\python.exe -m pip install -r requirements.txt -i %PIP_INDEX%
if errorlevel 1 exit /b 1

echo.
echo 安装完成！在 VS Code 中选择解释器：.venv\Scripts\python.exe
echo 然后运行：python 00_check_env.py
pause
