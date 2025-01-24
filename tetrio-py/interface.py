from selenium import webdriver # 叫出同一目錄的selenium和WebDriver
import pyautogui
import time

# driver = webdriver.Edge() # 此WebDriver是Chrome版本的
# driver.maximize_window()
# driver.get("https://tetr.io/") # 前往這個網址

# pyautogui.moveTo(950, 670, duration = 1) 
# pyautogui.click(clicks=1, interval=0.5, button='left') 

# pyautogui.moveTo(920, 550, duration = 1)
# pyautogui.click(clicks=1, interval=0.5, button='left') 

# pyautogui.moveTo(850, 680, duration = 1)
# pyautogui.click(clicks=1, interval=0.5, button='left') 

# pyautogui.moveTo(1480, 400, duration = 1)
# pyautogui.click(clicks=1, interval=0.5, button='left') 



x,y = pyautogui.position()
while(x > 10 or y > 10):
    print(pyautogui.position())
    x,y = pyautogui.position()
    time.sleep(1)



def piece_colors():
    'T': '#b151a7',  # 紫色
    'L': '#ba6d3e',  # 橙色
    'O': '#b9a13c',  # 黃色
    'J': '#7969c6',  # 藍色
    'I': '#3db388',  # 深綠色
    'Z': '#bb3e44',  # 紅色
    'S': '#82ac3b'   # 綠色
def piece_index():
    pass
def orientation_columns():
    pass

class tetrio_bot():
    def __init__(self):
        pass
    def launch_edge():
        pass
    def start_game():
        pass
    def get_next_pieces():
        pass
    def move_left():
        pass
    def move_right():
        pass
    def drop_piece():
        pass
    def change_to_orientation():
        pass
    def move_to_column():
        pass
    def get_next_piece():
        pass
    def play_move():
        pass
    def init():
        pass

# main
tetriobot = tetrio_bot()
tetriobot.init()
