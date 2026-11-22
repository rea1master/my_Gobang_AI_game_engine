"""
Alpha-Beta 搜索 + 迭代加深 + 置换表 + 静态搜索

Negamax 形式，窗口 (alpha, beta)，从"当前该走方"视角取值。
"""

import time
from board import SIZE, EMPTY, BLACK, WHITE
from evaluate import MATE, linear_eval, SCORE, quick_threat, point_value
from movegen import ordered_moves, generate_candidates

# ---- 置换表 ----
TT_SIZE = 1 << 18  # 约 26 万条目
TT_MASK = TT_SIZE - 1

# flag 值
EXACT = 0
LOWER = 1   # 下界（beta 截断）
UPPER = 2   # 上界（alpha 未更新）


class TTEntry:
    __slots__ = ('zhash', 'depth', 'flag', 'score', 'best_move')
    def __init__(self, zhash=0, depth=0, flag=EXACT, score=0, best_move=None):
        self.zhash = zhash
        self.depth = depth
        self.flag = flag
        self.score = score
        self.best_move = best_move


tt = [TTEntry() for _ in range(TT_SIZE)]


def tt_probe(zhash, depth, alpha, beta):
    """置换表探测；返回 (hit, score, best_move)"""
    idx = zhash & TT_MASK
    e = tt[idx]
    if e.zhash != zhash:
        return (False, 0, None)
    if e.depth < depth:
        return (False, 0, e.best_move)  # 深度不够，但 best_move 可用于排序
    sc = e.score
    if e.flag == EXACT:
        return (True, sc, e.best_move)
    if e.flag == LOWER and sc >= beta:
        return (True, beta, e.best_move)
    if e.flag == UPPER and sc <= alpha:
        return (True, alpha, e.best_move)
    return (False, sc, e.best_move)


def tt_store(zhash, depth, flag, score, best_move):
    idx = zhash & TT_MASK
    e = tt[idx]
    # 替换策略：同 zhash 且深度不大于当前则覆盖；不同 zhash 直接覆盖
    if e.zhash == zhash and e.depth > depth:
        return
    e.zhash = zhash
    e.depth = depth
    e.flag = flag
    e.score = score
    e.best_move = best_move


# ---- 搜索主函数 ----

# 全局统计
nodes_searched = 0
tt_hits = 0
start_time = 0
time_limit = 0


def reset_stats():
    global nodes_searched, tt_hits, start_time, time_limit
    nodes_searched = 0
    tt_hits = 0
    start_time = time.time()
    time_limit = 1.0


def time_out():
    return time.time() - start_time >= time_limit * 0.9


# ---- 静态搜索（quiescence）----

def quiesce(board, alpha, beta, ply, qdepth=0):
    """只搜索强制着法（冲四/活四），消除水平线效应。深度上限 6 层。"""
    global nodes_searched
    if time_out():
        return 0
    nodes_searched += 1

    # 静态估值
    stand_pat = linear_eval(board)
    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    if qdepth >= 6:
        return alpha

    # 只考虑己方能立刻造出冲四/活四的着法（强制着法）
    side = board.side
    forcing = []
    for r, c in generate_candidates(board):
        if quick_threat(board.grid, r, c, side, light=True) in ('L4o', 'L4s'):
            forcing.append((r, c))

    for r, c in forcing:
        board.make_move(r, c)
        v = -quiesce(board, -beta, -alpha, ply + 1, qdepth + 1)
        board.unmake_move()
        if v >= beta:
            return beta
        if v > alpha:
            alpha = v

    return alpha


# ---- Alpha-Beta ----

def alphabeta(board, depth, alpha, beta, ply):
    """
    Negamax Alpha-Beta 搜索。
    返回值：从"当前该走方"的视角的估值。
    """
    global nodes_searched, tt_hits
    if time_out():
        return 0
    nodes_searched += 1

    # 终局检测
    winner = board.check_win()
    if winner != EMPTY:
        # 上一步落子方（winner）赢了 → 当前该走方已输
        return -MATE + ply

    if board.is_full():
        return 0  # 平局

    # 置换表
    zhash = board.zhash
    hit, score, tt_move = tt_probe(zhash, depth, alpha, beta)
    if hit:
        tt_hits += 1
        return score

    # 深度到底
    if depth <= 0:
        return quiesce(board, alpha, beta, ply)

    # 生成候选着法（只有根节点做完整排序，深层用轻量排序）
    if ply <= 0:
        moves = ordered_moves(board, max_moves=16, light=False)
    else:
        moves = ordered_moves(board, max_moves=10, light=True)

    # 把置换表最佳着法提到最前
    if tt_move is not None:
        for i, m in enumerate(moves):
            if m == tt_move:
                moves.insert(0, moves.pop(i))
                break

    best_move = None
    best_score = -MATE * 2
    flag = UPPER
    side = board.side

    for i, (r, c) in enumerate(moves):
        board.make_move(r, c)

        # PVS: 第一个着法全窗口，后续零窗口
        if i == 0:
            v = -alphabeta(board, depth - 1, -beta, -alpha, ply + 1)
        else:
            # 零窗口尝试
            v = -alphabeta(board, depth - 1, -alpha - 1, -alpha, ply + 1)
            if alpha < v < beta:
                # 重新搜索
                v = -alphabeta(board, depth - 1, -beta, -v, ply + 1)

        board.unmake_move()

        if v > best_score:
            best_score = v
            best_move = (r, c)
        if v > alpha:
            alpha = v
            flag = EXACT

        if alpha >= beta:
            flag = LOWER
            break

    if flag == UPPER:
        best_score = alpha

    tt_store(zhash, depth, flag, best_score, best_move)
    return best_score


# ---- 迭代加深 ----

def iterative_deepening(board, max_depth=10, tt_limit=1.0):
    """
    迭代加深外层，返回 (best_move, best_score, depth_reached)。
    """
    global time_limit, start_time

    start_time = time.time()
    time_limit = tt_limit

    best_move = None
    best_score = 0

    # 先检查立即胜
    from movegen import find_winning_move, find_blocking_moves
    wm = find_winning_move(board)
    if wm:
        return wm, MATE, 0

    # 初始化
    moves = ordered_moves(board, max_moves=20)
    if not moves:
        return (7, 7), 0, 0  # 空盘天元

    # 逐步加深
    for d in range(1, max_depth + 1):
        alpha = -MATE * 2
        beta = MATE * 2
        best_move_d = None
        best_score_d = -MATE * 2

        for r, c in moves:
            board.make_move(r, c)
            v = -alphabeta(board, d - 1, -beta, -alpha, 1)
            board.unmake_move()

            if v > best_score_d:
                best_score_d = v
                best_move_d = (r, c)
            if time_out() and d > 1:
                # 时间用完，返回上一层的完整结果
                return best_move, best_score, d - 1

        if time_out() and d > 1:
            return best_move, best_score, d - 1

        # 本层完成
        best_move = best_move_d
        best_score = best_score_d

        # 必胜/必负早停
        if best_score >= MATE - 50:
            return best_move, best_score, d
        if best_score <= -MATE + 50:
            # 核实：如果不是唯一堵点，可以继续
            pass

    return best_move, best_score, max_depth