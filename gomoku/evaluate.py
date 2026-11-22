"""
估值函数：威胁等级、点值 G、局面值 F、双威胁检测

核心思想（详见 report/algorithm-design.md §3）：
- W(p,c)：c 在 p 落子后，"再落一子即成五"的空点集合
- 威胁等级按 |W| 和"下一步可达性"递推定义，不靠棋型字符串匹配：
    L5  成五
    L4o 活四（|W| >= 2，两端成五，不可防）
    L4s 冲四（|W| == 1，一点成五，强制应对）
    L3o 活三（下一步可成活四）
    L3s 眠三（下一步只可成冲四）
    L2  活二
- 点值 G = 四个方向模式分之和（题目定义）
- 局面值 F = maxG1 - maxG2（题目定义）
"""

from board import (SIZE, EMPTY, BLACK, WHITE, DIRS, SCORE, MATE,
                   LINES, line_score)

_RANK = {'L5': 5, 'L4o': 4, 'L4s': 3, 'L3o': 2, 'L3s': 1, 'OTHER': 0}


# ============================================================
#  W(p,c)：成五点集
# ============================================================

def _win_points_in_dir(grid, r, c, color, dr, dc):
    """
    前提：(r,c) 已落 color。
    仅看方向 (dr,dc)，返回"再落一子即该方向成五"的空点集合。
    """
    result = set()
    for j in range(5):
        base_r = r + (j - 4) * dr
        base_c = c + (j - 4) * dc
        cnt = 0
        empty_pt = None
        ok = True
        for k in range(5):
            rr = base_r + k * dr
            cc = base_c + k * dc
            if not (0 <= rr < SIZE and 0 <= cc < SIZE):
                ok = False
                break
            v = grid[rr][cc]
            if v == color:
                cnt += 1
            elif v == EMPTY:
                empty_pt = (rr, cc)
            else:
                ok = False          # 窗口内混入对方棋子，该窗口无效
                break
        if ok and cnt == 4 and empty_pt is not None:
            result.add(empty_pt)
    return result


def _win_count_in_dir(grid, r, c, color, dr, dc):
    """
    与 _win_points_in_dir 等价，但只数个数（0/1/2），不建集合、提前退出。
    热路径专用。
    """
    n = 0
    for j in range(5):
        base_r = r + (j - 4) * dr
        base_c = c + (j - 4) * dc
        cnt = 0
        empty_cnt = 0
        ok = True
        for k in range(5):
            rr = base_r + k * dr
            cc = base_c + k * dc
            if not (0 <= rr < SIZE and 0 <= cc < SIZE):
                ok = False
                break
            v = grid[rr][cc]
            if v == color:
                cnt += 1
            elif v == EMPTY:
                empty_cnt += 1
            else:
                ok = False
                break
        if ok and cnt == 4 and empty_cnt == 1:
            n += 1
            if n >= 2:
                return 2
    return n


def win_one_points(grid, r, c, color):
    """(r,c) 已落 color，返回四方向合并的成五点集"""
    pts = set()
    for dr, dc in DIRS:
        pts |= _win_points_in_dir(grid, r, c, color, dr, dc)
    return pts


# ============================================================
#  方向局部威胁等级
# ============================================================

