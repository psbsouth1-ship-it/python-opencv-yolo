"""MC 视觉脚本：检测画面里的「末影人」，命中后点击画面中心自动攻击。

画面来源：直接截取 Minecraft 游戏窗口（GDI，无需摄像头/OBS）；找不到窗口时退回主屏幕。
触发条件：画面中出现足够多的末影人。末影人 = 几乎纯黑的车体 + 一对亮紫色眼睛，
          所以判别方式是「找紫色眼睛，再看眼睛周围是不是大片纯黑」——
          这样能把空气里的紫色粒子、紫水晶、其他紫色特效排除掉（它们周围没有黑车体）。
触发动作：鼠标移到画面中心（准星处）按下左键再松开（MC 的攻击判定在「按下」那一下）。
触发节奏：一次触发只打一次；末影人先消失、再重新出现才会触发下一次。

用法：
    python 07_mc脚本.py                       # 默认参数
    python 07_mc脚本.py --min-targets 3       # 至少 3 个末影人才攻击
    python 07_mc脚本.py --no-control          # 只检测不操作鼠标（先看效果）
    python 07_mc脚本.py --debug               # 直接打开调试窗口，看掩码/目标/状态
    python 07_mc脚本.py --save-frame runs\\shot.png   # 截一帧后退出，用来调阈值

热键（全局，在游戏里也能按）：
    F8  开启/关闭自动攻击
    F9  开关调试窗口（窗口里按 q 或 Esc 也能关）
    F10 立即退出

所有阈值都在下方「配置」里，命令行参数只覆盖当前这一次运行。
"""

from __future__ import annotations

import argparse
import ctypes
import time
from collections import deque
from ctypes import wintypes
from dataclasses import dataclass

import cv2
import numpy as np

# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------
WINDOW_TITLE_KEYWORD = "Minecraft"  # Java 版标题形如 "Minecraft* 1.20.1 - 多人游戏"

MIN_TARGETS = 2  # 画面里至少看到这么多个末影人（每个末影人计 1 个「眼睛团」）
ROI = (0.10, 0.20, 0.90, 0.90)  # 检测区域 (x1, y1, x2, y2)，按画面比例；默认避开四周 HUD

# 末影人眼睛：亮紫 —— B、R 都够高且明显高于 G
EYE_B_MIN = 95
EYE_R_MIN = 85
EYE_BG_DIFF = 45
EYE_RG_DIFF = 30
EYE_MIN_AREA = 4  # 单个眼睛团的最小像素数（滤掉极小噪点；经过闭运算后一对眼睛通常 >= 8）
EYE_JOIN_W, EYE_JOIN_H = 5, 3  # 闭运算核：只把同一只末影人的左右眼连起来，不会把相邻的末影人连成一团
EYE_MIN_Y = 0.04  # 画面顶部这个比例以上不找眼睛（准星、天空杂色）

# 末影人车体：几乎纯黑。眼睛周围这块窗口里至少要有这么大比例的纯黑，才认为眼睛长在末影人身上
BODY_MAX = 45
BODY_WIN_W, BODY_WIN_H = 20, 28  # 以眼睛为中心、左右/上下的窗口半径（像素）
BODY_MIN_RATIO = 0.45
MERGE_DIST_X, MERGE_DIST_Y = 36, 36  # 相距这么近的紫块算同一只末影人（像素，约等于半个屏幕宽度的 1/25）

CENTER_TOLERANCE = 0.12  # 目标离画面中心多近才算「准星已经对着它」（占画面宽/高的比例）
CENTER_POINT = (0.5, 0.5)  # 攻击时鼠标点击的位置（画面比例），默认正中心准星

FIRE_INTERVAL = 0.35  # 两次攻击的最小间隔（秒）；「每次触发只打一次」的兜底保护
CLICK_HOLD = 0.04  # 左键按下后保持多久再松开（秒）

HOTKEY_TOGGLE = 0x77  # F8  开关
HOTKEY_DEBUG = 0x78  # F9  调试窗口
HOTKEY_QUIT = 0x79  # F10 退出

