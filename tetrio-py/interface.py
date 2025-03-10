from selenium import webdriver # 叫出同一目錄的selenium和WebDriver
import pyautogui
import time
from PIL import Image, ImageGrab
import math
import testmcts

def find_coordinate():
    x,y = pyautogui.position()
    while(x > 10 or y > 10):
        print(pyautogui.position())
        x,y = pyautogui.position()
        time.sleep(1)


URL = "https://tetr.io/"
  
#下面位置數字還沒改
NEXT_PIECE_POSITION_X =1240
NEXT_PIECE_POSITION_Y =370
NEXT_PIECE_WIDTH =20
NEXT_PIECE_HEIGHT =96
NEXT_PIECE_COUNT =5

JOIN_X = 950
JOIN_Y = 670

SOLO_X = 920
SOLO_Y = 640

BLITZ_X = 880
BLITZ_Y = 420

START_X = 1580
START_Y = 420



piece_colors = {
    'T': '#b151a7',
    'L': '#ba6d3e',
    'O': '#b9a13c',
    'J': '#7969c6',
    'I': '#3db388',
    'Z': '#bb3e44',
    'S': '#82ac3b'
}

piece_index = {
    'I': 0,
    'T': 1,
    'O': 2,
    'J': 3,
    'L': 4,
    'S': 5,
    'Z': 6
}

orientation_columns = {
    'I': [4,6],
    'T': [4,5,4,4],
    'O': [5],
    'L': [4,5,4,4],
    'S': [4,5],
    'J': [4,5,4,4],
    'Z': [4,5]
}



def get_luminance(r, g, b):
    """
    參考原 JS 的亮度公式:
    0.2126 * R + 0.7152 * G + 0.0722 * B
    這裡直接用整數 r, g, b 計算
    """
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

