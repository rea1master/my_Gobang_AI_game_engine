"""
候选点生成与排序
- 邻域裁剪：只考虑距已有棋子 Chebyshev 距离 ≤ 2 的空点（命题 1）
- 排序键：成五 > 堵五 > 冲四 > 活三 > 点值 G
"""

from board import SIZE, EMPTY, BLACK, WHITE
from evaluate import quick_threat, point_value, is_double_threat, line_potential


def generate_candidates(board):
    """
    返回候选点列表 [(row, col), ...]，按"距离已有棋子 ≤ 2"筛选。
    """
    if board.move_count == 0:
        # 开局首手：天元
        return [(7, 7)]

    visited = set()
    candidates = []

    # 收集所有已有棋子
    stones = [(r, c) for r in range(SIZE) for c in range(SIZE)
              if board.grid[r][c] != EMPTY]

    for sr, sc in stones:
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                r, c = sr + dr, sc + dc
                if 0 <= r < SIZE and 0 <= c < SIZE:
                    if board.grid[r][c] == EMPTY and (r, c) not in visited:
                        visited.add((r, c))
                        candidates.append((r, c))

    return candidates


def rank_move(board, r, c, light=False):
    """
    返回着法 (r,c) 的排序键。
    排序键越小越优先（直接比较 tuple）。
    键 = (priority_class, -point_score)
    priority_class: 0=成五(己)  1=堵五(敌)  2=四/双威胁  3=活三  4=其他
    light=True 时跳过昂贵的 L3 前瞻与双威胁检测（深层节点用）。
    """
    side = board.side
    opp = board.opponent()

    # 0: 己方成五
    board.grid[r][c] = side
    if board.has_five(r, c, side):
        board.grid[r][c] = EMPTY
        return (0, -10_000_000)
    board.grid[r][c] = EMPTY

    # 1: 对方成五（必堵）
    board.grid[r][c] = opp
    if board.has_five(r, c, opp):
        board.grid[r][c] = EMPTY
        return (1, -10_000_000)
    board.grid[r][c] = EMPTY

    # 2–4: 威胁等级（防守优先）
    if light:
        # 轻量模式：只做 L4 级检测（不看 L3 前瞻），再用廉价潜力分排序
        qt_opp = quick_threat(board.grid, r, c, opp, light=True)
        if qt_opp == 'L4o':
            return (2, -2_000_000)
        if qt_opp == 'L4s':
            return (2, -150_000)
        qt_side = quick_threat(board.grid, r, c, side, light=True)
        if qt_side == 'L4o':
            return (2, -1_900_000)
        if qt_side == 'L4s':
            return (2, -140_000)
        return (4, -line_potential(board.grid, r, c, side))

    qt_opp = quick_threat(board.grid, r, c, opp, light=False)
    if qt_opp == 'L4o':
        return (2, -2_000_000)
    if qt_opp == 'L4s':
        return (2, -150_000)
    if qt_opp == 'L3o':
        # 对手在此落子能成活三 → 这是防守要点
        return (3, -95_000)

    qt_side = quick_threat(board.grid, r, c, side, light=False)
    if qt_side == 'L4o':
        return (2, -1_900_000)
    if qt_side == 'L4s':
        return (2, -140_000)

    # 完整模式（根节点用）
    if is_double_threat(board.grid, r, c, side):
        return (2, -1_800_000)      # 双威胁：必胜着法

    score = point_value(board.grid, r, c, side)
    if qt_side == 'L3o':
        score += 12_000             # 自己成活三
    return (3, -score)


def ordered_moves(board, max_moves=16, light=False):
    """
    生成候选点并排序，取前 max_moves 个。
    先用廉价潜力分预筛（避免对全部候选做威胁检测），再精细排序。
    light=True 用于深层节点。
    """
    cands = generate_candidates(board)
    side = board.side
    pre = 12 if light else 20
    if len(cands) > pre:
        cands.sort(key=lambda rc: -line_potential(board.grid, rc[0], rc[1], side))
        cands = cands[:pre]
    cands.sort(key=lambda rc: rank_move(board, rc[0], rc[1], light=light))
    return cands[:max_moves]


def find_winning_move(board):
    """找到己方一步成五的点，没有返回 None"""
    for r, c in generate_candidates(board):
        board.grid[r][c] = board.side
        win = board.has_five(r, c, board.side)
        board.grid[r][c] = EMPTY
        if win:
            return (r, c)
    return None


def find_blocking_moves(board):
    """找到对手一步成五的点（必须堵），返回列表"""
    opp = board.opponent()
    blocks = []
    for r, c in generate_candidates(board):
        board.grid[r][c] = opp
        if board.has_five(r, c, opp):
            board.grid[r][c] = EMPTY
            blocks.append((r, c))
            continue
        board.grid[r][c] = EMPTY
    return blocks