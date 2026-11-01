"""
engine.py
Tetris 遊戲與模擬邏輯 (bitmask 實作)
"""

import random
import numpy as np

# 方塊定義: O, I, L, J, S, Z, T -> 0, 1, 2, 3, 4, 5, 6
PIECE_NAMES = ['O', 'I', 'L', 'J', 'S', 'Z', 'T']

PIECE_SHAPE = [
    [[3, 3], [3, 3], [3, 3], [3, 3]],
    [[15], [1, 1, 1, 1], [15], [1, 1, 1, 1]],
    [[7, 1], [1, 1, 3], [4, 7], [3, 2, 2]],
    [[7, 4], [3, 1, 1], [1, 7], [2, 2, 3]],
    [[6, 3], [1, 3, 2], [6, 3], [1, 3, 2]],
    [[3, 6], [2, 3, 1], [3, 6], [2, 3, 1]],
    [[7, 2], [1, 3, 1], [2, 7], [2, 3, 2]]
]

AVAILABLE_CHOICES = [
    [9, 9, 9, 9],
    [7, 10, 7, 10],
    [8, 9, 8, 9],
    [8, 9, 8, 9],
    [8, 9, 8, 9],
    [8, 9, 8, 9],
    [8, 9, 8, 9],
]

AVAILABLE_CHOICES_NUMBER = [9, 17, 34, 34, 17, 17, 34]

# 各方塊合法落子動作 (direction, col)
PIECE_ACTIONS = [
    [(0, c) for c in range(9)],
    [(0, c) for c in range(7)] + [(1, c) for c in range(10)],
    [(0, c) for c in range(8)] + [(1, c) for c in range(9)] + [(2, c) for c in range(8)] + [(3, c) for c in range(9)],
    [(0, c) for c in range(8)] + [(1, c) for c in range(9)] + [(2, c) for c in range(8)] + [(3, c) for c in range(9)],
    [(0, c) for c in range(8)] + [(1, c) for c in range(9)],
    [(0, c) for c in range(8)] + [(1, c) for c in range(9)],
    [(0, c) for c in range(8)] + [(1, c) for c in range(9)] + [(2, c) for c in range(8)] + [(3, c) for c in range(9)],
]


def get_board_features(board):
    """計算盤面特徵：heights, holes, hole_depth, bumpiness, aggregate_height, max_height, wells"""
    heights = [0] * 10
    for r in range(19, -1, -1):
        row = board[r]
        if row:
            for c in range(10):
                if heights[c] == 0 and (row & (1 << (9 - c))):
                    heights[c] = r + 1

    holes = 0
    hole_depth = 0
    for c in range(10):
        h = heights[c]
        if h > 1:
            for r in range(h - 1):
                if not (board[r] & (1 << (9 - c))):
                    holes += 1
                    blocks_above = sum(1 for r2 in range(r + 1, h) if (board[r2] & (1 << (9 - c))))
                    hole_depth += blocks_above

    bumpiness = sum(abs(heights[c] - heights[c + 1]) for c in range(9))
    aggregate_height = sum(heights)
    max_height = max(heights)

    wells = 0
    for c in range(10):
        left_h = 20 if c == 0 else heights[c - 1]
        right_h = 20 if c == 9 else heights[c + 1]
        min_neighbor = min(left_h, right_h)
        if min_neighbor > heights[c]:
            w = min_neighbor - heights[c]
            # 邊緣留井深度 <= 4 不算深井
            if (c == 0 or c == 9) and w <= 4:
                continue
            wells += w * (w + 1) // 2

    return heights, holes, hole_depth, bumpiness, aggregate_height, max_height, wells


def compute_heuristics(board, lines_cleared=0, is_game_over=False, height_punishment_degree=1.0, is_pure_mcts=False):
    """盤面啟發式評估函數"""
    if is_game_over:
        return -100000.0

    heights, holes, hole_depth, bumpiness, aggregate_height, max_height, wells = get_board_features(board)

    if is_pure_mcts:
        # 純 MCTS：線性消行與平整防守
        raw_wells = 0
        for c in range(10):
            lh = 20 if c == 0 else heights[c - 1]
            rh = 20 if c == 9 else heights[c + 1]
            mn = min(lh, rh)
            if mn > heights[c]:
                w = mn - heights[c]
                raw_wells += w * (w + 1) // 2

        score = (
            lines_cleared * 20.0
            - (aggregate_height * 0.6 * height_punishment_degree)
            - (holes * 45.0)
            - (hole_depth * 6.0)
            - (bumpiness * 1.8)
            - (raw_wells * 1.5)
        )
    else:
        # CNN-MCTS：階梯多行獎勵與邊緣留井
        clear_rewards = {0: 0.0, 1: 10.0, 2: 35.0, 3: 75.0, 4: 220.0}
        r_clear = clear_rewards.get(lines_cleared, lines_cleared * 20.0)

        well_bonus = 0.0
        if heights[9] < heights[8] and (heights[8] - heights[9] <= 4):
            well_bonus = (heights[8] - heights[9]) * 4.0

        score = (
            r_clear
            + well_bonus
            - (aggregate_height * 0.45 * height_punishment_degree)
            - (holes * 40.0)
            - (hole_depth * 5.0)
            - (bumpiness * 1.4)
            - (wells * 0.8)
        )

    if max_height > 12:
        score -= ((max_height - 12) ** 2) * 4.0

    return score


