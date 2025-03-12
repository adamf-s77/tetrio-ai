from tensorflow.keras.models import load_model
import mss
import numpy as np
import cv2
import keyboard
import time
import os

# 定義 Tetris 類別
TETRIS_CLASSES = ["O", "I", "T", "S", "Z", "L", "J"]

# 載入已訓練的模型
MODEL_PATH = "C:\\Users\\USER\\Desktop\\tetr_model\\next_pieces.h5"
model = load_model(MODEL_PATH)

# 設定輸出檔案
LOG_FILE = "C:\\Users\\USER\\Desktop\\tetr_model\\next_pieces_log.txt"

# 選擇模式
while True:
    mode = input("請選擇模式：\n1. Leaderboards\n2. Solo\n請輸入 1 或 2：")
    if mode in ["1", "2"]:
        mode = int(mode)
        break
    else:
        print("❌ 無效輸入，請輸入 1 或 2")

# 設定 `top` 調整量
TOP_OFFSET = -45 if mode == 1 else 0

# Next 方塊擷取區域
NEXT_POSITIONS = [
    {"top": 230 + TOP_OFFSET, "left": 1170, "width": 160, "height": 90},
    {"top": 320 + TOP_OFFSET, "left": 1170, "width": 160, "height": 110},
    {"top": 430 + TOP_OFFSET, "left": 1170, "width": 160, "height": 105},
    {"top": 535 + TOP_OFFSET, "left": 1170, "width": 160, "height": 105},
    {"top": 640 + TOP_OFFSET, "left": 1170, "width": 160, "height": 100}
]

print(f"✅ 你選擇了 {'Leaderboards' if mode == 1 else 'Solo'} 模式，Top 偏移量: {TOP_OFFSET}")

# 擷取畫面區域
def capture_region(region):
    with mss.mss() as sct:
        screenshot = sct.grab(region)
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

# 預測函數
def predict_piece(piece_img):
    piece_img = cv2.resize(piece_img, (64, 64)) / 255.0
    piece_img = np.expand_dims(piece_img, axis=0)  # 增加 batch 維度
    predictions = model.predict(piece_img, verbose=0)  # ✅ 關閉進度條
    return TETRIS_CLASSES[np.argmax(predictions)]  # 返回預測結果

previous_pieces = None  # 用於比較前一次的識別結果
print("開始即時識別 Next 方塊，按 ESC 退出...")
with open(LOG_FILE, "w") as log_file:
    while True:
        detected_pieces = []
        for region in NEXT_POSITIONS:
            piece_img = capture_region(region)
            detected_piece = predict_piece(piece_img)
            detected_pieces.append(detected_piece)
        
        # 只有當 Next 5 方塊改變時才輸出，並且持續辨識直到方塊改變
        if previous_pieces is None or detected_pieces != previous_pieces:
            output_line = f"Next 5 Pieces: {detected_pieces}\n"
            print(output_line.strip())
            log_file.write(output_line)
            log_file.flush()
            previous_pieces = detected_pieces
            while True:
                temp_pieces = []
                for region in NEXT_POSITIONS:
                    piece_img = capture_region(region)
                    temp_piece = predict_piece(piece_img)
                    temp_pieces.append(temp_piece)
                
                if temp_pieces != detected_pieces:
                    break
        
        if keyboard.is_pressed("esc"):
            print("\n[INFO] ESC 按鍵偵測到，程式即將退出...")
            break
        
        time.sleep(0.01)  # 每 0.01 秒更新一次
