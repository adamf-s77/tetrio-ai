"""
run_demo.py
俄羅斯方塊 MCTS AI 執行與測試腳本
"""

import sys
import os
import time
import argparse
import random
import numpy as np

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from src.engine import (
    State,
    PIECE_ACTIONS,
    get_board_features,
    compute_heuristics
)
from src.mcts_agent import MCTSAgent, MCTSNode
from src.mcts import monte_carlo_tree_search, Node

PIECE_NAMES = ['O', 'I', 'L', 'J', 'S', 'Z', 'T']

COLORS = {
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
    'DIM': '\033[2m',
    'CYAN': '\033[96m',
    'YELLOW': '\033[93m',
    'MAGENTA': '\033[95m',
    'BLUE': '\033[94m',
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'WHITE': '\033[97m',
    'GRAY': '\033[90m',
}

PIECE_COLORS = {
    0: '\033[93m',
    1: '\033[96m',
    2: '\033[33m',
    3: '\033[94m',
    4: '\033[92m',
    5: '\033[91m',
    6: '\033[95m',
}


def render_board(
    board,
    step,
    lines_cleared,
    now_piece,
    next_pieces,
    latency_ms,
    fps,
    target_lines,
    mode="pure_mcts",
    variance=None,
    game_score=0,
    clears_count=None,
    combo=0
):
    """繪製盤面與即時狀態"""
    heights, holes, hole_depth, bumpiness, aggregate_height, max_height, wells = get_board_features(board)
    clears_count = clears_count or {1: 0, 2: 0, 3: 0, 4: 0}

    progress = min(100.0, (lines_cleared / target_lines) * 100.0)
    bar_width = 16
    filled_bars = int(bar_width * (progress / 100.0))
    progress_bar = f"[{'#' * filled_bars}{'.' * (bar_width - filled_bars)}]"

    mode_title = "CNN-MCTS" if mode == "cnn_mcts" else "Pure MCTS"

    lines = []
    lines.append(f"{COLORS['BOLD']}============================================================{COLORS['RESET']}")
    lines.append(f"{COLORS['BOLD']}  Tetris AI Demo [{COLORS['YELLOW']}{mode_title}{COLORS['RESET']}{COLORS['BOLD']}]{COLORS['RESET']}")
    lines.append(f"============================================================")
    lines.append(f" ┌────────────────────┐  即時狀態:")

    for r in range(19, -1, -1):
        row_bits = board[r]
        row_cells = []
        for c in range(10):
            if row_bits & (1 << (9 - c)):
                row_cells.append(f"{COLORS['GREEN']}██{COLORS['RESET']}")
            else:
                row_cells.append(f"{COLORS['GRAY']}··{COLORS['RESET']}")
        grid_row = "".join(row_cells)

        info = ""
        if r == 19:
            p_name = PIECE_NAMES[now_piece] if now_piece is not None else "-"
            p_color = PIECE_COLORS.get(now_piece, COLORS['WHITE'])
            info = f"當前方塊: {p_color}[{p_name}]{COLORS['RESET']}"
        elif r == 18:
            n1 = PIECE_NAMES[next_pieces[0]] if len(next_pieces) > 0 else "-"
            n2 = PIECE_NAMES[next_pieces[1]] if len(next_pieces) > 1 else "-"
            n3 = PIECE_NAMES[next_pieces[2]] if len(next_pieces) > 2 else "-"
            info = f"後續隊列: [{n1}] [{n2}] [{n3}]"
        elif r == 17:
            info = f"步數: {step}"
        elif r == 16:
            info = f"消行: {lines_cleared} / {target_lines}"
        elif r == 15:
            info = f"進度: {progress_bar} {progress:5.1f}%"
        elif r == 14:
            combo_str = f" (Combo: {combo})" if combo > 1 else ""
            info = f"得分: {game_score:,}{combo_str}"
        elif r == 13:
            c1, c2, c3, c4 = clears_count.get(1, 0), clears_count.get(2, 0), clears_count.get(3, 0), clears_count.get(4, 0)
            info = f"消行統計: 1行:{c1} | 2行:{c2} | 3行:{c3} | 4行:{c4}"
        elif r == 12:
            info = f"延遲: {latency_ms:5.1f} ms"
        elif r == 11:
            info = f"FPS: {fps:5.1f}"
        elif r == 10 and variance is not None:
            info = f"CNN Var: {variance:6.2f}"
        elif r == 9:
            info = "盤面指標:"
        elif r == 8:
            hole_color = COLORS['RED'] if holes > 0 else COLORS['RESET']
            info = f"空洞 (Holes)    : {hole_color}{holes}{COLORS['RESET']} (深度: {hole_depth})"
        elif r == 7:
            info = f"凹凸 (Bumpiness): {bumpiness}"
        elif r == 6:
            h_color = COLORS['RED'] if max_height > 12 else COLORS['RESET']
            info = f"最大高度 (Max H): {h_color}{max_height}{COLORS['RESET']} / 20"
        elif r == 5:
            info = f"總高度 (Agg H)  : {aggregate_height}"
        elif r == 4:
            info = f"井深 (Wells)    : {wells}"

        lines.append(f" │{grid_row}│  {info}")

    lines.append(f" └────────────────────┘")
    lines.append(f"------------------------------------------------------------")
    return "\n".join(lines)


