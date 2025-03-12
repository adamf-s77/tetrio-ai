
import sys
import math
import random
import numpy as np
import time

#OILJSZT -> 0123456
#top left down right -> 0123
#ex: 
# x    x xxx xx
# xxx  x   x x
#     xx     x 

#left right turnleft turnright down -> 01234

# T4
# O5
# L4
# S4
# J4
# Z4
# I4

PIECE_SHAPE = [
    [[3,3]],
    [[15],[1,1,1,1]],
    [[7,1],[1,1,3],[4,7],[3,2,2]],
    [[7,4],[3,1,1],[1,7],[2,2,3]],
    [[6,3],[1,3,2],[6,3],[1,3,2]],
    [[3,6],[2,3,1],[3,6],[2,3,1]],
    [[7,2],[1,3,1],[2,7],[2,3,2]]
]



AVAILABLE_CHOICES = [
    [9],
    [7,10],
    [8,9,8,9],
    [8,9,8,9],
    [8,9,8,9],
    [8,9,8,9],
    [8,9,8,9],
]

AVAILABLE_CHOICES_NUMBER = [9,17,34,34,34,34,34]

class State(object):
    """
    蒙特卡羅樹搜索的游戏状态，记录在某一个Node节点下的状态数据，包含当前的游戏得分、当前的游戏round数等。
    需要实现判断当前状态是否达到游戏结束状态，支持从Action集合中随机取出操作。
    """

    def __init__(self,next_pieces):
        self.current_value = 0
        # For the first root node, the index is 0 and the game should start from 1
        # self.current_round_index = 0
        self.cumulative_choices_dir = np.array([],dtype = int)
        self.cumulative_choices_col = np.array([],dtype = int)
        self.board = np.zeros(20,dtype = int)
        if(len(next_pieces) > 0):
            self.now_piece = next_pieces[0] 
            self.next_pieces = np.delete(next_pieces,0) 
        else:
            self.now_piece = None
            self.next_pieces = None



    def get_current_value(self):
        return self.current_value

    def set_current_value(self, value):
        self.current_value = value

    # def get_current_round_index(self):
    #     return self.current_round_index

    # def set_current_round_index(self, turn):
    #     self.current_round_index = turn

    def get_cumulative_choices_dir(self):
        return self.cumulative_choices_dir

    def set_cumulative_choices_dir(self, dir):
        self.cumulative_choices_dir = np.append(self.cumulative_choices_dir,dir)

    def get_cumulative_choices_col(self):
        return self.cumulative_choices_col

    def set_cumulative_choices_col(self, col):
        self.cumulative_choices_col = np.append(self.cumulative_choices_col,col)


    def get_board(self):
        return self.board

    def set_board(self, board):
        self.board = board

    def show_board(self):
        for i in range(19,-1,-1):
            print(np.binary_repr(self.board[i],width = 10))
        print()

    def get_next_pieces(self):
        return self.next_pieces
    
    def set_next_pieces(self,next_pieces):
        self.next_pieces = next_pieces

    def is_terminal(self):
       return self.now_piece == None

    def compute_reward(self):
        return self.current_value
    
    def place_piece(self,dir,col):
        piece_shape = PIECE_SHAPE[self.now_piece][dir].copy()
        height = len(piece_shape)


        for i in range(height):
            piece_shape[i] = piece_shape[i] << (AVAILABLE_CHOICES[self.now_piece][dir] - col - 1)


        j = 19
        while self.board[j] & piece_shape[0] == 0 and j >= 0: j -= 1
        j += 1
        new_board = self.board.copy()

        clear_lines = 0
        for i in range(height):
            if(i+j == 20): return new_board,-1
            new_board[i+j] = new_board[i+j] | piece_shape[i]
            if(new_board[i+j] == 1023):
                clear_lines += 1
                new_board = np.delete(new_board,i+j)
                new_board = np.append(new_board,0)
                j -= 1
        return new_board,clear_lines



    def get_next_state_with_random_choice(self):
        #get choice
        if self.now_piece == 0: dir = 0
        elif self.now_piece == 1: dir = random.randrange(0,2)
        else: dir = random.randrange(0,4)  #top left down right -> 0123
        col = random.randrange(0,AVAILABLE_CHOICES[self.now_piece][dir])

        new_board,value = self.place_piece(dir,col)
        if(value == -1):
            next_state = State(np.array([]))
            next_state.set_cumulative_choices_dir(dir)
            next_state.set_cumulative_choices_col(col)
            return next_state
        next_state = State(self.next_pieces)
        next_state.set_board(new_board)
        next_state.set_cumulative_choices_dir(dir)
        next_state.set_cumulative_choices_col(col)
        return next_state




class Node(object):
    """
    蒙特卡洛樹搜索的樹結構的Node。包含了父節點和直接夠的資訊，還有用于計算UCB的遍历次数等信息。
    """

    def __init__(self):
        self.parent = None
        self.children = []
        self.visit_times = 0
        self.quality_value = 0.0
        self.state = None

    def set_state(self, state):
        self.state = state

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
        return len(self.children) == AVAILABLE_CHOICES_NUMBER[self.state.now_piece]

    def add_child(self, sub_node):
        sub_node.set_parent(self)
        self.children.append(sub_node)

    def __repr__(self):
        return "Node: {}, Q/N: {}/{}, state: {}".format(
            hash(self), self.quality_value, self.visit_times, self.state
        )