def dir_level(grid, r, c, color, dr, dc, light=False):
    """
    (r,c) 已落 color 时，仅评估方向 (dr,dc) 的等级。
    light=True 跳过 L3 前瞻（深层节点排序用，快 5~10 倍）。
    返回 'L5' | 'L4o' | 'L4s' | 'L3o' | 'L3s' | 'OTHER'
    """
    # L5：该方向连成 5 子及以上
    cnt = 1
    rr, cc = r + dr, c + dc
    while 0 <= rr < SIZE and 0 <= cc < SIZE and grid[rr][cc] == color:
        cnt += 1
        rr += dr
        cc += dc
    rr, cc = r - dr, c - dc
    while 0 <= rr < SIZE and 0 <= cc < SIZE and grid[rr][cc] == color:
        cnt += 1
        rr -= dr
        cc -= dc
    if cnt >= 5:
        return 'L5'

    wps_cnt = _win_count_in_dir(grid, r, c, color, dr, dc)
    if wps_cnt >= 2:
        return 'L4o'
    if wps_cnt == 1:
        return 'L4s'

    if light:
        return 'OTHER'

    # L3：该方向存在空点 q，落 q 后该方向可成活四 / 只能成冲四
    cand = []
    for k in range(-4, 5):
        if k == 0:
            continue
        qr, qc = r + k * dr, c + k * dc
        if not (0 <= qr < SIZE and 0 <= qc < SIZE):
            continue
        if grid[qr][qc] != EMPTY:
            continue
        cand.append((qr, qc))

    for qr, qc in cand:
        grid[qr][qc] = color
        q_cnt = _win_count_in_dir(grid, qr, qc, color, dr, dc)
        grid[qr][qc] = EMPTY
        if q_cnt >= 2:
            return 'L3o'

    for qr, qc in cand:
        grid[qr][qc] = color
        q_cnt = _win_count_in_dir(grid, qr, qc, color, dr, dc)
        grid[qr][qc] = EMPTY
        if q_cnt == 1:
            return 'L3s'

    return 'OTHER'


def line_potential(grid, r, c, color):
    """
    廉价局面潜力（不考虑精确威胁等级），专供深层节点排序：
    统计 (r,c) 四方向 ±4 范围内的己方/对方棋子数，按"连子越多越值钱"加权。
    """
    opp = WHITE if color == BLACK else BLACK
    score = 0
    for dr, dc in DIRS:
        mine = 0
        theirs = 0
        for k in range(-4, 5):
            if k == 0:
                continue
            rr, cc = r + k * dr, c + k * dc
            if not (0 <= rr < SIZE and 0 <= cc < SIZE):
                continue
            v = grid[rr][cc]
            if v == color:
                mine += 1
            elif v == opp:
                theirs += 1
        # 己方连子权重高；对方连子说明此处也是对手要点（防守价值）
        score += mine * mine * 10 + theirs * theirs * 8 + (mine + theirs) * 2
    return score


def quick_threat(grid, r, c, color, light=False):
    """四方向中的最高威胁等级（用于着法排序）"""
    grid[r][c] = color
    best = 'OTHER'
    for dr, dc in DIRS:
        lv = dir_level(grid, r, c, color, dr, dc, light=light)
        if _RANK[lv] > _RANK[best]:
            best = lv
            if best == 'L5':
                break
    grid[r][c] = EMPTY
    return best


def threat_level(grid, r, c, color):
    """返回 (等级, 分值)，兼容报告 §3.3 的描述"""
    lv = quick_threat(grid, r, c, color)
    if lv == 'OTHER':
        return ('NONE', 0)
    return (lv, SCORE[lv])


# ============================================================
#  点值 G / 局面值 F（题目定义）
# ============================================================

def point_value(grid, r, c, color):
    """
    G_color(r,c)：在 (r,c) 落 color 后，四方向模式分之和。
    同方向只按该方向最高等级计一次，避免重复计分。
    """
    grid[r][c] = color
    total = 0
    for dr, dc in DIRS:
        lv = dir_level(grid, r, c, color, dr, dc)
        if lv != 'OTHER':
            total += SCORE[lv]
    grid[r][c] = EMPTY
    return total


def evaluate_position(board):
    """返回 (maxG1, maxG2, F)：题目定义的己方/对手最大点值与局面优势度"""
    side = board.side
    opp = board.opponent()
    maxG1 = 0
    maxG2 = 0
    for r in range(SIZE):
        for c in range(SIZE):
            if board.grid[r][c] != EMPTY:
                continue
            g1 = point_value(board.grid, r, c, side)
            if g1 > maxG1:
                maxG1 = g1
            g2 = point_value(board.grid, r, c, opp)
            if g2 > maxG2:
                maxG2 = g2
    return maxG1, maxG2, maxG1 - maxG2


