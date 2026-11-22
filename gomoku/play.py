"""
人机对弈控制台入口 —— 在 VSCode 里打开本文件，直接按右上角 ▶ 运行键即可开玩。
不带任何命令行参数也能跑（默认每手 1 秒、深度 8）。

棋盘显示说明：
    A~O 是列号(0~14)，左侧 0~14 是行号
    X = 你(黑棋)   O = AI(白棋)   . = 空位
输入格式：
    A7      -> 第7行A列（字母=列，数字=行）
    7 6     -> 第7行第6列
    quit    -> 退出
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board import Board, BLACK, WHITE, EMPTY, SIZE
from engine import GomokuAI


def parse_input(line):
    """解析用户输入 'A7' / 'a7' / '7 6' 等格式，返回 (row, col) 或 None"""
    line = line.strip().upper()
    # 字母+数字格式（如 A7）
    if len(line) >= 2 and line[0].isalpha():
        c = ord(line[0]) - ord('A')
        try:
            r = int(line[1:])
        except ValueError:
            return None
        if 0 <= r < SIZE and 0 <= c < SIZE:
            return (r, c)
    # 空格分隔格式（如 "7 6"）
    parts = line.split()
    if len(parts) == 2:
        try:
            r, c = int(parts[0]), int(parts[1])
            if 0 <= r < SIZE and 0 <= c < SIZE:
                return (r, c)
        except ValueError:
            pass
    return None


def human_move(board):
    """人类玩家落子，循环直到合法"""
    while True:
        try:
            line = input(f"  {'BLACK(X)' if board.side == BLACK else 'WHITE(O)'} move (e.g. A7 or '7 6'): ")
        except EOFError:
            print("\n  [!] 输入流结束（调试控制台不支持键盘输入）。")
            print("  [!] 请在 VSCode 的【终端】里运行: python gomoku/play.py")
            raise SystemExit
        if line.lower() in ('quit', 'q', 'exit'):
            raise KeyboardInterrupt
        rc = parse_input(line)
        if rc is None:
            print("  Invalid input. Try e.g. 'A7' or '7 6'.")
            continue
        r, c = rc
        if board.grid[r][c] != EMPTY:
            print(f"  ({r},{c}) is occupied. Choose another.")
            continue
        return (r, c)


def play_game(level='advanced', time_limit=None, max_depth=None):
    """一局完整的人机对弈"""
    board = Board()
    ai = GomokuAI(level=level, time_limit=time_limit, max_depth=max_depth)
    ai.reset()

    print("=" * 50)
    print("  GOMOKU — Human vs AI")
    print(f"  Difficulty: {ai.level_name}  (depth={ai.max_depth}, time={ai.time_limit}s)")
    print("  You are BLACK (X), AI is WHITE (O)")
    print("  Enter moves like 'A7' or '7 6'. Type 'quit' to exit.")
    print("=" * 50)
    print()
    print(board)
    print()

    turn = 0
    while True:
        side_name = 'BLACK(X)' if board.side == BLACK else 'WHITE(O)'

        if board.side == BLACK:
            # 人类走棋
            try:
                r, c = human_move(board)
            except KeyboardInterrupt:
                print("\n  Game quit by user.")
                return
        else:
            # AI 走棋
            print(f"  {side_name} thinking... ", end="", flush=True)
            r, c = ai.decide(board)
            print(ai.stats_summary())

        board.make_move(r, c)
        turn += 1

        winner = board.check_win()
        if winner != EMPTY:
            print()
            print(board)
            name = 'BLACK(X)' if winner == BLACK else 'WHITE(O)'
            print(f"\n  *** {name} wins in {turn} moves! ***")
            return

        if board.is_full():
            print()
            print(board)
            print("\n  *** Draw! ***")
            return

        print()
        print(board)
        print()


if __name__ == '__main__':
    # ---- 默认配置：VSCode 直接按运行键就用这组参数 ----
    LEVEL = 'advanced'   # 难度：normal / advanced / impossible
    TIME_LIMIT = None    # 不填则用难度自带时限
    MAX_DEPTH = None     # 不填则用难度自带深度

    # 命令行参数（都可省略）
    #   --level normal|advanced|impossible
    #   --time 1.0     --depth 8
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--level' and i + 1 < len(args):
            LEVEL = args[i + 1]; i += 2
        elif args[i] == '--time' and i + 1 < len(args):
            TIME_LIMIT = float(args[i + 1]); i += 2
        elif args[i] == '--depth' and i + 1 < len(args):
            MAX_DEPTH = int(args[i + 1]); i += 2
        else:
            i += 1

    play_game(LEVEL, TIME_LIMIT, MAX_DEPTH)