# ----------------------------------------------------------------------------
# Win32 绑定
# ----------------------------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000  # 某些渲染模式下需要它才能截到画面
DIB_RGB_COLORS = 0
BI_RGB = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SM_CXSCREEN, SM_CYSCREEN = 0, 1
DESKTOPHORZRES, DESKTOPVERTRES = 118, 117  # 真实像素尺寸（高 DPI 下与 SM_CXSCREEN 不同）
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.mouse_event.argtypes = [wintypes.DWORD, ctypes.c_int, ctypes.c_int, wintypes.DWORD, ctypes.c_void_p]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
]
gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.GetDeviceCaps.restype = ctypes.c_int


# ----------------------------------------------------------------------------
# 找窗口 & 截图
# ----------------------------------------------------------------------------
def process_name(pid: int) -> str:
    """按 PID 取进程可执行文件名；进程不存在时返回空串。"""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return buf.value.replace("\\", "/").rsplit("/", 1)[-1].lower()
    finally:
        kernel32.CloseHandle(handle)


def find_game_window(keyword: str) -> int:
    """找标题含关键字的可见 Minecraft 窗口，返回客户区最大的那个 hwnd；找不到返回 0。

    用「标题 + 进程名」双重判断，避免把 VS Code 里打开的 07_mc脚本.py 标签页当成游戏窗口。
    """
    candidates: list[tuple[int, int]] = []
    game_exes = {"java.exe", "javaw.exe", "minecraft.exe", "minecraftlauncher.exe", "bedrock_server.exe"}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def collect(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        # 同时匹配关键字和 minecraft，中文标题也能命中
        if keyword.lower() not in title.lower() and "minecraft" not in title.lower():
            return True
        if not user32.IsWindowVisible(hwnd):
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if process_name(pid.value) not in game_exes:
            return True

        rect = wintypes.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        area = (rect.right - rect.left) * (rect.bottom - rect.top)
        if area > 0:
            candidates.append((area, hwnd))
        return True

    user32.EnumWindows(collect, 0)
    if not candidates:
        return 0
    return max(candidates)[1]


class ScreenGrabber:
    """用 GDI 截窗口客户区；窗口不可用（最小化/被关掉）时退回截主屏幕。"""

    def __init__(self, hwnd: int | None):
        self.hwnd = hwnd or 0
        self.screen_origin = (0, 0)
        self._hdc = wintypes.HDC()
        self._memdc = wintypes.HDC()
        self._bmp = wintypes.HBITMAP()
        self._surface_size = (0, 0)
        self._failures = 0

    @property
    def window_origin(self) -> tuple[int, int]:
        """窗口客户区左上角在屏幕上的坐标；退回屏幕截图时是 (0, 0)。"""
        return self.screen_origin

    def _release_surface(self) -> None:
        if self._memdc:
            gdi32.DeleteDC(self._memdc)
        if self._bmp:
            gdi32.DeleteObject(self._bmp)
        if self._hdc:
            user32.ReleaseDC(wintypes.HWND(self.hwnd), self._hdc)
        self._memdc, self._bmp, self._hdc = wintypes.HDC(), wintypes.HBITMAP(), wintypes.HDC()
        self._surface_size = (0, 0)

    def _bitmap_to_numpy(self, width: int, height: int) -> np.ndarray | None:
        info = BITMAPINFO()
        info.bmiHeader = BITMAPINFOHEADER(
            ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, BI_RGB, 0, 0, 0, 0, 0
        )
        buf = ctypes.create_string_buffer(width * height * 4)
        lines = gdi32.GetDIBits(
            self._memdc, self._bmp, 0, height, ctypes.cast(buf, ctypes.c_void_p), ctypes.byref(info), DIB_RGB_COLORS
        )
        if not lines:
            return None
        # 32 位 DIB 是 BGRA，丢掉 alpha 得到 OpenCV 的 BGR
        return np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)[:, :, :3].copy()

    def _grab_window(self) -> np.ndarray | None:
        if not user32.IsWindow(self.hwnd) or user32.IsIconic(self.hwnd):
            self.hwnd = 0
            return None

        rect = wintypes.RECT()
        if not user32.GetClientRect(self.hwnd, ctypes.byref(rect)):
            self.hwnd = 0
            return None
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return None

        if (width, height) != self._surface_size:
            self._release_surface()
            self.screen_origin = (0, 0)  # 稍后重算
            self._hdc = user32.GetDC(wintypes.HWND(self.hwnd))
            self._memdc = gdi32.CreateCompatibleDC(self._hdc)
            self._bmp = gdi32.CreateCompatibleBitmap(self._hdc, width, height)
            if not self._memdc or not self._bmp:
                self.hwnd = 0
                return None
            gdi32.SelectObject(self._memdc, self._bmp)
            self._surface_size = (width, height)

        point = wintypes.POINT(0, 0)
        if user32.ClientToScreen(self.hwnd, ctypes.byref(point)):
            self.screen_origin = (point.x, point.y)

        if not gdi32.BitBlt(self._memdc, 0, 0, width, height, self._hdc, 0, 0, SRCCOPY | CAPTUREBLT):
            if not gdi32.BitBlt(self._memdc, 0, 0, width, height, self._hdc, 0, 0, SRCCOPY):
                self._failures += 1
                return None

        frame = self._bitmap_to_numpy(width, height)
        if frame is None:
            self._failures += 1
        else:
            self._failures = 0
        return frame

    def _grab_screen(self) -> np.ndarray | None:
        width = user32.GetSystemMetrics(SM_CXSCREEN)
        height = user32.GetSystemMetrics(SM_CYSCREEN)
        if width <= 0 or height <= 0:
            return None

        # 截图用真实屏幕像素，鼠标点击用虚拟屏幕坐标（高 DPI 缩放下两者不同，必须换算）
        real_w, real_h = self._screen_pixels()
        if (real_w, real_h) not in (self._surface_size, (0, 0)) or self.hwnd:
            self._release_surface()
            self._hdc = user32.GetDC(wintypes.HWND(0))  # 0 = 整个屏幕
            self._memdc = gdi32.CreateCompatibleDC(self._hdc)
            self._bmp = gdi32.CreateCompatibleBitmap(self._hdc, real_w, real_h)
            if not self._memdc or not self._bmp:
                return None
            gdi32.SelectObject(self._memdc, self._bmp)
            self._surface_size = (real_w, real_h)
        self.screen_origin = (0, 0)

        if not gdi32.BitBlt(self._memdc, 0, 0, real_w, real_h, self._hdc, 0, 0, SRCCOPY | CAPTUREBLT):
            return None
        return self._bitmap_to_numpy(real_w, real_h)

    def grab(self) -> tuple[np.ndarray | None, tuple[int, int]]:
        """返回 (BGR 画面, 画面左上角的屏幕坐标)。"""
        if self.hwnd:
            frame = self._grab_window()
            if frame is not None:
                return frame, self.screen_origin
            if self._failures >= 60 and self.hwnd:
                print("[警告] 窗口截图连续失败，改为截主屏幕。")
                self.hwnd = 0
        return self._grab_screen(), (0, 0)

    @staticmethod
    def _screen_pixels() -> tuple[int, int]:
        """整个屏幕的真实像素尺寸（高 DPI 时 GetSystemMetrics 给的是逻辑尺寸）。"""
        hdc = user32.GetDC(wintypes.HWND(0))
        if not hdc:
            return user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN)
        try:
            return gdi32.GetDeviceCaps(hdc, DESKTOPHORZRES), gdi32.GetDeviceCaps(hdc, DESKTOPVERTRES)
        finally:
            user32.ReleaseDC(wintypes.HWND(0), hdc)

    def close(self) -> None:
        self._release_surface()


