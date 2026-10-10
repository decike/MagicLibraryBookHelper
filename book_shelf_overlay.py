# -*- coding: utf-8 -*-
import re
import time
import queue
import threading
import ctypes
import tkinter as tk
import sys
import os

import cv2
import mss
import numpy as np
from rapidfuzz import process, fuzz
from rapidocr_onnxruntime import RapidOCR

# ================== 配置区 ==================
# 基准分辨率（基于你之前的截图测试环境）
BASE_W = 2560
BASE_H = 1440

# 让 Python 识别系统 DPI，避免高分辨率屏幕坐标错乱
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# 动态获取屏幕分辨率
user32 = ctypes.windll.user32
SCREEN_W = user32.GetSystemMetrics(0)
SCREEN_H = user32.GetSystemMetrics(1)
scale_x = SCREEN_W / BASE_W
scale_y = SCREEN_H / BASE_H

print(f"当前分辨率：{SCREEN_W}x{SCREEN_H}，缩放比例：{scale_x:.2f}x{scale_y:.2f}")

# 自动计算当前分辨率下的区域和行高
REGION = {
    'left': int(45 * scale_x),
    'top': int(225 * scale_y),
    'width': int(655 * scale_x),
    'height': int(600 * scale_y)
}
ROWS = 15
ROW_H = int(40 * scale_y)
DISPLAY_X = int(720 * scale_x)  # 右侧显示文字的 x 坐标
FONT_SIZE = max(12, int(16 * scale_x))  # 字体大小也自适应缩放
FONT = ('Microsoft YaHei', FONT_SIZE, 'bold')
MATCH_CUTOFF = 60
UPDATE_INTERVAL = 0.3

# 兼容打包成 exe 后的文件路径
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(application_path, 'catalog.txt')

# ================== 解析目录 ==================
def load_catalog(path):
    shelf_names = {}
    book_to_shelf = {}
    current = None
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            m = re.match(r'^([12][A-Q])[:：](.+)$', line)
            if m:
                current = m.group(1)
                shelf_names[current] = m.group(2).strip()
                continue
            m = re.match(r'^《(.+?)》$', line)
            if m and current:
                book = m.group(1).strip()
                book_to_shelf[book] = current
    return book_to_shelf, shelf_names

def normalize(s):
    s = s.replace('《', '').replace('》', '')
    s = re.sub(r'(Vol|Vo[l1])\.?\s*\d+', '', s, flags=re.I)
    s = re.sub(r'[\s·・]+', '', s)
    s = s.replace('：', ':').replace('－', '-').replace('—', '-').replace('–', '-')
    return s.strip()

# ================== 初始化 ==================
if not os.path.exists(CATALOG_FILE):
    print(f"错误：找不到目录文件 {CATALOG_FILE}")
    input("按回车键退出...")
    sys.exit(1)

book_to_shelf, shelf_names = load_catalog(CATALOG_FILE)
norm_to_shelf = {normalize(book): shelf for book, shelf in book_to_shelf.items()}
choices = list(norm_to_shelf.keys())

print(f'目录载入：{len(book_to_shelf)} 本书，{len(shelf_names)} 个书架')

# 初始化 RapidOCR
ocr = RapidOCR()

# ================== OCR 与匹配 ==================
def match_shelf(text):
    if not text or not text.strip():
        return None, ''
    norm = normalize(text)
    if not norm:
        return None, ''
    if norm in norm_to_shelf:
        shelf = norm_to_shelf[norm]
        return shelf, shelf_names.get(shelf, '')
    result = process.extractOne(norm, choices, scorer=fuzz.partial_ratio)
    if result:
        match, score, _ = result
        if score >= MATCH_CUTOFF:
            shelf = norm_to_shelf[match]
            return shelf, shelf_names.get(shelf, '')
    return None, ''

# ================== 截屏线程 ==================
q = queue.Queue()
sct = mss.mss()

def grab_region():
    shot = sct.grab(REGION)
    img = np.array(shot)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def worker():
    while True:
        try:
            img = grab_region()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            result, _ = ocr(gray_bgr)
            line_texts = {i: [] for i in range(ROWS)}

            if result:
                for box, text, score in result:
                    ys = [p[1] for p in box]
                    xs = [p[0] for p in box]
                    cy = sum(ys) / 4
                    cx = min(xs)

                    row = int(cy // ROW_H)
                    if 0 <= row < ROWS:
                        line_texts[row].append((cx, text))

            results = []
            for i in range(ROWS):
                sorted_texts = sorted(line_texts[i], key=lambda x: x[0])
                full_text = ''.join([t[1] for t in sorted_texts])
                shelf, shelf_name = match_shelf(full_text)
                results.append((full_text, shelf, shelf_name))

            q.put(results)

        except Exception as e:
            print('worker error:', e)
        time.sleep(UPDATE_INTERVAL)

# ================== 透明 Overlay ==================
root = tk.Tk()
root.overrideredirect(True)
root.attributes('-topmost', True)
root.attributes('-transparentcolor', 'magenta')
root.config(bg='magenta')
root.geometry(f'{SCREEN_W}x{SCREEN_H}+0+0')

canvas = tk.Canvas(root, bg='magenta', highlightthickness=0)
canvas.pack(fill='both', expand=True)

def set_click_through():
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
    except Exception:
        pass

root.after(100, set_click_through)


def draw_text_with_outline(x, y, text, fill='white', outline='black'):
    """画带指定颜色描边的文字（8方向描边，让边缘更饱满）"""
    for dx, dy in [(-1, -1), (-1, 0), (-1, 1), 
                   (0, -1),           (0, 1), 
                   (1, -1),  (1, 0),  (1, 1)]:
        canvas.create_text(x + dx, y + dy, text=text, anchor='w', fill=outline, font=FONT)
    canvas.create_text(x, y, text=text, anchor='w', fill=fill, font=FONT)


def update_overlay():
    try:
        while True:
            results = q.get_nowait()
            canvas.delete('all')
            for i, (text, shelf, shelf_name) in enumerate(results):
                y = REGION['top'] + i * ROW_H + ROW_H // 2
                if shelf:
                    display = f'{shelf}：{shelf_name}'
                    if shelf.startswith('1'):
                        # 1x 书架：白字 + 粉色描边
                        draw_text_with_outline(DISPLAY_X, y, display, 
                                               fill='white', outline='#FF69B4')
                    else:
                        # 2x 书架：白字 + 蓝色描边
                        draw_text_with_outline(DISPLAY_X, y, display, 
                                               fill='white', outline='#00BFFF')
            root.update()
    except queue.Empty:
        pass
    root.after(100, update_overlay)

if __name__ == '__main__':
    print("启动成功！请确保游戏处于【无边框窗口】模式。")
    threading.Thread(target=worker, daemon=True).start()
    update_overlay()
    root.mainloop()