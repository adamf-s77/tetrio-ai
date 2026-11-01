
import sys
import math
import random
import numpy as np

AVAILABLE_CHOICES = [1, -1, 2, -2]
AVAILABLE_CHOICE_NUMBER = len(AVAILABLE_CHOICES)
MAX_ROUND_NUMBER = 10

class State(object):
    """
    蒙特卡羅樹搜索的游戏状态，记录在某一个Node节点下的状态数据，包含当前的游戏得分、当前的游戏round数等。
    需要实现判断当前状态是否达到游戏结束状态，支持从Action集合中随机取出操作。
    """

    def __init__(self):
        self.current_value = 0.0
        # For the first root node, the index is 0 and the game should start from 1
        self.current_round_index = 0
        self.cumulative_choices = []

    def get_current_value(self):
        return self.current_value

    def set_current_value(self, value):
        self.current_value = value

    def get_current_round_index(self):
        return self.current_round_index

    def set_current_round_index(self, turn):
        self.current_round_index = turn

    def get_cumulative_choices(self):
        return self.cumulative_choices

    def set_cumulative_choices(self, choices):
        self.cumulative_choices = choices

    def is_terminal(self):
        # The round index starts from 1 to max round number
        return self.current_round_index == MAX_ROUND_NUMBER

    def compute_reward(self):
        return -abs(1 - self.current_value)

    def get_next_state_with_random_choice(self):
        random_choice = random.choice([choice for choice in AVAILABLE_CHOICES])
        next_state = State()
        next_state.set_current_value(self.current_value + random_choice)
        next_state.set_current_round_index(self.current_round_index + 1)
        next_state.set_cumulative_choices(self.cumulative_choices + [random_choice])
        return next_state

    def __repr__(self):
        return "State: {}, value: {}, round: {}, choices: {}".format(
            hash(self), self.current_value, self.current_round_index, self.cumulative_choices
        )

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
        return len(self.children) == AVAILABLE_CHOICE_NUMBER

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
    
    final_state_reward = current_state.compute_reward()
    return final_state_reward

def expand(node):
    """
    输入一个节点，在该节点上拓展一个新的节点，使用random方法执行Action，返回新增的节点。注意，需要
    """

    tried_sub_node_states = [
        sub_node.get_state() for sub_node in node.get_children()
    ]

    print(tried_sub_node_states)

    new_state = node.get_state().get_next_state_with_random_choice()
    # Check until get the new state which has the different action from others
    while new_state in tried_sub_node_states:
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

def main():
    # Create the initialized state and initialized node
    init_state = State()  # 創建初始遊戲狀態
    init_node = Node()  # 創建初始節點
    init_node.set_state(init_state)  # 將初始狀態賦予節點
    current_node = init_node  # 設定當前節點

    # Set the rounds to play
    for i in range(10):  # 進行 10 回合的 MCTS 搜索
        print("Play round: {}".format(i + 1))
        
        # 執行 MCTS 來選擇下一個最佳節點
        current_node = monte_carlo_tree_search(current_node)
        
        print("Choose node: {}".format(current_node))

if __name__ == "__main__":
    main()