# ----------------------------------------------------------------------------
# 检测：紫色眼睛 → 车体验证 → 计数 + 准星判定
# ----------------------------------------------------------------------------
@dataclass
class Target:
    cx: int  # 眼睛团中心（整帧坐标）
    cy: int
    area: int
    body_ratio: float  # 眼睛周围的黑车体占比


@dataclass
class Detection:
    hits: list[Target]  # 通过车体验证的末影人眼睛团
    trigger: bool
    on_center: bool  # 准星是否已经对着其中一个目标
    reason: str


def _purple_eyes(bgr: np.ndarray) -> np.ndarray:
    """亮紫色掩码：比背景亮、B/R 高、G 低。"""
    b, g, r = cv2.split(bgr.astype(np.int16))
    eye = (b > EYE_B_MIN) & (r > EYE_R_MIN) & (b > g + EYE_BG_DIFF) & (r > g + EYE_RG_DIFF)
    return eye.astype(np.uint8)


def _black_body(bgr: np.ndarray) -> np.ndarray:
    """末影人车体：三个通道都几乎为 0 的纯黑。"""
    return (bgr.max(axis=2) < BODY_MAX).astype(np.uint8)


def detect_endermen(
    frame: np.ndarray,
    min_targets: int = MIN_TARGETS,
    roi: tuple[float, float, float, float] = ROI,
    eyes_out: np.ndarray | None = None,
    body_out: np.ndarray | None = None,
) -> Detection:
    """检测末影人，并判断准星是否已对准其中一个。

    eyes_out / body_out 传同尺寸灰度图（可选），会把各自的掩码画上去，供调试窗口查看。
    """
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(width * roi[0]), int(height * roi[1]), int(width * roi[2]), int(height * roi[3]))
    if x2 <= x1 or y2 <= y1:
        return Detection([], False, False, "检测区域无效")

    eyes = _purple_eyes(frame[y1:y2, x1:x2])
    body = _black_body(frame[y1:y2, x1:x2])
    # 末影人眼睛是 2x1 像素的小点，先做一次闭运算把小点连成一个团块再数
    eye_span = cv2.getStructuringElement(cv2.MORPH_RECT, (EYE_JOIN_W, EYE_JOIN_H))
    eyes_joined = cv2.morphologyEx(eyes, cv2.MORPH_CLOSE, eye_span)

    if eyes_out is not None and eyes_out.shape[:2] == frame.shape[:2]:
        eyes_out[:] = 0
        eyes_out[y1:y2, x1:x2] = eyes_joined * 255
    if body_out is not None and body_out.shape[:2] == frame.shape[:2]:
        body_out[:] = 0
        body_out[y1:y2, x1:x2] = body * 255

    roi_h, roi_w = body.shape
    min_y = int(height * EYE_MIN_Y) - y1
    count, _labels, stats, centroids = cv2.connectedComponentsWithStats(eyes_joined, connectivity=8)

    blobs: list[Target] = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        cx_roi, cy_roi = int(centroids[label][0]), int(centroids[label][1])
        if area < EYE_MIN_AREA or cy_roi < min_y:
            continue
        window = body[
            max(0, cy_roi - BODY_WIN_H) : min(roi_h, cy_roi + BODY_WIN_H),
            max(0, cx_roi - BODY_WIN_W) : min(roi_w, cx_roi + BODY_WIN_W),
        ]
        body_ratio = float(window.mean()) if window.size else 0.0
        if body_ratio >= BODY_MIN_RATIO:
            blobs.append(Target(cx_roi + x1, cy_roi + y1, area, body_ratio))

    hits = _group_by_distance(blobs, MERGE_DIST_X, MERGE_DIST_Y)

    center_x, center_y = width * CENTER_POINT[0], height * CENTER_POINT[1]
    on_center = any(
        abs(t.cx - center_x) <= width * CENTER_TOLERANCE
        and abs(t.cy - center_y) <= height * CENTER_TOLERANCE
        for t in hits
    )

    if len(hits) >= min_targets:
        reason = f"{len(hits)} 个末影人"
        return Detection(hits, True, on_center, reason + ("（准星已对准）" if on_center else "（准星未对准）"))
    return Detection(hits, False, on_center, f"末影人不足（{len(hits)}/{min_targets}）")