def run_tetris_demo(mode="pure_mcts", target_lines=300, delay=0.03, budget=0, seed=None, silent=False):
    """執行單次展示"""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    if not silent:
        print("\033[2J\033[H", end="")
        print(f"啟動 Tetris AI (模式: {mode}, 目標消行: {target_lines})...")
        time.sleep(0.2)

    if mode == "cnn_mcts":
        agent = MCTSAgent(mode='cnn_mcts', budget=budget)
    else:
        agent = MCTSAgent(mode='pure_mcts', budget=budget)

    queue = [random.randrange(0, 7) for _ in range(6)]
    now_piece = queue.pop(0)
    queue.append(random.randrange(0, 7))

    root_state = State([now_piece] + queue)
    curr_state = root_state

    step = 0
    total_cleared = 0
    start_total_time = time.time()
    latencies = []
    last_variance = None

    try:
        while total_cleared < target_lines:
            step += 1
            step_start = time.time()

            best_node = agent.search(curr_state)

            step_time = time.time() - step_start
            latencies.append(step_time)
            latency_ms = step_time * 1000.0
            recent_fps = 1.0 / step_time if step_time > 0 else 99.0

            if best_node is None or best_node.state.is_terminal():
                if not silent:
                    print("\033[H", end="")
                    print(render_board(
                        curr_state.board, step, total_cleared,
                        curr_state.now_piece, curr_state.next_pieces,
                        latency_ms, recent_fps, target_lines,
                        mode=mode, variance=last_variance,
                        game_score=getattr(curr_state, 'game_score', 0),
                        clears_count=getattr(curr_state, 'clears_count', None),
                        combo=getattr(curr_state, 'combo', 0)
                    ))
                    print(f"\n遊戲結束於第 {step} 步，累計消行: {total_cleared} 行，得分: {getattr(curr_state, 'game_score', 0):,} 分。")
                return {
                    "success": False,
                    "step": step,
                    "lines": total_cleared,
                    "score": getattr(curr_state, 'game_score', 0),
                    "time": time.time() - start_total_time,
                    "fps": recent_fps,
                    "clears": getattr(curr_state, 'clears_count', {})
                }

            total_cleared = best_node.state.current_value
            curr_state = best_node.state
            if mode == "cnn_mcts":
                last_variance = getattr(best_node, 'variance', None)

            if not silent and (delay > 0 or step % 5 == 0):
                print("\033[H", end="")
                print(render_board(
                    curr_state.board, step, total_cleared,
                    curr_state.now_piece, curr_state.next_pieces,
                    latency_ms, recent_fps, target_lines,
                    mode=mode, variance=last_variance,
                    game_score=getattr(curr_state, 'game_score', 0),
                    clears_count=getattr(curr_state, 'clears_count', None),
                    combo=getattr(curr_state, 'combo', 0)
                ))

            if delay > 0:
                time.sleep(delay)

        total_time = time.time() - start_total_time
        avg_fps = step / total_time if total_time > 0 else 0
        avg_latency_ms = (sum(latencies) / len(latencies)) * 1000.0 if latencies else 0
        final_score = getattr(curr_state, 'game_score', 0)
        final_clears = getattr(curr_state, 'clears_count', {})

        if not silent:
            print("\033[H", end="")
            print(render_board(
                curr_state.board, step, total_cleared,
                curr_state.now_piece, curr_state.next_pieces,
                0.0, avg_fps, target_lines,
                mode=mode, variance=last_variance,
                game_score=final_score,
                clears_count=final_clears,
                combo=getattr(curr_state, 'combo', 0)
            ))

            print(f"\n============================================================")
            print(f"完成！累計消行: {total_cleared} 行，總分: {final_score:,} 分，總耗時: {total_time:.2f} 秒 ({avg_fps:.1f} FPS)")
            c1, c2, c3, c4 = final_clears.get(1, 0), final_clears.get(2, 0), final_clears.get(3, 0), final_clears.get(4, 0)
            print(f"消行分佈: 1行: {c1} | 2行: {c2} | 3行: {c3} | 4行: {c4}")
            print(f"============================================================\n")

        return {
            "success": True,
            "step": step,
            "lines": total_cleared,
            "score": final_score,
            "time": total_time,
            "fps": avg_fps,
            "latency_ms": avg_latency_ms,
            "clears": final_clears
        }

    except KeyboardInterrupt:
        print(f"\n已中斷。當前消行: {total_cleared} 行，得分: {getattr(curr_state, 'game_score', 0):,} 分。\n")
        return {
            "success": False,
            "step": step,
            "lines": total_cleared,
            "score": getattr(curr_state, 'game_score', 0),
            "time": time.time() - start_total_time,
            "fps": 0,
            "clears": getattr(curr_state, 'clears_count', {})
        }


