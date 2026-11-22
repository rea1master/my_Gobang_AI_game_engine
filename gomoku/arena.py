"""
自对弈评测脚本
用法: python gomoku/arena.py [--games N] [--time TIME] [--depth DEPTH]

两个相同 AI 互相对弈，统计黑白胜率、平均耗时、节点数等。
"""

import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board import Board, BLACK, WHITE, EMPTY
from engine import GomokuAI


def self_play_game(ai_black, ai_white):
    """一局自对弈，返回 (winner_color, black_time, white_time, moves)"""
    board = Board()
    ai_black.reset()
    ai_white.reset()

    b_total = 0.0
    w_total = 0.0
    moves = 0

    while True:
        t0 = time.time()
        r, c = ai_black.decide(board) if board.side == BLACK else ai_white.decide(board)
        elapsed = time.time() - t0

        if board.side == BLACK:
            b_total += elapsed
        else:
            w_total += elapsed

        board.make_move(r, c)
        moves += 1

        winner = board.check_win()
        if winner != EMPTY:
            return (winner, b_total, w_total, moves)
        if board.is_full():
            return (EMPTY, b_total, w_total, moves)


def run_arena(num_games=20, time_limit=1.0, max_depth=10):
    """运行多局自对弈并输出统计"""
    print(f"=== Self-play Arena ===")
    print(f"Games: {num_games}  |  Time limit: {time_limit}s/hand  |  Max depth: {max_depth}")
    print()

    ai_b = GomokuAI(time_limit=time_limit, max_depth=max_depth)
    ai_w = GomokuAI(time_limit=time_limit, max_depth=max_depth)

    black_wins = 0
    white_wins = 0
    draws = 0
    total_moves = 0
    total_b_time = 0.0
    total_w_time = 0.0

    for g in range(num_games):
        winner, bt, wt, mv = self_play_game(ai_b, ai_w)
        if winner == BLACK:
            black_wins += 1
        elif winner == WHITE:
            white_wins += 1
        else:
            draws += 1
        total_moves += mv
        total_b_time += bt
        total_w_time += wt

        result = 'BLACK' if winner == BLACK else ('WHITE' if winner == WHITE else 'DRAW')
        print(f"  Game {g+1:3d}: {result:6s}  |  moves={mv:3d}  "
              f"|  B_time={bt*1000:.0f}ms  W_time={wt*1000:.0f}ms")

    print()
    print("-" * 50)
    print(f"Results ({num_games} games):")
    print(f"  BLACK wins : {black_wins:3d}  ({100*black_wins/num_games:.1f}%)")
    print(f"  WHITE wins : {white_wins:3d}  ({100*white_wins/num_games:.1f}%)")
    print(f"  Draws      : {draws:3d}  ({100*draws/num_games:.1f}%)")
    print(f"  Avg moves  : {total_moves/num_games:.1f}")
    print(f"  Avg B time : {total_b_time/num_games*1000:.0f} ms/hand")
    print(f"  Avg W time : {total_w_time/num_games*1000:.0f} ms/hand")
    print("-" * 50)


if __name__ == '__main__':
    n = 20; tl = 1.0; md = 10
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--games' and i + 1 < len(args):
            n = int(args[i + 1]); i += 2
        elif args[i] == '--time' and i + 1 < len(args):
            tl = float(args[i + 1]); i += 2
        elif args[i] == '--depth' and i + 1 < len(args):
            md = int(args[i + 1]); i += 2
        else:
            i += 1
    run_arena(n, tl, md)
