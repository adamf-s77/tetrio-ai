"""
mcts_agent.py
MCTS 決策代理模組，支援 UCB1 與 CLT-UCB。
"""

import sys
import math
import random
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.engine import (
    PIECE_ACTIONS,
    PIECE_SHAPE,
    AVAILABLE_CHOICES,
    AVAILABLE_CHOICES_NUMBER,
    get_board_features,
    compute_heuristics,
    simulate_placement,
    State,
)
from src.cnn_evaluator import CNNPolicyEvaluator


def norm_quantile(n):
    """常態分佈分位數近似計算"""
    if n <= 1:
        return 1.0
    alpha = max(1e-5, min(0.9999, 1.0 - 1.0 / n))
    try:
        q = 10.0 * math.log(1.0 - math.log(-math.log(alpha) / math.log(2.0)) / math.log(22.0)) / math.log(41.0)
        return max(0.5, min(q, 3.5))
    except Exception:
        return 1.5


class MCTSNode:
    """MCTS 樹節點"""

    def __init__(self, state=None, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action  # (direction, col)
        self.children = []
        self.visit_times = 0
        self.quality_value = 0.0

        # CLT-UCB 變異數
        self.variance = 100.0
        self.prior_value = 0.0
        self.prior_variance = 100.0

        self.untried_actions = []
        if state and not state.is_terminal():
            self.untried_actions = list(PIECE_ACTIONS[state.now_piece])
            random.shuffle(self.untried_actions)

    def is_all_expand(self):
        return len(self.untried_actions) == 0

    def add_child(self, child_node):
        child_node.parent = self
        self.children.append(child_node)

    def get_move(self):
        if self.action is not None:
            return self.action[0], self.action[1]
        if self.state and self.state.parent_dir_and_col:
            return self.state.parent_dir_and_col[0], self.state.parent_dir_and_col[1]
        return 0, 0


class MCTSAgent:
    """MCTS 決策代理類別"""

    def __init__(
        self,
        mode='cnn_mcts',
        cnn_evaluator=None,
        budget=None,
        height_punishment_degree=1.0,
        backup_punishment_degree=0.95,
        clt_c=0.08,
    ):
        if mode in ('cnn', 'cnn_mcts'):
            self.mode = 'cnn_mcts'
        else:
            self.mode = 'pure_mcts'

        self.budget = budget
        self.height_punishment_degree = height_punishment_degree
        self.backup_punishment_degree = backup_punishment_degree
        self.clt_c = clt_c

        if self.mode == 'cnn_mcts':
            self.evaluator = cnn_evaluator or CNNPolicyEvaluator()
        else:
            self.evaluator = None

    def select_child(self, node, is_exploration=True):
        best_score = -float('inf')
        best_child = None
        log_n = math.log(max(1, node.visit_times))
        total_n = max(1, node.visit_times)

        for child in node.children:
            if child.visit_times == 0:
                return child

            q_mean = child.quality_value / child.visit_times

            if is_exploration:
                if self.mode == 'cnn_mcts':
                    z = norm_quantile(total_n)
                    sigma = math.sqrt(max(1e-4, child.variance))
                    score = q_mean + self.clt_c * z * (sigma / math.sqrt(child.visit_times))
                else:
                    score = q_mean + 10.0 * math.sqrt(2.0 * log_n / child.visit_times)
            else:
                score = q_mean

            if score > best_score:
                best_score = score
                best_child = child

        return best_child

    def tree_policy(self, node):
        curr = node
        while not curr.state.is_terminal():
            if not curr.is_all_expand():
                direction, col = curr.untried_actions.pop()
                next_state = curr.state.get_next_state(direction, col)
                child_node = MCTSNode(next_state, parent=curr, action=(direction, col))
                curr.add_child(child_node)
                return child_node
            else:
                sub_node = self.select_child(curr, is_exploration=True)
                if sub_node is None:
                    return curr
                curr = sub_node
        return curr

    def rollout(self, node):
        state = node.state
        if state.is_terminal():
            return -100000.0, 1.0

        step1_lines = state.step_clear_lines
        is_pure = (self.mode == 'pure_mcts')

        best_next = -float('inf')
        if state.now_piece is not None:
            for a in PIECE_ACTIONS[state.now_piece]:
                nb, cl = simulate_placement(state.board, state.now_piece, a[0], a[1])
                sc = compute_heuristics(
                    nb,
                    lines_cleared=step1_lines + (cl if cl != -1 else 0),
                    is_game_over=(cl == -1),
                    height_punishment_degree=self.height_punishment_degree,
                    is_pure_mcts=is_pure,
                )
                if sc > best_next:
                    best_next = sc
        else:
            best_next = compute_heuristics(
                state.board,
                lines_cleared=step1_lines,
                is_game_over=False,
                height_punishment_degree=self.height_punishment_degree,
                is_pure_mcts=is_pure,
            )

        if self.mode == 'cnn_mcts' and self.evaluator is not None:
            v_cnn, var_cnn = self.evaluator.evaluate(state.board)
            node.variance = var_cnn
            total_value = (v_cnn * 0.1) + best_next
            return total_value, var_cnn
        else:
            return best_next, 100.0

    def backup(self, node, value, variance):
        curr = node
        r = value
        while curr is not None:
            curr.visit_times += 1
            curr.quality_value += r

            if curr.visit_times > 1:
                mean = curr.quality_value / curr.visit_times
                delta = r - mean
                curr.variance = max(1e-4, curr.variance * 0.9 + (delta ** 2) * 0.1)
            else:
                curr.variance = max(1e-4, variance)

            r *= self.backup_punishment_degree
            curr = curr.parent

    def search(self, root_state):
        if root_state is None or root_state.now_piece is None:
            return None

        root_node = MCTSNode(root_state)
        action_count = len(PIECE_ACTIONS[root_state.now_piece])

        if self.budget is None or self.budget <= 0:
            budget = action_count
        else:
            budget = max(self.budget, action_count)

        for _ in range(budget):
            leaf = self.tree_policy(root_node)
            if leaf is None:
                break
            val, var = self.rollout(leaf)
            self.backup(leaf, val, var)

        best_child = self.select_child(root_node, is_exploration=False)
        return best_child
