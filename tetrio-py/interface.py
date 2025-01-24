from selenium import webdriver # 叫出同一目錄的selenium和WebDriver
import pyautogui
import time

#找滑鼠位置
# x,y = pyautogui.position()
# while(x > 10 or y > 10):
#     print(pyautogui.position())
#     x,y = pyautogui.position()
#     time.sleep(1)


URL = "https://tetr.io/"

#下面位置數字還沒改
NEXT_PIECE_POSITION_X =0
NEXT_PIECE_POSITION_Y =0
NEXT_PIECE_WIDTH =0
NEXT_PIECE_HEIGHT =0
NEXT_PIECE_COUNT =0

JOIN_X = 950
JOIN_Y = 670

SOLO_X = 920
SOLO_Y = 550

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

# const nearestColour = require('nearest-color').from(PIECE_COLOURS);

# function getLuminence(colour) {
#     const r = Number.parseInt(colour.slice(0, 2), 16);
#     const g = Number.parseInt(colour.slice(2, 4), 16);
#     const b = Number.parseInt(colour.slice(4, 6), 16);

#     return 0.2126 * r + 0.7152 * g + 0.0722 * b;
# }

class tetrio_bot():
    def __init__(self):
        self.current_column = 4 #5 if 0
        self.eltetris = 'new ElTetris(10,20)' #後面要改成自己的ai
        self.move = 0

    def start_game(self):
        pyautogui.moveTo(JOIN_X, JOIN_Y, duration = 1) 
        pyautogui.click(clicks=1, interval=0.5, button='left') 
        pyautogui.moveTo(SOLO_X, SOLO_Y, duration = 1)
        pyautogui.click(clicks=1, interval=0.5, button='left') 
        pyautogui.moveTo(BLITZ_X, BLITZ_Y, duration = 1)
        pyautogui.click(clicks=1, interval=0.5, button='left') 
        pyautogui.moveTo(START_X, START_Y, duration = 1)
        pyautogui.click(clicks=1, interval=0.5, button='left') 

        self.current_pieces = self.get_next_pieces()
        self.get_next_piece()
        time.sleep(1.8)

    def get_next_pieces(self):
        # const nextPiecesBitmap = robot.screen.capture(
        #     NEXT_PIECE_POSITION_X,
        #     NEXT_PIECE_POSITION_Y,
        #     NEXT_PIECE_WIDTH,
        #     NEXT_PIECE_HEIGHT * NEXT_PIECE_COUNT
        # );

        # const pieces = [];

        # for (let i = 0; i < NEXT_PIECE_COUNT; i += 1) {
        #     let x = 0;
        #     let y = i * NEXT_PIECE_HEIGHT;

        #     const distance = Math.sqrt(
        #         Math.pow(NEXT_PIECE_WIDTH / 2, 2) +
        #             Math.pow(NEXT_PIECE_HEIGHT / 2, 2)
        #     );

        #     const colours = [];

        #     for (let j = 0; j < Math.floor(distance); j += 1) {
        #         const colour = nextPiecesBitmap.colorAt(x + j, y + j);

        #         if (getLuminence(colour) <= 90) {
        #             continue;
        #         }

        #         colours.push(`#${colour}`);
        #     }

        #     console.log(
        #         nearestColour(averageColour(colours)).name,
        #         averageColour(colours)
        #     );

        #     pieces.push(nearestColour(averageColour(colours)).name);
        # }

        # //spawn('import', ['-w', 'root', `./screenshot-${pieces.join(',')}.png`]);

        # return pieces;
        return 0
    
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
    def get_next_piece(self):
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
        driver.maximize_window()
        driver.get(URL)
        self.start_game()
        while(1):
            self.play_move()

# main
tetriobot = tetrio_bot()
tetriobot.init()