def tree_policy(node):
    """
    蒙特卡罗树搜索的Selection和Expansion阶段，传入当前需要开始搜索的节点（例如根节点）。
    基本策略是先找当前未选择过的子节点，如果是多个则随机选。如果都被选择过就按权衡过
    """

    # Check if the current node is the leaf node
    while node.get_state().is_terminal() == False:
        if node.is_all_expand():
            node = best_child(node, True)
        else:
            # Return the new sub node
            sub_node = expand(node)
            return sub_node
    # Return the leaf node
    return node


def default_policy(node):
    """
    蒙特卡罗树搜索的Simulation阶段，输入一个需要expand的节点，随机操作后创建新的节点。
    基本策略是随机选择Action。
    """

    # Get the state of the game
    current_state = node.get_state()

    # Run until the game over
    while current_state.is_terminal() == False:
        # Pick one random action to play and get next state
        current_state = current_state.get_next_state_with_random_choice()
        # current_state.set_next_pieces(np.append(current_state.get_next_pieces(),random.randrange(0,7)))#增加深度用
    
    return current_state.get_current_value()


def if_board_in_lst(board,lst):

    for i in lst:
        if(board == i).all():
            return True
    return False


def expand(node):
    """
    输入一个节点，在该节点上拓展一个新的节点，使用random方法执行Action，返回新增的节点。注意，需要
    """

    tried_sub_node_states = [
        sub_node.get_state().get_board() for sub_node in node.get_children()
    ]



    new_state = node.get_state().get_next_state_with_random_choice()

    # Check until get the new state which has the different action from others
    while if_board_in_lst(new_state.get_board(),tried_sub_node_states):
        new_state = node.get_state().get_next_state_with_random_choice()

    sub_node = Node()
    sub_node.set_state(new_state)
    node.add_child(sub_node)

    return sub_node

def best_child(node, is_exploration):
    """
    使用UCB算法，权衡exploration和exploitation后选择得分最高的子节点，注意如果是预测阶段直接选择
    """

    # TODO: Use the min float value
    best_score = -sys.maxsize
    best_sub_node = None
    # Travel all sub nodes to find the best one
    for sub_node in node.get_children():
        # Ignore exploration for inference
        if is_exploration:
            C = 1 / math.sqrt(2.0)
        else:
            C = 0.0

        # UCB = quality / times + C * sqrt(2 * ln(total_times) / times)
        left = sub_node.get_quality_value() / sub_node.get_visit_times()
        right = 2.0 * math.log(node.get_visit_times()) / sub_node.get_visit_times()
        score = left + C * math.sqrt(right)

        if score > best_score:
            best_sub_node = sub_node
            best_score = score
    return best_sub_node

def backup(node, reward):
    """
    蒙特卡洛树搜索的Backpropagation阶段，输入前面获取需要expand的节点和新的reward，向上传递更新值。
    """
    # Update until the root node
    while node != None:
        # Update the visit times
        node.visit_times_add_one()

        # Update the quality value
        node.quality_value_add_n(reward)

        # Change the node to the parent node
        node = node.parent

def monte_carlo_tree_search(node):
    """
    实现蒙特卡洛树搜索算法，传入一个根节点，在有限时间内根据之前已经探索过的树结构找到最佳的决策路径。
    
    蒙特卡洛树搜索包含四个步骤：
    1. Selection & Expansion（选择 & 拓展）: 使用 `tree_policy` 找到值得探索的子节点。
    2. Simulation（模拟）: 使用 `default_policy` 随机执行动作，计算 `reward`。
    3. Backpropagation（回溯）: 使用 `backup` 将 `reward` 更新到路径上的所有节点。
    4. Exploitation（利用）: 选择 `Q 值` 最大的子节点作为最优决策。
    """
    computation_budget = 10

    # Run as much as possible under the computation budget
    for i in range(computation_budget):
        # 1. Find the best node to expand
        expand_node = tree_policy(node)

        # 2. Random run to add node and get reward
        reward = default_policy(expand_node)

        # 3. Update all passing nodes with reward
        backup(expand_node, reward)

    # N. Get the best next node
    best_next_node = best_child(node, False)
    return best_next_node

def get_move(next_pieces):
    init_state = State(next_pieces)
    init_node = Node()
    init_node.set_state(init_state)
    result_node = monte_carlo_tree_search(init_node)
    return(result_node.get_state().get_cumulative_choices_dir()[-1],result_node.get_state().get_cumulative_choices_col()[-1])



# def run_by_random():
#     init_state = State([1,2,3,4,5])  # 創建初始遊戲狀態
#     while True:
#         init_state = init_state.get_next_state_with_random_choice()
#         init_state.show_board()
#         init_state.set_next_pieces(np.append(init_state.get_next_pieces(),random.randrange(0,7)))
#         time.sleep(0.5)

# def main():
#     # Create the initialized state and initialized node
#     init_state = State([1,2,3,4,5])  # 創建初始遊戲狀態
#     init_node = Node()  # 創建初始節點
#     init_node.set_state(init_state)  # 將初始狀態賦予節點
#     current_node = init_node  # 設定當前節點

#     # Set the rounds to play
#     i = 0
#     for i in range(10):  
#         print("Play round: {}".format(i + 1))
#         # 執行 MCTS 來選擇下一個最佳節點
#         current_node = monte_carlo_tree_search(current_node)
#         current_node.get_state().show_board()
#         print(current_node.get_state().get_current_value())
#         current_node.get_state().set_next_pieces(np.append(current_node.get_state().get_next_pieces(),random.randrange(0,7)))
#         time.sleep(0.5)
#         i += 1


# main()

#OILJSZT -> 0123456