# ============================================================
#  双威胁检测（规则 R1）—— 必须按方向计数
# ============================================================

def is_double_threat(grid, r, c, color):
    """
    (r,c) 落 color 后是否形成"对手一手防不住"的双威胁。

    按方向计数（同一方向只算一个威胁，避免把活三的两个端点数成两个威胁）：
      - 任一方向成五 / 活四     -> True
      - 两个不同方向各有冲四     -> True（四四）
      - 一个方向冲四 + 另一方向活三 -> True（四三）
      - 两个不同方向各有活三     -> True（双活三）
    """
    grid[r][c] = color

    l4_dirs = 0
    l3o_dirs = 0
    win = False

    for dr, dc in DIRS:
        lv = dir_level(grid, r, c, color, dr, dc)
        if lv == 'L5' or lv == 'L4o':
            win = True
            break
        if lv == 'L4s':
            l4_dirs += 1
        elif lv == 'L3o':
            l3o_dirs += 1

    grid[r][c] = EMPTY

    if win:
        return True
    if l4_dirs >= 2:
        return True
    if l4_dirs >= 1 and l3o_dirs >= 1:
        return True
    if l3o_dirs >= 2:
        return True
    return False


# ============================================================
#  战术查询：活三 / 活四威胁点
# ============================================================

def _near_stone(grid, r, c):
    """粗筛：周围 1 格内有棋子才值得计算"""
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            rr, cc = r + dr, c + dc
            if 0 <= rr < SIZE and 0 <= cc < SIZE and grid[rr][cc] != EMPTY:
                return True
    return False


def open_four_points(grid, color, cands=None):
    """
    找出所有空点 q：color 落在 q 后，某方向形成活四（|W| >= 2）。
    也就是"color 下一手能造出不可阻挡的活四"的点。
    若 color 已有活三，这些就是必须封堵的点。
    """
    if cands is None:
        cands = [(r, c) for r in range(SIZE) for c in range(SIZE)
                 if grid[r][c] == EMPTY and _near_stone(grid, r, c)]
    pts = []
    for r, c in cands:
        if grid[r][c] != EMPTY:
            continue
        grid[r][c] = color
        hit = False
        for dr, dc in DIRS:
            if dir_level(grid, r, c, color, dr, dc, light=True) == 'L4o':
                hit = True
                break
        grid[r][c] = EMPTY
        if hit:
            pts.append((r, c))
    return pts


def open_three_points(grid, color, cands=None):
    """找出所有空点 q：color 落 q 后形成活三（下一手可成活四）"""
    if cands is None:
        cands = [(r, c) for r in range(SIZE) for c in range(SIZE)
                 if grid[r][c] == EMPTY and _near_stone(grid, r, c)]
    pts = []
    for r, c in cands:
        if grid[r][c] != EMPTY:
            continue
        grid[r][c] = color
        hit = False
        for dr, dc in DIRS:
            if dir_level(grid, r, c, color, dr, dc) == 'L3o':
                hit = True
                break
        grid[r][c] = EMPTY
        if hit:
            pts.append((r, c))
    return pts


# ============================================================
#  叶节点估值（O(1)：读 board 增量维护的线模式总分）
# ============================================================

def linear_eval(board):
    """
    返回对 board.side 的局势估值（正=有利，负=不利）。

    board 在落子/撤销时增量维护每条线的模式分（只更新经过落点的 4 条线），
    因此这里只是两次查表，复杂度 O(1)。
    防守项加权 1.15，让 AI 略偏保守。
    """
    me = board.score_of(board.side)
    op = board.score_of(board.opponent())
    return me - int(op * 1.15)