class tetrio_bot():
    def __init__(self):
        self.current_column = 4 #5 if 0
        self.eltetris = 'new ElTetris(10,20)' #後面要改成自己的ai
        self.move = 0

    def start_game(self):
        # pyautogui.moveTo(JOIN_X, JOIN_Y, duration = 1) 
        # pyautogui.click(clicks=1, interval=0.5, button='left') 
        # pyautogui.moveTo(SOLO_X, SOLO_Y, duration = 1)
        # pyautogui.click(clicks=1, interval=0.5, button='left') 
        # pyautogui.moveTo(BLITZ_X, BLITZ_Y, duration = 1)
        # pyautogui.click(clicks=1, interval=0.5, button='left') 
        # pyautogui.moveTo(START_X, START_Y, duration = 1)
        # pyautogui.click(clicks=1, interval=0.5, button='left') 
        find_coordinate()
        self.current_pieces = self.get_next_pieces()
        time.sleep(1.8)

    
    def capture_next_pieces_area(self):
        """
        依照 NEXT_PIECE_* 參數，
        截下「所有下一個方塊」所在的長條畫面並回傳 PIL Image。
        """
        left = NEXT_PIECE_POSITION_X
        top = NEXT_PIECE_POSITION_Y
        right = left + NEXT_PIECE_WIDTH
        bottom = top + NEXT_PIECE_HEIGHT * NEXT_PIECE_COUNT

        # 使用 Pillow 截圖
        # 在某些環境可直接 ImageGrab.grab(bbox=(left, top, right, bottom))
        # 若失敗，請考慮使用其他函式庫 (pyscreenshot, mss) 或在 Linux headless 下使用 Xvfb
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        return screenshot



    # -----------------------------
    # 4) 將一串顏色 (RGB) 做平均
    # -----------------------------
    def average_color(self, rgb_list):
        """
        傳入 [(r1, g1, b1), (r2, g2, b2), ...]，回傳 (avg_r, avg_g, avg_b)
        """
        if not rgb_list:
            return (0,0,0)  # 若沒有任何像素，回傳黑色避免錯誤
        sum_r = sum(c[0] for c in rgb_list)
        sum_g = sum(c[1] for c in rgb_list)
        sum_b = sum(c[2] for c in rgb_list)
        count = len(rgb_list)
        return (sum_r // count, sum_g // count, sum_b // count)

    # -----------------------------
    # 5) 找出「最接近」的已知方塊顏色
    # -----------------------------
    def rgb_to_hex(self, rgb):
        """(r, g, b) -> '#rrggbb'"""
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    def hex_to_rgb(self, hex_code):
        """'#rrggbb' -> (r, g, b)"""
        hex_code = hex_code.strip('#')
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return (r, g, b)

    def color_distance(self, c1, c2):
        """兩個 RGB 色的歐幾里得距離"""
        return math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2)

    def nearest_piece_name(self, avg_rgb):
        """
        傳入(平均)RGB後，在 PIECE_COLOURS 字典中找「距離最小」的顏色，
        回傳該方塊的名稱 (T, L, O, J, I, Z, S)。
        """
        best_name = None
        min_dist = float('inf')

        for piece_name, hex_col in piece_colors.items():
            known_rgb = self.hex_to_rgb(hex_col)
            dist = self.color_distance(avg_rgb, known_rgb)
            if dist < min_dist:
                min_dist = dist
                best_name = piece_name
        return best_name

    # -----------------------------
    # 6) 主函式：逐塊掃描對角線像素、濾暗色、算平均、比對方塊
    # -----------------------------
    def get_next_pieces(self):
    # 先整體截圖
        big_screenshot = self.capture_next_pieces_area()
        width, height = big_screenshot.size  # 應該是 (NEXT_PIECE_WIDTH, NEXT_PIECE_HEIGHT * NEXT_PIECE_COUNT)
        print(f"Screenshot size: {width}x{height}")

        # 存放最終結果，例如 ['T', 'O', 'L', ...]
        pieces = []

        # 每個方塊的區域高度是 NEXT_PIECE_HEIGHT
        # 逐個區塊處理
        for i in range(NEXT_PIECE_COUNT):
            # 計算此方塊在 big_screenshot 裡的 y 座標起始
            piece_y_start = i * NEXT_PIECE_HEIGHT
            piece_x_start = 0
            print(f"Processing piece {i+1}/{NEXT_PIECE_COUNT} at y={piece_y_start}")

            # 計算對角線可用最大距離 (與 JS 一樣)
            distance = math.sqrt((NEXT_PIECE_WIDTH / 2)**2 + (NEXT_PIECE_HEIGHT / 2)**2)
            print(f"Diagonal distance: {distance}")

            # 收集本區塊的顏色 (只取對角線範圍像素)
            collected_colors = []
            for j in range(int(distance)):
                px = piece_x_start + j
                py = piece_y_start + j

                # 判斷邊界，以免 py 或 px 超過該方塊範圍
                if px >= NEXT_PIECE_WIDTH or py >= (piece_y_start + NEXT_PIECE_HEIGHT):
                    break

                # 取得像素 (r, g, b)
                r, g, b = big_screenshot.getpixel((px, py))
                luminance = get_luminance(r, g, b)

                # 濾除暗色 (亮度 <= 90 不要)
                if luminance > 90:
                    collected_colors.append((r, g, b))
                else:
                    print(luminance)

            print(f"Collected {len(collected_colors)} colors for piece {i+1}")

            # 計算平均色
            avg_rgb = self.average_color(collected_colors)
            print(f"Average color for piece {i+1}: {avg_rgb}")

            # 找出對應的最接近方塊
            piece_name = self.nearest_piece_name(avg_rgb)
            print(f"Detected piece name for piece {i+1}: {piece_name}")

            pieces.append(piece_name)

        # 打印結果
        print("Detected pieces:", pieces)
        return pieces
        
    
    def move_left(self):
        pyautogui.press('left')

    def move_right(self):
        pyautogui.press('right')

    def drop_piece(self):
        pyautogui.press('space')

    def change_to_orientation(self,orientation):
        for i in range(orientation):
            pyautogui.press('up')
        self.current_column = orientation_columns[self.current_piece][orientation]


    def move_to_column(self):
        pass
    def play_move(self):
        # const {
        #     orientationIndex,
        #     orientation,
        #     column
        # } = this.eltetris.pickMove(PIECE_INDEXES[this.currentPiece]);

        # this.eltetris.playMove(this.eltetris.board, orientation, column);

        # console.log(
        #     'move #',
        #     this.moves,
        #     'played',
        #     this.currentPiece,
        #     'at column',
        #     column
        # );

        # ElTetris.drawBoard(this.eltetris.board);
        pass
    
    def init(self):
        driver = webdriver.Edge()
        driver.set_window_size(1920,1080)
        driver.set_window_position(0,0)
        driver.get(URL)
        self.start_game()
        find_coordinate()

# main
tetriobot = tetrio_bot()
tetriobot.init()

move = func(next_pieces)
