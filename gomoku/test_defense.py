"""
实战验证：让 AI 执白，对付"只会走活三/冲四"的脚本对手，
检查 AI 是否会被简单的活三连续进攻击败。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board, BLACK, WHITE, EMPTY, DIRS, SIZE
from engine import GomokuAI


def find_open_three_move(board, color):
    """脚本对手：找能成活三的点"""
    from evaluate import open_three_points
    pts = open_three_points(board.grid, color)
    if pts:
        # 选一个能形成最多威胁的
        return pts[0]
    return None


def find_four_move(board, color):
    from evaluate import open_four_points
    pts = open_four_points(board.grid, color)
    return pts[0] if pts else None


def find_win_move(board, color):
    for r in range(SIZE):
        for c in range(SIZE):
            if board.grid[r][c] != EMPTY:
                continue
            board.grid[r][c] = color
            w = board.has_five(r, c, color)
            board.grid[r][c] = EMPTY
            if w:
                return (r, c)
    return None


def scripted_move(board, color):
    """脚本对手优先级：成五 > 冲四/活四 > 活三 > 随机靠子"""
    m = find_win_move(board, color)
    if m:
        return m
    m = find_four_move(board, color)
    if m:
        return m
    m = find_open_three_move(board, color)
    if m:
        return m
    # 靠子
    for r in range(SIZE):
        for c in range(SIZE):
            if board.grid[r][c] != EMPTY:
                continue
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < SIZE and 0 <= cc < SIZE and board.grid[rr][cc] != EMPTY:
                        return (r, c)
    return (7, 7)


def run(tag, ai_color=WHITE, time_limit=1.0, max_depth=6, verbose=True):
    board = Board()
    ai = GomokuAI(time_limit=time_limit, max_depth=max_depth)
    ai.reset()

    for turn in range(120):
        if board.side == ai_color:
            r, c = ai.decide(board)
            tag_move = 'AI '
        else:
            r, c = scripted_move(board, board.side)
            tag_move = 'OPP'
        board.make_move(r, c)
        if verbose:
            print(f'{turn+1:3d}. {tag_move} {chr(65+c)}{r}  {ai.stats_summary() if tag_move=="AI " else ""}')
        w = board.check_win()
        if w != EMPTY:
            who = 'AI' if w == ai_color else 'OPP'
            print(f'>>> {tag}: winner={who} in {turn+1} moves')
            return who == 'AI'
        if board.is_full():
            print(f'>>> {tag}: draw')
            return None
    print(f'>>> {tag}: unfinished')
    return None


if __name__ == '__main__':
    wins = 0
    total = 0
    for depth in (4, 6):
        ok = run(f'depth={depth}', ai_color=WHITE, time_limit=1.0, max_depth=depth, verbose=False)
        total += 1
        if ok:
            wins += 1
    print(f'AI vs scripted attacker: {wins}/{total} games won')
