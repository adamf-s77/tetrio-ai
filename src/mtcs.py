import sys,math,random,numpy as np,time
import matplotlib.pyplot as plt
import matplotlib
import os

matplotlib.use('Agg')



#OILJSZT -> 0123456
PIECE_SHAPE = [
    [[3,3],[3,3],[3,3],[3,3]],
    [[15],[1,1,1,1],[15],[1,1,1,1]],
    [[7,1],[1,1,3],[4,7],[3,2,2]],
    [[7,4],[3,1,1],[1,7],[2,2,3]],
    [[6,3],[1,3,2],[6,3],[1,3,2]],
    [[3,6],[2,3,1],[3,6],[2,3,1]],
    [[7,2],[1,3,1],[2,7],[2,3,2]]
]



AVAILABLE_CHOICES = [
    [9,9,9,9],
    [7,10,7,10],
    [8,9,8,9],
    [8,9,8,9],
    [8,9,8,9],
    [8,9,8,9],
    [8,9,8,9],
]

AVAILABLE_CHOICES_NUMBER = [9,17,34,34,17,17,34]

class State(object):
    """
    蒙特卡羅樹搜索的游戏状态，记录在某一个Node节点下的状态数据，包含当前的游戏得分、当前的游戏round数等。
    需要实现判断当前状态是否达到游戏结束状态，支持从Action集合中随机取出操作。
    """

    def __init__(self,next_pieces):
        self.now_piece = None
        self.next_pieces = []
        self.parent_dir_and_col = []
        self.board = np.zeros(20,dtype = int)
        self.current_score = 0
        self.height = 0
        self.cumulative_choices_dir = np.array([],dtype = int)
        self.cumulative_choices_col = np.array([],dtype = int)
        if(len(next_pieces) != 0):
            self.current_value = 0
            self.board = np.zeros(20,dtype = int)
            self.now_piece = next_pieces[0] 
            self.next_pieces = np.delete(next_pieces,0) 
            self.parent_dir_and_col = []

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
        self.now_piece = next_pieces[0]
        self.next_pieces = np.delete(next_pieces,0)

    def is_terminal(self):
       return self.now_piece == None

    def compute_reward(self):
        return self.current_value
    
    def place_piece(self,dir,col):
        piece_shape = PIECE_SHAPE[self.now_piece][dir].copy()
        height = len(piece_shape)

        #放哪個位置
        for i in range(height): 
            piece_shape[i] = piece_shape[i] << (AVAILABLE_CHOICES[self.now_piece][dir] - col - 1)


        #判斷下界
        j = 19-height
        # while self.board[j] & piece_shape[0] == 0 and j >= 0: j -= 1
        overlap = 0
        while overlap == 0:
            for i in range(len(piece_shape)):
                if self.board[j+i] & piece_shape[i] != 0 or j < 0: overlap = 1
            j -= 1  
        j += 2
        new_board = self.board.copy()

        clear_lines = 0
        for i in range(height):
            if(i+j == 19): return new_board,-1
            new_board[i+j] = new_board[i+j] | piece_shape[i]
            if(new_board[i+j] == 1023):
                clear_lines += 1
                new_board = np.delete(new_board,i+j)
                new_board = np.append(new_board,0)
                j -= 1
        return new_board,clear_lines



    def get_next_state_with_random_choice(self,dir = None,col = None):
        #get choice
        if(dir == None): dir = random.randrange(0,4)  #top left down right -> 0123
        if(col == None): col = random.randrange(0,AVAILABLE_CHOICES[self.now_piece][dir])

        new_board,value = self.place_piece(dir,col)
        
        # if value > 0: 
        #     print("success!")
        #     time.sleep(3)

        if(value == -1):
            next_state = State(np.array([]))
            next_state.set_current_value(self.get_current_value() + value + 1)
            next_state.parent_dir_and_col = [dir,col]
            next_state.current_score = self.current_score - 1
            next_state.set_cumulative_choices_dir(dir)
            next_state.set_cumulative_choices_col(col)
            return next_state
        next_state = State(self.next_pieces)
        next_state.set_board(new_board)
        next_state.current_score = self.current_score
        if(value > 0):
            next_state.current_score += (value*2-1)*100 if value != 4 else (value*2)*100
        next_state.current_score += 30
        for i in range(19,-1,-1):
            if(next_state.board[i] != 0):
                next_state.height = i
                break
        next_state.set_current_value(self.get_current_value() + value)
        next_state.parent_dir_and_col = [dir,col]
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
        return len(self.children) >= AVAILABLE_CHOICES_NUMBER[self.state.now_piece]

    def add_child(self, sub_node):
        sub_node.set_parent(self)
        self.children.append(sub_node)

    def print_children_quality_value(self):
        for i in self.children:
            print(i.quality_value,end = ' ')
        print()

    def get_move(self):
        return self.state.get_cumulative_choices_dir()[-1],self.state.get_cumulative_choices_col()[-1]


def tree_policy(node):
    """
    蒙特卡罗树搜索的Selection和Expansion阶段，传入当前需要开始搜索的节点（例如根节点）。
    基本策略是先找当前未选择过的子节点，如果是多个则随机选。如果都被选择过就按权衡过
    """
    # print("tree policy times:",i)
    # print("now piece:",node.get_state().now_piece)

    # Check if the current node is the leaf node
    while node.get_state().is_terminal() == False:

        # print("expand?")
        if node.is_all_expand():
            # print("y")
            node = best_child(node, True)
        else:
            # print("n")
            # Return the new sub node
            sub_node = expand(node)
            return sub_node
    # Return the leaf node
    # print("leave tree policy")
    return node


