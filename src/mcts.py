import sys
import math
import random
import os
import time
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None


# OILJSZT -> 0, 1, 2, 3, 4, 5, 6
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

# Unique valid action list (direction, column) for each piece
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
    """
    計算盤面的標準俄羅斯方塊特徵：
    1. heights: 各列當前高度 (0~20)
    2. holes: 封死空洞數 (下方為 0 且上方有 1 的格子數)
    3. hole_depth: 空洞上方被壓住的方塊層數累計
    4. bumpiness: 相鄰列高度落差絕對值總和
    5. aggregate_height: 所有列高度總和
    6. max_height: 最高列高度
    7. wells: 夾壁深井懲罰
    """
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
            wells += w * (w + 1) // 2

    return heights, holes, hole_depth, bumpiness, aggregate_height, max_height, wells


def compute_heuristics(board, lines_cleared=0, is_game_over=False, height_punishment_degree=1.0):
    """
    標準俄羅斯方塊啟發式評估函數：
    - Complete Lines (消除行數)：大幅正獎勵
    - Holes (封死空洞數)：極高負懲罰 (空洞是暴斃主因)
    - Hole Depth (深埋空洞)：重力懲罰上方堆疊塊數
    - Bumpiness (表面平整度)：負懲罰，保持平坦
    - Aggregate Height (總高度)：負懲罰
    - Wells (深井)：懲罰過深難以填補的狹縫
    - Max Height (高空危險)：超過安全高度 (10) 啟動二次方嚴厲懲罰
    """
    if is_game_over:
        return -100000.0

    heights, holes, hole_depth, bumpiness, aggregate_height, max_height, wells = get_board_features(board)

    score = (
        lines_cleared * 25.0
        - (aggregate_height * 0.6 * height_punishment_degree)
        - (holes * 40.0)
        - (hole_depth * 5.0)
        - (bumpiness * 1.8)
        - (wells * 1.2)
    )

    # 高度超過 10 行時啟動非線性危險規避懲罰
    if max_height > 10:
        score -= ((max_height - 10) ** 2) * 4.0

    return score


def simulate_placement(board, piece, direction, col):
    """
    在盤面執行下落放置，模擬方塊物理掉落與消行邏輯。
    返回 (新盤面, 消除行數)；若撞頂暴斃則消除行數返回 -1。
    """
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
    """
    蒙特卡羅樹搜索的遊戲狀態。
    記錄當前盤面、當前方塊、後續方塊隊列、累計得分與消除行數。
    """

    def __init__(self, next_pieces, board=None):
        self.board = np.zeros(20, dtype=int) if board is None else board.copy()
        self.now_piece = None
        self.next_pieces = np.array([], dtype=int)
        self.parent_dir_and_col = []
        self.current_score = 0.0
        self.current_value = 0  # 累計消除行數 (clear lines)
        self.step_clear_lines = 0  # 本步消除行數
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
        next_state.step_clear_lines = max(0, clear_lines)
        next_state.current_value = self.current_value + max(0, clear_lines)
        next_state.current_score = compute_heuristics(new_board, max(0, clear_lines), is_over)

        # 計算最高高度
        for r in range(19, -1, -1):
            if next_state.board[r] != 0:
                next_state.height = r
                break

        next_state.cumulative_choices_dir = np.append(self.cumulative_choices_dir, direction)
        next_state.cumulative_choices_col = np.append(self.cumulative_choices_col, col)
        return next_state

    def get_next_state_with_random_choice(self, direction=None, col=None):
        if direction is None:
            direction = random.randrange(0, 4)
        if col is None:
            col = random.randrange(0, AVAILABLE_CHOICES[self.now_piece][direction])
        return self.get_next_state(direction, col)