def _group_by_distance(blobs: list[Target], dx: int, dy: int) -> list[Target]:
    """同一只末影人身上可能冒出好几个紫色团块，按距离把它们合并成一个目标。

    合并后面积取最大那块（避免把窗口边框之类的碎片算成「第二个末影人」）。
    """
    groups: list[list[Target]] = []
    for blob in sorted(blobs, key=lambda t: -t.area):
        for group in groups:
            if abs(group[0].cx - blob.cx) <= dx and abs(group[0].cy - blob.cy) <= dy:
                group.append(blob)
                break
        else:
            groups.append([blob])
    return [max(group, key=lambda t: t.area) for group in groups]


# ----------------------------------------------------------------------------
# 鼠标：平滑移动 → 按下 → 松开
# ----------------------------------------------------------------------------
class Mouse:
    @staticmethod
    def position() -> tuple[int, int]:
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def cursor_in_rect(self, rect: tuple[int, int, int, int]) -> bool:
        x, y = self.position()
        left, top, right, bottom = rect
        return left <= x < right and top <= y < bottom

    def glide(self, target_x: int, target_y: int) -> None:
        """直接移到目标点。Java 版在鼠标被游戏捕获时会锁定光标，分步移动没有意义。"""
        user32.SetCursorPos(target_x, target_y)

    def attack(self, x: int, y: int) -> None:
        self.glide(x, y)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
        time.sleep(CLICK_HOLD)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)