def if_board_in_lst(dir_and_col,lst):

    for i in lst:
        if dir_and_col[0] == i[0] and dir_and_col[1] == i[1]:
            return True
    return False

def best_child(node, is_exploration):
    """
    使用UCB算法，权衡exploration和exploitation后选择得分最高的子节点，注意如果是预测阶段直接选择
    """
    # print("compute best child")
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

        # print("value",sub_node.get_quality_value(),"visit times",sub_node.get_visit_times())
        # UCB = quality / times + C * sqrt(2 * ln(total_times) / times)
        left = sub_node.get_quality_value() / sub_node.get_visit_times()
        right = 100 * math.log(node.get_visit_times()) / sub_node.get_visit_times()
        score = left + C * math.sqrt(right)

        if score > best_score:
            best_sub_node = sub_node
            best_score = score
    return best_sub_node


def expand(node):
    """
    输入一个节点，在该节点上拓展一个新的节点，使用random方法执行Action，返回新增的节点。注意，需要
    """
    # print("expand in")

    tried_sub_node_states = [
        sub_node.get_state().parent_dir_and_col for sub_node in node.get_children()
    ]
    # print(len(node.get_children()))
    # print(node.get_state().now_piece)
    # print(len(tried_sub_node_states))

    # print("lst builded")
    new_state = node.get_state().get_next_state_with_random_choice()
    # new_state.show_board()
    # Check until get the new state which has the different action from others
    while if_board_in_lst(new_state.parent_dir_and_col,tried_sub_node_states):
        new_state = node.get_state().get_next_state_with_random_choice()
    # print("chosen")

    sub_node = Node()
    if len(new_state.next_pieces) > 0: new_state.next_pieces = np.append(new_state.get_next_pieces(),random.randrange(0,7))
    sub_node.set_state(new_state)
    node.add_child(sub_node)
    # print("expand out")
    # print(sub_node.get_state().now_piece)
    # print(sub_node.get_state().next_pieces)
    return sub_node 

def default_policy(node,i = 1):
    """
    蒙特卡罗树搜索的Simulation阶段，输入一个需要expand的节点，随机操作后创建新的节点。
    基本策略是随机选择Action。
    """
    # node.get_state().show_board()
    reward = node.get_state().current_score - node.get_parent().get_state().current_score
    if(reward > 3):
        reward *= 2
    # print(reward)
    return reward * 10/(node.get_state().height+1) 

def backup(node,reward):
    """
    蒙特卡洛树搜索的Backpropagation阶段，输入前面获取需要expand的节点和新的reward，向上传递更新值。
    """
    # Update until the root node
    while node != None:
        # Update the visit times
        node.visit_times_add_one()
        # Update the quality value
        node.quality_value_add_n(reward)
        reward *= 0.9

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
    # print("in monte carlo")
    computation_budget = 20000
    # Run as much as possible under the computation budget
    for i in range(computation_budget):

        # if(i%1000 == 0):
        #     print("simulations:",i)
        # 1. Find the best node to expand
        # print("tree_policy")
        expand_node = tree_policy(node)
        # 2. Random run to add node and get reward
        # print("default_policy")
        reward = default_policy(expand_node,i)
        # print(reward)
        # 3. Update all passing nodes with reward
        # time.sleep(0.5)
        backup(expand_node,reward)

    # N. Get the best next node
    node.print_children_quality_value()
    best_next_node = best_child(node, False)
    # print("out monte carlo")
    return best_next_node

def save_state_image(state, frame_idx, out_dir='frames'):
    os.makedirs(out_dir, exist_ok=True)
    plt.imshow(state, cmap='gray', interpolation='nearest')
    plt.axis('off')
    plt.savefig(f"{out_dir}/frame_{frame_idx:04d}.png", bbox_inches='tight', pad_inches=0)
    plt.close()

def main():
    init_state = State([random.randrange(0,7) for i in range(5)])
    init_node = Node()
    init_node.set_state(init_state)
    current_node = init_node
    tmp = 100
    for i in range(2000):  
        print("times: ", i)
        current_node = monte_carlo_tree_search(current_node)
        current_node.get_state().show_board()
        print("score: ",int(current_node.get_state().current_score))
        print("clear lines: ", current_node.get_state().get_current_value(), end='\n\n')
        if(tmp < 400 and current_node.get_state().get_current_value() >= tmp):
            tmp += 100
            while(1):
                a = input()
                if(a == "ok"): break
        save_state_image(current_node.get_state().get_board_matrix(), i)


class Last_Node:
    def __init__(self):
        self.current_node = Node()

    def get_move(self,next_pieces,dir = None,col = None):
        if(self.current_node.get_state() == None):
            state = State(next_pieces)
            self.current_node.set_state(state)
        else:
            self.current_node.get_state().set_next_pieces(next_pieces)
        self.current_node.children = []
        self.current_node = monte_carlo_tree_search(self.current_node)
        self.current_node.get_state().show_board()
        return self.current_node.get_move()

# main()


#next_pieces 延伸方塊要修改

# node = Last_Node()

# a,b = node.get_move([1,2,3,4,5])
# print(a,b)
# c,d = node.get_move([2,3,4,5,6])
# print(c,d)


