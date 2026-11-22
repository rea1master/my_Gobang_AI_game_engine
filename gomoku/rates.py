"""
难度胜率标定脚本

用「普通人」代理对手分别对打三档 AI，统计人类胜率。
用法: python gomoku/rates.py [--games N] [--level normal|advanced|impossible|all]
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board import Board, BLACK, WHITE, EMPTY
from engine import GomokuAI, LEVELS, LEVEL_KEYS
from proxy import HumanProxy


def play_one(level, human_black=True, slip=0.20, seed=None):
    """一局：人 vs AI，返回 'human' / 'ai' / 'draw'"""
    board = Board()
    ai = GomokuAI(level=level, rng_seed=seed)
    ai.reset()
    human = HumanProxy(slip=slip, seed=(seed or 0) + 7)

    human_color = BLACK if human_black else WHITE
    ai_color = WHITE if human_black else BLACK

    for _ in range(225):
        if board.side == human_color:
            r, c = human.decide(board)
        else:
            r, c = ai.decide(board)
        if board.grid[r][c] != EMPTY:
            # 非法着法保护
            for rr in range(15):
                for cc in range(15):
                    if board.grid[rr][cc] == EMPTY:
                        r, c = rr, cc
                        break
        board.make_move(r, c)
        w = board.check_win()
        if w != EMPTY:
            return 'human' if w == human_color else 'ai'
        if board.is_full():
            return 'draw'
    return 'draw'


def run_level(level, games=20, slip=0.20):
    humans = 0
    ais = 0
    draws = 0
    t0 = time.time()
    for g in range(games):
        # 交替先后手，避免先手优势干扰结论
        human_black = (g % 2 == 0)
        res = play_one(level, human_black=human_black, slip=slip, seed=g * 13 + 1)
        if res == 'human':
            humans += 1
        elif res == 'ai':
            ais += 1
        else:
            draws += 1
    dt = time.time() - t0
    n = games
    print(f"[{LEVELS[level]['name']:>4}] 局数={n:3d}  人类胜={humans:3d} ({100*humans/n:5.1f}%)  "
          f"AI胜={ais:3d} ({100*ais/n:5.1f}%)  平={draws}  用时={dt:.1f}s")
    return humans / n


if __name__ == '__main__':
    games = 20
    level_arg = 'all'
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--games' and i + 1 < len(args):
            games = int(args[i + 1]); i += 2
        elif args[i] == '--level' and i + 1 < len(args):
            level_arg = args[i + 1]; i += 2
        else:
            i += 1

    levels = LEVEL_KEYS if level_arg == 'all' else [level_arg]
    print(f"=== 难度胜率标定（对手=普通人代理，slip=0.20）===")
    for lv in levels:
        run_level(lv, games)
