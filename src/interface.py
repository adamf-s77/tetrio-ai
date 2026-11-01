from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import pyautogui
import keyboard
import time
from PIL import Image, ImageGrab, ImageDraw
import math
import colorsys
import os
import copy
import sys

# 確保輸出支援 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 支援 Windows DPI 縮放校準
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import mcts
except ImportError:
    from src import mcts
import numpy as np

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02  # 快速且穩健的按鍵響應

URL = "https://tetr.io/"

# 讀取 .env 中的偵測座標與尺寸設定 (提供最佳 1920x1080 預設值)
NEXT_PIECE_POSITION_X = int(os.getenv("NEXT_PIECE_X", "1210"))
NEXT_PIECE_POSITION_Y = int(os.getenv("NEXT_PIECE_Y", "350"))
NEXT_PIECE_WIDTH = int(os.getenv("NEXT_PIECE_WIDTH", "95"))     # 加寬至 95px，完整涵蓋方塊區域
NEXT_PIECE_HEIGHT = int(os.getenv("NEXT_PIECE_HEIGHT", "96"))   # 每個槽位高度
NEXT_PIECE_COUNT = 5

# 盤面生成點區域 (用於偵測開局第一塊)
SPAWN_AREA_X = int(os.getenv("SPAWN_AREA_X", "910"))
SPAWN_AREA_Y = int(os.getenv("SPAWN_AREA_Y", "260"))
SPAWN_AREA_WIDTH = int(os.getenv("SPAWN_AREA_WIDTH", "100"))
SPAWN_AREA_HEIGHT = int(os.getenv("SPAWN_AREA_HEIGHT", "80"))

piece_index = {
    'O': 0,
    'I': 1,
    'L': 2,
    'J': 3,
    'S': 4,
    'Z': 5,
    'T': 6
}

orientation_columns = {
    'O': [4, 4, 4, 4],
    'I': [3, 4, 3, 5],
    'L': [3, 3, 3, 4],
    'J': [3, 3, 3, 4],
    'S': [3, 3, 3, 4],
    'Z': [3, 3, 3, 4],
    'T': [3, 3, 3, 4]
}


def find_coordinate():
    """等待滑鼠移至螢幕左上角 (x < 10, y < 10) 觸發啟動"""
    x, y = pyautogui.position()
    while y > 10 or x > 10:
        print(f"\r[等待啟動] 目前游標: ({x:4d}, {y:4d}) -> 請將滑鼠移至螢幕【左上角 (x<10, y<10)】開始！", end="", flush=True)
        time.sleep(0.3)
        x, y = pyautogui.position()
    print("\n>> 偵測到滑鼠位於左上角，啟動 AI 自動落子！")
    return 1        


def find_coordinate1():
    """安全停止機制：滑鼠移至螢幕右上角 (x > 1000, y < 10) 即可安全停止"""
    x, y = pyautogui.position()
    if x > 1000 and y < 10:
        print("\n>> 偵測到滑鼠移至右上角，AI 自動遊玩已安全停止。")
        return 0        
    return 1


def detect_piece_from_image(image_crop):
    """
    使用 HSV 色相（Hue）直方圖多數決演算法，精準辨識方塊：
    - 忽略黑色/深灰色背景 (過濾 S < 0.35 或 V < 0.35)
    - 根據 7 種標準色相區間精確投票，徹底避免 RGB 歐氏距離誤判
    """
    width, height = image_crop.size
    piece_votes = {'Z': 0, 'L': 0, 'O': 0, 'S': 0, 'I': 0, 'J': 0, 'T': 0}
    colored_pixels = 0

    # 隔步採樣（每 2 像素採樣一次，兼具高速與精確）
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            r, g, b = image_crop.getpixel((x, y))[:3]
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)

            # 僅統計具備足夠飽和度與亮度的方塊像素
            if s > 0.35 and v > 0.35:
                colored_pixels += 1
                deg = h * 360.0
                if deg <= 12 or deg >= 340:
                    piece_votes['Z'] += 1  # 紅色
                elif 13 <= deg <= 35:
                    piece_votes['L'] += 1  # 橘色
                elif 36 <= deg <= 65:
                    piece_votes['O'] += 1  # 黃色
                elif 66 <= deg <= 125:
                    piece_votes['S'] += 1  # 綠色
                elif 126 <= deg <= 190:
                    piece_votes['I'] += 1  # 青色 / 淺藍
                elif 191 <= deg <= 270:
                    piece_votes['J'] += 1  # 深藍
                elif 271 <= deg <= 339:
                    piece_votes['T'] += 1  # 紫色 / 洋紅

    # 若彩色像素過少，代表該區域為空
    if colored_pixels < 8:
        return None, 0

    best_piece = max(piece_votes, key=piece_votes.get)
    return best_piece, colored_pixels