class Node(object):
    """
    蒙特卡羅樹搜索樹節點，維護遍歷次數 (visit_times) 與累計質量值 (quality_value)。
    """

    def __init__(self, state=None):
        self.parent = None
        self.children = []
        self.visit_times = 0
        self.quality_value = 0.0
        self.state = state
        self.untried_actions = []
        if state and not state.is_terminal():
            self.untried_actions = list(PIECE_ACTIONS[state.now_piece])
            random.shuffle(self.untried_actions)

    def set_state(self, state):
        self.state = state
        if state and not state.is_terminal():
            self.untried_actions = list(PIECE_ACTIONS[state.now_piece])
            random.shuffle(self.untried_actions)
        else:
            self.untried_actions = []

    def get_state(self):
        return self.state

    def get_parent(self):
        return self.parent

    def set_parent(self, parent):
        self.parent = parent

    def get_children(self):
        return self.children

    def get_visit_times(self):
        return self.visit_times

    def set_visit_times(self, times):
        self.visit_times = times

    def visit_times_add_one(self):
        self.visit_times += 1

    def get_quality_value(self):
        return self.quality_value

    def set_quality_value(self, value):
        self.quality_value = value

    def quality_value_add_n(self, n):
        self.quality_value += n

    def is_all_expand(self):
        return len(self.untried_actions) == 0

    def add_child(self, sub_node):
        sub_node.set_parent(self)
        self.children.append(sub_node)

    def print_children_quality_value(self):
        for i in self.children:
            print(f"{i.quality_value:.2f}", end=' ')
        print()

    def print_children_visited_times(self):
        for i in self.children:
            print(i.get_visit_times(), end=' ')
        print()

    def get_move(self):
        return self.state.parent_dir_and_col[0], self.state.parent_dir_and_col[1]


def tree_policy(node):
    """
    蒙特卡羅樹搜索的 Selection 和 Expansion 階段。
    若節點未完全拓展，隨機拓展一個未嘗試過的動作；否則以 UCB 選擇最佳子節點向下搜索。
    """
    while not node.get_state().is_terminal():
        if not node.is_all_expand():
            sub_node = expand(node)
            return sub_node
        else:
            sub_node = best_child(node, True)
            if sub_node is None:
                return node
            node = sub_node
    return node


def best_child(node, is_exploration, C=10.0):
    """
    使用 UCB1 演算法，權衡 Exploration 與 Exploitation 選擇得分最高之子節點。
    """
    best_score = -sys.maxsize
    best_sub_node = None
    log_n = math.log(max(1, node.get_visit_times()))

    for sub_node in node.get_children():
        if sub_node.get_visit_times() == 0:
            return sub_node

        mean_q = sub_node.get_quality_value() / sub_node.get_visit_times()
        if is_exploration:
            score = mean_q + C * math.sqrt(2.0 * log_n / sub_node.get_visit_times())
        else:
            score = mean_q

        if score > best_score:
            best_score = score
            best_sub_node = sub_node

    return best_sub_node


def expand(node):
    """
    在給定節點上拓展一個新的子節點，選取一項未嘗試動作並產生對應後續盤面狀態。
    """
    if not node.untried_actions:
        return None

    direction, col = node.untried_actions.pop()
    next_state = node.get_state().get_next_state(direction, col)
    sub_node = Node(next_state)
    node.add_child(sub_node)
    return sub_node


def default_policy(node, i=1, height_punishment_degree=1.0):
    """
    蒙特卡羅樹搜索的 Simulation 評估階段。
    以盤面啟發式總評分（包含總高度、空洞數、凹凸度平整度懲罰）評估當前落子，
    並結合隊列中的下一個方塊最佳回應進行前瞻模擬，回傳預期收益。
    """
    state = node.get_state()
    if state.is_terminal():
        return -100000.0

    step1_lines = state.step_clear_lines
    # 若有後續方塊，模擬對手/自身在下一個方塊的最佳落子回應
    if state.now_piece is not None:
        best_val = -float('inf')
        for a in PIECE_ACTIONS[state.now_piece]:
            nb, cl = simulate_placement(state.board, state.now_piece, a[0], a[1])
            sc = compute_heuristics(
                nb,
                lines_cleared=step1_lines + (cl if cl != -1 else 0),
                is_game_over=(cl == -1),
                height_punishment_degree=height_punishment_degree
            )
            if sc > best_val:
                best_val = sc
        return best_val
    else:
        return compute_heuristics(
            state.board,
            lines_cleared=step1_lines,
            is_game_over=False,
            height_punishment_degree=height_punishment_degree
        )


