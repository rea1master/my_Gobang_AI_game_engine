"""
「普通人」基准对手（用于标定难度胜率）

行为模拟一个会看威胁、但不算深的普通玩家：
1. 能赢就赢
2. 对手要赢就堵
3. 能造活四就造
4. 对手要造活四就堵
5. 能造活三就造
6. 否则在已有棋子附近挑一个"看起来还行"的点，带一点随机性
"""

import random
from board import SIZE, EMPTY, BLACK, WHITE
from evaluate import open_four_points, open_three_points, point_value


def _near_cands(grid):
    pts = []
    for r in range(SIZE):
        for c in range(SIZE):
            if grid[r][c] != EMPTY:
                continue
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < SIZE and 0 <= cc < SIZE and grid[rr][cc] != EMPTY:
                        pts.append((r, c))
                        break
                else:
                    continue
                break
    return pts


def _win_move(grid, color):
    for r in range(SIZE):
        for c in range(SIZE):
            if grid[r][c] != EMPTY:
                continue
            grid[r][c] = color
            w = _has_five(grid, r, c, color)
            grid[r][c] = EMPTY
            if w:
                return (r, c)
    return None


def _has_five(grid, r, c, color):
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        cnt = 1
        rr, cc = r + dr, c + dc
        while 0 <= rr < SIZE and 0 <= cc < SIZE and grid[rr][cc] == color:
            cnt += 1; rr += dr; cc += dc
        rr, cc = r - dr, c - dc
        while 0 <= rr < SIZE and 0 <= cc < SIZE and grid[rr][cc] == color:
            cnt += 1; rr -= dr; cc -= dc
        if cnt >= 5:
            return True
    return False


class HumanProxy:
    """普通人代理：slip 为走"随手棋"的概率"""

    def __init__(self, slip=0.20, seed=None):
        self.slip = slip
        self.rng = random.Random(seed)

    def reset(self):
        pass

    def decide(self, board):
        grid = board.grid
        me = board.side
        opp = board.opponent()
        cands = _near_cands(grid)
        if not cands:
            return (7, 7)

        # 1. 赢
        m = _win_move(grid, me)
        if m:
            return m
        # 2. 堵五
        m = _win_move(grid, opp)
        if m:
            return m

        # 随手棋：随机挑一个靠子点
        if self.rng.random() < self.slip:
            return self.rng.choice(cands[:40])

        # 3. 自己造活四
        mine4 = open_four_points(grid, me, cands)
        if mine4:
            return max(mine4, key=lambda rc: point_value(grid, rc[0], rc[1], me))
        # 4. 堵对手活四
        opp4 = open_four_points(grid, opp, cands)
        if opp4:
            return max(opp4, key=lambda rc: point_value(grid, rc[0], rc[1], me))
        # 5. 自己造活三
        mine3 = open_three_points(grid, me, cands)
        if mine3:
            return max(mine3, key=lambda rc: point_value(grid, rc[0], rc[1], me))
        # 6. 堵对手活三
        opp3 = open_three_points(grid, opp, cands)
        if opp3:
            return max(opp3, key=lambda rc: point_value(grid, rc[0], rc[1], me))

        # 7. 挑点值最高的
        return max(cands[:60], key=lambda rc: point_value(grid, rc[0], rc[1], me))