def simulate_placement(board, piece, direction, col):
    """模擬落子放置與消行邏輯"""
    piece_shape = PIECE_SHAPE[piece][direction].copy()
    height = len(piece_shape)
    shift = AVAILABLE_CHOICES[piece][direction] - col - 1
    for i in range(height):
        piece_shape[i] = piece_shape[i] << shift

    j = 19 - height
    overlap = 0
    while overlap == 0:
        for i in range(height):
            if j < 0 or (board[j + i] & piece_shape[i] != 0):
                overlap = 1
        j -= 1
    j += 2

    new_board = board.copy()
    clear_lines = 0
    for i in range(height):
        if i + j >= 19:
            return new_board, -1
        new_board[i + j] = new_board[i + j] | piece_shape[i]
        if new_board[i + j] == 1023:
            clear_lines += 1
            new_board = np.delete(new_board, i + j)
            new_board = np.append(new_board, 0)
            j -= 1
    return new_board, clear_lines


class State(object):
    """遊戲狀態封裝類別"""

    def __init__(self, next_pieces, board=None):
        self.board = np.zeros(20, dtype=int) if board is None else board.copy()
        self.now_piece = None
        self.next_pieces = np.array([], dtype=int)
        self.parent_dir_and_col = []
        self.current_score = 0.0
        self.current_value = 0  # 累計消行
        self.step_clear_lines = 0
        self.game_score = 0
        self.clears_count = {1: 0, 2: 0, 3: 0, 4: 0}
        self.combo = 0
        self.height = 0
        self.is_over = False
        self.cumulative_choices_dir = np.array([], dtype=int)
        self.cumulative_choices_col = np.array([], dtype=int)

        if len(next_pieces) != 0:
            self.now_piece = int(next_pieces[0])
            self.next_pieces = np.array(next_pieces[1:], dtype=int)

    def get_current_value(self):
        return self.current_value

    def set_current_value(self, value):
        self.current_value = value

    def get_board_matrix(self):
        matrix = np.zeros((20, 10), dtype=np.uint8)
        for i in range(20):
            for j in range(10):
                if self.board[i] & (1 << (9 - j)):
                    matrix[i][j] = 1
        return matrix

    def get_cumulative_choices_dir(self):
        return self.cumulative_choices_dir

    def set_cumulative_choices_dir(self, direction):
        self.cumulative_choices_dir = np.append(self.cumulative_choices_dir, direction)

    def get_cumulative_choices_col(self):
        return self.cumulative_choices_col

    def set_cumulative_choices_col(self, col):
        self.cumulative_choices_col = np.append(self.cumulative_choices_col, col)

    def get_board(self):
        return self.board

    def set_board(self, board):
        self.board = board

    def show_board(self):
        for i in range(19, -1, -1):
            print(np.binary_repr(self.board[i], width=10))
        print()

    def get_next_pieces(self):
        return self.next_pieces

    def set_next_pieces(self, next_pieces):
        if len(next_pieces) > 0:
            self.now_piece = int(next_pieces[0])
            self.next_pieces = np.array(next_pieces[1:], dtype=int)
        else:
            self.now_piece = None
            self.next_pieces = np.array([], dtype=int)

    def is_terminal(self):
        return self.is_over or self.now_piece is None

    def compute_reward(self):
        return self.current_score

    def place_piece(self, direction, col):
        return simulate_placement(self.board, self.now_piece, direction, col)

    def get_next_state(self, direction, col):
        new_board, clear_lines = self.place_piece(direction, col)
        is_over = (clear_lines == -1)

        future_pieces = list(self.next_pieces)
        if len(future_pieces) > 0:
            future_pieces.append(random.randrange(0, 7))
        else:
            future_pieces = [random.randrange(0, 7)]

        next_state = State(future_pieces, board=new_board)
        next_state.parent_dir_and_col = [direction, col]
        next_state.is_over = is_over
        cleared = max(0, clear_lines)
        next_state.step_clear_lines = cleared
        next_state.current_value = self.current_value + cleared
        next_state.current_score = compute_heuristics(new_board, cleared, is_over)

        # 計分與連鎖
        next_state.clears_count = dict(self.clears_count)
        base_line_scores = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
        piece_drop_points = 29
        if cleared > 0:
            if cleared in next_state.clears_count:
                next_state.clears_count[cleared] += 1
            else:
                next_state.clears_count[cleared] = 1
            next_state.combo = self.combo + 1
            combo_bonus = 50 * max(0, next_state.combo - 1)
            line_score = base_line_scores.get(cleared, cleared * 200) + combo_bonus
            earned = line_score + piece_drop_points
        else:
            next_state.combo = 0
            earned = piece_drop_points
        next_state.game_score = self.game_score + earned

        for r in range(19, -1, -1):
            if next_state.board[r] != 0:
                next_state.height = r
                break

        next_state.cumulative_choices_dir = np.append(self.cumulative_choices_dir, direction)
        next_state.cumulative_choices_col = np.append(self.cumulative_choices_col, col)
        return next_state