def run_benchmark(target_lines=100, seed=42):
    """執行 Pure MCTS 與 CNN-MCTS 雙引擎基準測試"""
    print(f"\n============================================================")
    print(f" 俄羅斯方塊雙引擎基準測試 (目標: 各消除 {target_lines} 行)")
    print(f"============================================================\n")

    print(">>> [1/2] 正在測試: Pure MCTS...")
    res1 = run_tetris_demo(mode="pure_mcts", target_lines=target_lines, delay=0.0, seed=seed)

    print("\n>>> [2/2] 正在測試: CNN-MCTS...")
    res2 = run_tetris_demo(mode="cnn_mcts", target_lines=target_lines, delay=0.0, seed=seed)

    s1, s2 = res1.get('score', 0), res2.get('score', 0)
    score_diff = ((s2 - s1) / s1 * 100.0) if s1 > 0 else 0
    c1_map = res1.get('clears', {})
    c2_map = res2.get('clears', {})

    print(f"\n======================== 基準測試結果對比 ========================")
    print(f" 項目                     Pure MCTS            CNN-MCTS")
    print(f" ------------------------------------------------------------------")
    print(f" 目標消行數               {target_lines} 行                 {target_lines} 行")
    print(f" 遊戲總得分               {s1:>8,} 分            {s2:>8,} 分  ({score_diff:+.1f}%)")
    print(f" 單行消除 (1行)           {c1_map.get(1, 0):>8} 次            {c2_map.get(1, 0):>8} 次")
    print(f" 雙行消除 (2行)           {c1_map.get(2, 0):>8} 次            {c2_map.get(2, 0):>8} 次")
    print(f" 三行消除 (3行)           {c1_map.get(3, 0):>8} 次            {c2_map.get(3, 0):>8} 次")
    print(f" 四行消除 (4行)           {c1_map.get(4, 0):>8} 次            {c2_map.get(4, 0):>8} 次")
    print(f" 決策幀率 (FPS)           {res1.get('fps', 0):>7.1f} FPS           {res2.get('fps', 0):>7.1f} FPS")
    print(f" 總耗時                   {res1.get('time', 0):>7.2f} 秒            {res2.get('time', 0):>7.2f} 秒")
    print(f" ------------------------------------------------------------------")
    print(f"==================================================================\n")


def main():
    env_budget = int(os.getenv("TETRIS_MCTS_BUDGET", "0"))
    env_target_lines = int(os.getenv("TETRIS_TARGET_LINES", "300"))

    parser = argparse.ArgumentParser(description="Tetris MCTS Demo Runner")
    parser.add_argument("--mode", type=str, default="cnn_mcts", choices=["cnn_mcts", "pure_mcts", "benchmark", "web"],
                        help="運行模式: cnn_mcts, pure_mcts, benchmark, web")
    parser.add_argument("--web", action="store_true",
                        help="啟動網頁實機連線 (等同 --mode web)")
    parser.add_argument("--target-lines", type=int, default=env_target_lines,
                        help=f"目標消除行數 (預設: {env_target_lines})")
    parser.add_argument("--speed", type=str, default="normal", choices=["slow", "normal", "fast", "instant"],
                        help="速度: slow, normal, fast, instant")
    parser.add_argument("--budget", type=int, default=env_budget,
                        help=f"MCTS 搜尋預算 (預設: {env_budget})")
    parser.add_argument("--seed", type=int, default=None,
                        help="隨機種子")

    args = parser.parse_args()

    if args.mode == "benchmark":
        run_benchmark(target_lines=args.target_lines, seed=args.seed or 42)
        return

    if args.web or args.mode == "web":
        print("啟動 TETR.IO 自動遊玩模組 (src/interface.py)...")
        try:
            from src.interface import tetrio_bot
            bot = tetrio_bot()
            bot.init()
        except Exception as e:
            print(f"啟動失敗: {e}")
        return

    speed_map = {
        "slow": 0.08,
        "normal": 0.03,
        "fast": 0.01,
        "instant": 0.0
    }
    delay = speed_map[args.speed]

    run_tetris_demo(
        mode=args.mode,
        target_lines=args.target_lines,
        delay=delay,
        budget=args.budget,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
