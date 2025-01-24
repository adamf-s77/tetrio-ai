from selenium import webdriver # 叫出同一目錄的selenium和WebDriver
import pyautogui
import time
driver = webdriver.Edge() # 此WebDriver是Chrome版本的
driver.maximize_window()
driver.get("https://tetr.io/") # 前往這個網址

pyautogui.moveTo(950, 670, duration = 1) 
pyautogui.click(clicks=1, interval=0.5, button='left') 

pyautogui.moveTo(920, 550, duration = 1)
pyautogui.click(clicks=1, interval=0.5, button='left') 

pyautogui.moveTo(850, 680, duration = 1)
pyautogui.click(clicks=1, interval=0.5, button='left') 

pyautogui.moveTo(1480, 400, duration = 1)
pyautogui.click(clicks=1, interval=0.5, button='left') 


x,y = pyautogui.position()
while(x > 10 or y > 10):
    print(pyautogui.position())
    x,y = pyautogui.position()
    time.sleep(1)



def piece_colors():
    pass
def piece_index():
    pass
def orientation_columns():
    pass11222222
    lllllll