# ----------------------------------------------------------------------------
# 调试窗口
# ----------------------------------------------------------------------------
def make_debug_view(frame: np.ndarray, eyes: np.ndarray, det: Detection, state: dict) -> np.ndarray:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(width * ROI[0]), int(height * ROI[1]), int(width * ROI[2]), int(height * ROI[3]))

    view = frame.copy()
    cv2.rectangle(view, (x1, y1), (x2, y2), (0, 255, 255), 1)
    for target in det.hits:
        cv2.rectangle(view, (target.cx - 18, target.cy - 12), (target.cx + 18, target.cy + 12), (0, 255, 0), 2)
    cv2.drawMarker(
        view, (int(width * CENTER_POINT[0]), int(height * CENTER_POINT[1])), (255, 255, 255), cv2.MARKER_CROSS, 30, 2
    )

    half_w, half_h = width // 2, height // 2
    thumb = cv2.resize(view, (half_w, half_h))
    eyes_view = cv2.resize(eyes, (half_w, half_h))
    mask_view = cv2.cvtColor(eyes_view, cv2.COLOR_GRAY2BGR)

    status_color = (0, 255, 0) if det.trigger else (200, 200, 200)
    lines = [
        f"armed: {state['armed']}   hits: {len(det.hits)}",
        f"{det.reason}",
        f"on_center: {det.on_center}",
        f"fps: {state['fps']:.1f}   fired: {state['fired']}",
        "F8 arm  F9 debug  F10 quit",
    ]
    for i, text in enumerate(lines):
        cv2.putText(thumb, text, (8, 22 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(thumb, text, (8, 22 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 1)

    return np.hstack((thumb, np.full((half_h, 8, 3), 40, np.uint8), mask_view))


# ----------------------------------------------------------------------------
# 主循环
# ----------------------------------------------------------------------------
class Hotkeys:
    """用 GetAsyncKeyState 读全局按键，无需第三方库；只有「刚按下」才触发，避免连发。"""

    def __init__(self) -> None:
        self._held: set[int] = set()

    def pressed_once(self, vk: int) -> bool:
        down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
        if down and vk not in self._held:
            self._held.add(vk)
            return True
        if not down:
            self._held.discard(vk)
        return False


def save_current_frame(path: str) -> bool:
    """截一帧存成 PNG（UTF-8 路径安全：先 imencode 再写字节）。"""
    grabber = ScreenGrabber(find_game_window(WINDOW_TITLE_KEYWORD))
    try:
        frame, _ = grabber.grab()
        if frame is None:
            print("[警告] 截图失败。")
            return False
        ok, encoded = cv2.imencode(".png", frame)
        if not ok:
            print("[警告] PNG 编码失败。")
            return False
        with open(path, "wb") as fh:
            fh.write(encoded.tobytes())
        print(f"[信息] 已保存一帧：{path}（{frame.shape[1]}x{frame.shape[0]}）")
        return True
    finally:
        grabber.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="MC 末影人视觉检测 → 点击画面中心自动攻击")
    parser.add_argument("--keyword", default=WINDOW_TITLE_KEYWORD, help="游戏窗口标题关键字")
    parser.add_argument("--min-targets", type=int, default=MIN_TARGETS, help="画面里至少几个末影人才触发")
    parser.add_argument("--require-center", action="store_true", help="只在准星已对准末影人时才攻击")
    parser.add_argument("--no-control", action="store_true", help="只检测，不操作鼠标")
    parser.add_argument("--debug", action="store_true", help="启动时打开调试窗口")
    parser.add_argument("--save-frame", default="", help="截一帧保存到该路径后退出，用于调阈值")
    parser.add_argument("--max-seconds", type=float, default=0, help="运行多少秒后自动退出（0 = 一直运行）")
    args = parser.parse_args()

    if args.save_frame:
        raise SystemExit(0 if save_current_frame(args.save_frame) else 1)

    grabber = ScreenGrabber(find_game_window(args.keyword))
    hotkeys = Hotkeys()
    mouse = Mouse()
    eyes = np.zeros((0, 0), np.uint8)
    body = np.zeros((0, 0), np.uint8)
    frame_times: deque[float] = deque(maxlen=30)
    state = {"armed": not args.no_control, "debug": args.debug, "fired": 0, "fps": 0.0}
    was_present = False  # 上一帧是否已经满足条件（用于「每次触发只打一次」）
    last_fire = 0.0  # 上次攻击时间，冷却兜底
    started = time.perf_counter()

    if grabber.hwnd:
        print(f"[信息] 找到游戏窗口（hwnd={grabber.hwnd}），直接截取窗口画面。")
    else:
        print(f"[警告] 没找到标题含「{args.keyword}」的游戏窗口，先截整个主屏幕。")
        print("       建议游戏用「窗口化」或「窗口化全屏」，并保持在前台。")
    if args.no_control:
        print("[信息] --no-control：只检测，不动鼠标。")
    print("F8 开关自动攻击 | F9 调试窗口 | F10 退出")

    shots_taken = 0
    try:
        while True:
            if args.max_seconds and time.perf_counter() - started > args.max_seconds:
                print("[信息] 达到 --max-seconds，退出。")
                break

            frame, origin = grabber.grab()
            shots_taken += 1
            if frame is None:
                print("[警告] 截图失败，1 秒后重试。")
                time.sleep(1.0)
                continue

            now = time.perf_counter()
            frame_times.append(now)
            if len(frame_times) > 1:
                state["fps"] = (len(frame_times) - 1) / max(1e-6, frame_times[-1] - frame_times[0])

            if eyes.shape != frame.shape[:2]:
                eyes = np.zeros(frame.shape[:2], np.uint8)
                body = np.zeros(frame.shape[:2], np.uint8)

            det = detect_endermen(
                frame,
                min_targets=args.min_targets,
                eyes_out=eyes,
                body_out=body,
            )

            if hotkeys.pressed_once(HOTKEY_TOGGLE):
                state["armed"] = not state["armed"]
                print("[热键] 自动攻击：" + ("开启" if state["armed"] else "关闭"))
            if hotkeys.pressed_once(HOTKEY_DEBUG):
                state["debug"] = not state["debug"]
                if not state["debug"]:
                    cv2.destroyWindow("MC debug")
            if hotkeys.pressed_once(HOTKEY_QUIT):
                print("[热键] F10 退出。")
                break

            ready = det.trigger and (det.on_center or not args.require_center)
            cooling = now - last_fire < FIRE_INTERVAL
            if state["armed"] and ready and not was_present and not cooling:
                screen_x = origin[0] + int(frame.shape[1] * CENTER_POINT[0])
                screen_y = origin[1] + int(frame.shape[0] * CENTER_POINT[1])
                in_window = not grabber.hwnd or mouse.cursor_in_rect(
                    (origin[0], origin[1], origin[0] + frame.shape[1], origin[1] + frame.shape[0])
                )
                if in_window:
                    mouse.attack(screen_x, screen_y)
                    last_fire = time.perf_counter()
                    state["fired"] += 1
                    print(f"[攻击] {det.reason} → 点击画面中心（第 {state['fired']} 次）")
                elif shots_taken % 60 == 1:
                    print("[跳过] 鼠标不在游戏窗口内，先切回游戏。")
            was_present = ready

            if state["debug"]:
                cv2.imshow("MC debug", make_debug_view(frame, eyes, det, state))
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    state["debug"] = False
                    cv2.destroyWindow("MC debug")
            else:
                time.sleep(0.005)  # 让出 CPU，避免满速空转
    except KeyboardInterrupt:
        print("[信息] Ctrl+C 退出。")
    finally:
        grabber.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