def backup(node, reward, backup_punishment_degree=0.95):
    """
    蒙特卡羅樹搜索的 Backpropagation 階段。
    向樹根回溯更新訪問次數與品質值 (quality_value)。
    """
    curr = node
    r = reward
    while curr is not None:
        curr.visit_times_add_one()
        curr.quality_value_add_n(r)
        r *= backup_punishment_degree
        curr = curr.parent


def monte_carlo_tree_search(node, computation_budget=None, height_punishment_degree=1.0, backup_punishment_degree=0.95):
    """
    蒙特卡羅樹搜索主入口：
    傳入根節點，搜尋最優落子決策。
    若 computation_budget 為 None 或 <= 0，自動設定為當前方塊的全部合法放置數，
    確保當前候選落子全覆蓋評估，避免深度落差懲罰失衡。
    """
    if node.state is None or node.state.now_piece is None:
        return None

    action_count = len(PIECE_ACTIONS[node.state.now_piece])
    if computation_budget is None or computation_budget <= 0:
        computation_budget = action_count
    else:
        computation_budget = max(computation_budget, action_count)

    for i in range(computation_budget):
        expand_node = tree_policy(node)
        if expand_node is None:
            break
        reward = default_policy(expand_node, i, height_punishment_degree)
        backup(expand_node, reward, backup_punishment_degree)

    best_next_node = best_child(node, False)
    return best_next_node


def save_state_image(state, frame_idx, out_dir='frames'):
    """可選輸出盤面圖片 (需安裝 matplotlib)"""
    if not HAS_MATPLOTLIB or plt is None:
        return
    os.makedirs(out_dir, exist_ok=True)
    plt.imshow(state, cmap='gray', interpolation='nearest')
    plt.axis('off')
    plt.savefig(f"{out_dir}/frame_{frame_idx:04d}.png", bbox_inches='tight', pad_inches=0)
    plt.close()


class Last_Node:
    """
    外部介面封裝類別，支援 interface.py 與自動化調用。
    """
    def __init__(self, budget=0, height=1.0, backup=0.95):
        self.current_node = Node()
        self.computation_budget = budget
        self.height_punishment_degree = height
        self.backup_punishment_degree = backup

    def get_move(self, next_pieces, direction=None, col=None):
        if self.current_node.get_state() is None:
            state = State(next_pieces)
            self.current_node.set_state(state)
        else:
            self.current_node.get_state().set_next_pieces(next_pieces)
            self.current_node.set_state(self.current_node.get_state())

        self.current_node.children = []
        self.current_node.visit_times = 0
        self.current_node.quality_value = 0.0
        self.current_node = monte_carlo_tree_search(
            self.current_node,
            self.computation_budget,
            self.height_punishment_degree,
            self.backup_punishment_degree
        )
        if self.current_node is not None:
            return self.current_node.get_move()
        return 0, 0


def main():
    """本機自我測試函式，驗證 MCTS 決策引擎能穩定運行。"""
    print("=== Pure MCTS Tetris Engine 自檢測試 ===")
    initial_pieces = [random.randrange(0, 7) for _ in range(6)]
    init_state = State(initial_pieces)
    init_node = Node(init_state)
    current_node = init_node

    total_cleared = 0
    start_time = time.time()
    for i in range(1, 2001):
        budget = len(PIECE_ACTIONS[current_node.state.now_piece])
        current_node = monte_carlo_tree_search(current_node, computation_budget=budget)

        if current_node is None or current_node.get_state().is_terminal():
            print(f"遊戲結束於第 {i} 步，累計消行數: {total_cleared}")
            break

        total_cleared = current_node.get_state().get_current_value()

        if i % 100 == 0:
            elapsed = time.time() - start_time
            print(f"步數: {i:4d} | 消行數: {total_cleared:4d} | 耗時: {elapsed:.2f}s | FPS: {i / elapsed:.1f}")

        if total_cleared >= 300:
            elapsed = time.time() - start_time
            print(f"\n[SUCCESS] 成功達成目標！於第 {i} 步完成消除 {total_cleared} 行！總耗時: {elapsed:.2f}s")
            break

        # 推進下一輪搜尋
        current_node = Node(current_node.get_state())


if __name__ == "__main__":
    main()