class tetrio_bot:
    def __init__(self):
        self.currentColumn = 4 
        self.currentPiece = 'T'
        self.cp = 'T'
        self.rotation = 0
        self.column = 0

    def capture_next_pieces_area(self):
        """截取 NEXT 隊列全部區域並返回 PIL Image"""
        left = NEXT_PIECE_POSITION_X
        top = NEXT_PIECE_POSITION_Y
        right = left + NEXT_PIECE_WIDTH
        bottom = top + NEXT_PIECE_HEIGHT * NEXT_PIECE_COUNT
        return ImageGrab.grab(bbox=(left, top, right, bottom))

    def detect_spawn_piece(self):
        """偵測盤面正上方生成點的當前落下方塊"""
        try:
            crop = ImageGrab.grab(bbox=(
                SPAWN_AREA_X, SPAWN_AREA_Y,
                SPAWN_AREA_X + SPAWN_AREA_WIDTH,
                SPAWN_AREA_Y + SPAWN_AREA_HEIGHT
            ))
            piece, votes = detect_piece_from_image(crop)
            return piece
        except Exception:
            return None

    def get_next_pieces(self, save_debug=False):
        """辨識 NEXT 隊列中的 5 個後續方塊"""
        big_screenshot = self.capture_next_pieces_area()
        pieces = []

        if save_debug:
            debug_img = big_screenshot.copy()
            draw = ImageDraw.Draw(debug_img)

        for i in range(NEXT_PIECE_COUNT):
            y_start = i * NEXT_PIECE_HEIGHT
            y_end = y_start + NEXT_PIECE_HEIGHT - 6
            crop = big_screenshot.crop((0, y_start, NEXT_PIECE_WIDTH, y_end))

            piece_name, votes = detect_piece_from_image(crop)
            if piece_name is None:
                # 若未偵測到（例如陰影或特殊特效），預設回退為 T
                piece_name = 'T'

            pieces.append(piece_name)

            if save_debug:
                draw.rectangle([(2, y_start + 2), (NEXT_PIECE_WIDTH - 2, y_end - 2)], outline="red", width=2)
                draw.text((10, y_start + 5), f"{piece_name} ({votes})", fill="yellow")

        if save_debug:
            try:
                debug_img.save("debug_queue_detection.png")
                print(">> [調試截圖] 已儲存 debug_queue_detection.png，可檢視方塊偵測框！")
            except Exception:
                pass

        return pieces
    
    def turnLeft(self):
        pyautogui.press('z')
    
    def turnRight(self):
        pyautogui.press('x')
    
    def moveLeft(self):
        pyautogui.press('left')
    
    def moveRight(self):
        pyautogui.press('right')
    
    def dropPiece(self):
        pyautogui.press('space')

    def playMove(self):
        """根據 MCTS 決策執行旋轉、移動與硬降"""
        rot = self.rotation % 4
        possible_orientations = orientation_columns.get(self.cp, [3, 3, 3, 3])
        self.currentColumn = possible_orientations[rot]
        print(f"落子 [{self.cp}] 旋轉: {rot} 次 | 目標列: {self.column} (起始: {self.currentColumn})")

        # 1. 旋轉方塊 (按 z 逆時針旋轉)
        for _ in range(rot):
            self.turnLeft()

        # 2. 水平平移至目標列
        delta = self.column - self.currentColumn
        if delta < 0:
            for _ in range(abs(delta)):
                self.moveLeft()
        elif delta > 0:   
            for _ in range(delta):
                self.moveRight()
        
        # 3. 關鍵防抖：等待 40ms 確保瀏覽器已完成位移，再執行硬降
        time.sleep(0.04)
        self.dropPiece()

    def init(self):
        # 讀取 .env 參數
        budget = int(os.getenv("TETRIS_MCTS_BUDGET", "0"))
        height = float(os.getenv("TETRIS_HEIGHT_PUNISHMENT", "1.0"))
        backup = float(os.getenv("TETRIS_BACKUP_PUNISHMENT", "0.95"))
        browser_type = os.getenv("TETRIS_BROWSER", "edge").strip().lower()

        print("\n" + "=" * 65)
        print("【已自動自 .env 載入 Tetris AI 參數配置】")
        budget_desc = "自動全候選動作覆蓋 (推薦, 極速且最穩)" if budget == 0 else f"{budget} 次 MCTS 模擬"
        print(f" - MCTS 搜尋預算 (TETRIS_MCTS_BUDGET)      : {budget} ({budget_desc})")
        print(f" - 盤面高度懲罰 (TETRIS_HEIGHT_PUNISHMENT) : {height}")
        print(f" - 回溯衰減因子 (TETRIS_BACKUP_PUNISHMENT) : {backup}")
        print(f" - 目標瀏覽器   (TETRIS_BROWSER)           : {browser_type.upper()}")
        print(f" - NEXT 偵測框  : X={NEXT_PIECE_POSITION_X}, Y={NEXT_PIECE_POSITION_Y}, W={NEXT_PIECE_WIDTH}, H={NEXT_PIECE_HEIGHT}")
        print("=" * 65)

        print(f"\n>> 正在以極速模式 (eager) 啟動 {browser_type.upper()} 瀏覽器開啟 TETR.IO...")
        driver = None
        if browser_type == "chrome":
            opts = ChromeOptions()
            opts.page_load_strategy = 'eager'  # 解決「啟動太久」：不等資源完全閒置，頁面骨架就緒即返回
            try:
                driver = webdriver.Chrome(options=opts)
            except Exception as e:
                print(f"Chrome 啟動失敗 ({e})，改用 Edge...")
                edge_opts = EdgeOptions()
                edge_opts.page_load_strategy = 'eager'
                driver = webdriver.Edge(options=edge_opts)
        else:
            opts = EdgeOptions()
            opts.page_load_strategy = 'eager'  # 解決「啟動太久」
            try:
                driver = webdriver.Edge(options=opts)
            except Exception as e:
                print(f"Edge 啟動失敗 ({e})，改用 Chrome...")
                chrome_opts = ChromeOptions()
                chrome_opts.page_load_strategy = 'eager'
                driver = webdriver.Chrome(options=chrome_opts)

        driver.set_window_size(1920, 1080)
        driver.set_window_position(0, 0)
        driver.get(URL)

        while True:
            print("\n" + "=" * 65)
            print("【TETR.IO 實機 AI 對戰就緒】")
            print(" 1. 請在瀏覽器點擊進入 TETR.IO 遊戲 (建議 SOLO -> QUICK PLAY / BLITZ)")
            print(" 2. 進入遊戲倒數完畢後，將滑鼠移至【螢幕左上角 (x < 10, y < 10)】開始！")
            print(" 3. 隨時將滑鼠移至【螢幕右上角 (x > 1000, y < 10)】即可暫停停止。")
            print("=" * 65 + "\n")

            if find_coordinate() != 2:
                last_node = mcts.Last_Node(budget, height, backup)
                
                # 初始偵測 NEXT 隊列與首塊
                next_queue = self.get_next_pieces(save_debug=True)
                spawn_p = self.detect_spawn_piece()
                active_piece = spawn_p if spawn_p is not None else next_queue[0]

                print(f">> 初始就緒！當前落子首塊: [{active_piece}] | 後續預覽隊列: {next_queue}")
                time.sleep(1.0)

                # 對戰主迴圈 (解決隊列錯位：active_piece 與實機落子完全同步)
                step = 0
                while find_coordinate1():
                    step += 1
                    # 組合本次 MCTS 決策隊列: [active_piece] + next_queue
                    num_pieces = np.array([piece_index.get(active_piece, 0)] + [piece_index.get(p, 0) for p in next_queue])
                    
                    self.cp = active_piece
                    self.rotation, self.column = last_node.get_move(num_pieces)
                    
                    # 執行操作下落
                    self.playMove()
                    
                    # 實機上下落後，原本的 next_queue[0] 自動成為下一輪的 active_piece！
                    active_piece = next_queue[0]
                    
                    # 稍候 0.05 秒讓網頁畫面更新方塊隊列
                    time.sleep(0.05)
                    
                    # 重新截圖抓取最新 NEXT 隊列
                    next_queue = self.get_next_pieces()
                    print(f"第 {step:4d} 步完成 | 下一塊: [{active_piece}] | 後續: {next_queue}")


# main
if __name__ == "__main__":
    tetriobot = tetrio_bot()
    tetriobot.init()
