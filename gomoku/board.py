"""
棋盘表示与基础操作
- 15x15 棋盘，用整数数组表示 (0 空, 1 黑, 2 白)
- 落子/撤销
- 胜负判定（五连即胜，含 6 连及以上）
- Zobrist 哈希（64 位）增量维护
- 线模式分值增量维护（落子只更新经过该点的 4 条线，估值 O(1)）
- 坐标格式：(row, col)
"""

import random

SIZE = 15
EMPTY = 0
BLACK = 1
WHITE = 2

# ---- 方向向量（横、竖、主对角、副对角） ----
DIRS = [(0, 1), (1, 0), (1, 1), (1, -1)]

# ---- 模式分值表（对数刻度：10 倍一跳）----
SCORE = {
    'L5':  1000_0000,   # 成五
    'L4o':  100_0000,   # 活四
    'L4s':    10_0000,   # 冲四
    'L3o':     1_0000,   # 活三
    'L3s':      1000,   # 眠三
    'L2':         100,   # 活二
}
MATE = 1_0000_0000        # 必胜分，大于所有模式分之和


def _build_lines():
    """全盘 72 条线：横 15 + 竖 15 + 两向斜线各 21"""
    lines = []
    for r in range(SIZE):
        lines.append([(r, c) for c in range(SIZE)])
    for c in range(SIZE):
        lines.append([(r, c) for r in range(SIZE)])
    for start_r in range(SIZE):
        pts = []
        r, c = start_r, 0
        while r < SIZE and c < SIZE:
            pts.append((r, c)); r += 1; c += 1
        if len(pts) >= 5:
            lines.append(pts)
    for start_c in range(1, SIZE):
        pts = []
        r, c = 0, start_c
        while r < SIZE and c < SIZE:
            pts.append((r, c)); r += 1; c += 1
        if len(pts) >= 5:
            lines.append(pts)
    for start_r in range(SIZE):
        pts = []
        r, c = start_r, SIZE - 1
        while r < SIZE and c >= 0:
            pts.append((r, c)); r += 1; c -= 1
        if len(pts) >= 5:
            lines.append(pts)
    for start_c in range(SIZE - 1):
        pts = []
        r, c = 0, start_c
        while r < SIZE and c >= 0:
            pts.append((r, c)); r += 1; c -= 1
        if len(pts) >= 5:
            lines.append(pts)
    return lines


LINES = _build_lines()

# 每个格子属于哪些线、在线中的位置
CELL_LINES = {}
for _li, _line in enumerate(LINES):
    for _pos, (_r, _c) in enumerate(_line):
        CELL_LINES.setdefault((_r, _c), []).append((_li, _pos))


def line_score(vals, me):
    """
    单条线上 me 的威胁分（同一条线只按最高等级计一次，避免滑窗重复计分）。
    """
    n = len(vals)
    five = 0
    completions = set()
    l3o = 0

    for i in range(n - 4):
        s_cnt = 0
        empty_pos = -1
        blocked = False
        for k in range(5):
            v = vals[i + k]
            if v == me:
                s_cnt += 1
            elif v == EMPTY:
                if empty_pos < 0:
                    empty_pos = k
            else:
                blocked = True
                break
        if blocked:
            continue

        if s_cnt == 5:
            five += 1
        elif s_cnt == 4:
            completions.add(i + empty_pos)
        elif s_cnt == 3:
            if i > 0 and vals[i - 1] == EMPTY and i + 5 < n and vals[i + 5] == EMPTY:
                l3o += 1

    if five:
        return SCORE['L5'] * five
    if len(completions) >= 2:
        return SCORE['L4o']
    if len(completions) == 1:
        return SCORE['L4s']
    if l3o:
        return SCORE['L3o'] * min(l3o, 2)
    return 0


class Board:
    __slots__ = ('grid', 'side', 'moves', 'zhash', 'zobrist_table',
                 'line_vals', 'line_sc', 'total')

    def __init__(self):
        self.grid = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.side = BLACK
        self.moves = []
        rng = random.Random(20231120)
        self.zobrist_table = [
            [[rng.getrandbits(64) for _ in range(2)] for _ in range(SIZE)]
            for _ in range(SIZE)
        ]
        self.zhash = 0
        # 增量线估值
        self.line_vals = [[EMPTY] * len(line) for line in LINES]
        self.line_sc = [[0, 0] for _ in LINES]   # [黑分, 白分]
        self.total = [0, 0]

    # ----- 访问 ----------
    def get(self, r, c):
        if not (0 <= r < SIZE and 0 <= c < SIZE):
            return -1
        return self.grid[r][c]

    @property
    def move_count(self):
        return len(self.moves)

    def opponent(self, color=None):
        c = color or self.side
        return WHITE if c == BLACK else BLACK

    # ----- 增量线估值维护 -----
    def _refresh_cell_lines(self, r, c, color):
        """重算经过 (r,c) 的 4 条线的分值，并更新总分"""
        for li, pos in CELL_LINES[(r, c)]:
            old_b, old_w = self.line_sc[li]
            self.total[0] -= old_b
            self.total[1] -= old_w

            self.line_vals[li][pos] = color
            vals = self.line_vals[li]
            nb = line_score(vals, BLACK)
            nw = line_score(vals, WHITE)
            self.line_sc[li][0] = nb
            self.line_sc[li][1] = nw

            self.total[0] += nb
            self.total[1] += nw

    def score_of(self, color):
        """该颜色的线模式总分（增量维护，O(1)）"""
        return self.total[color - 1]

    # ----- 落子 / 撤销 -----
    def make_move(self, r, c):
        color = self.side
        self.grid[r][c] = color
        self.zhash ^= self.zobrist_table[r][c][color - 1]
        self._refresh_cell_lines(r, c, color)
        self.moves.append((r, c, color))
        self.side = self.opponent()

    def unmake_move(self):
        r, c, color = self.moves.pop()
        self.grid[r][c] = EMPTY
        self.zhash ^= self.zobrist_table[r][c][color - 1]
        self._refresh_cell_lines(r, c, EMPTY)
        self.side = color

    # ----- 胜负判定 -----
    def has_five(self, r, c, color):
        for dr, dc in DIRS:
            cnt = 1
            rr, cc = r + dr, c + dc
            while 0 <= rr < SIZE and 0 <= cc < SIZE and self.grid[rr][cc] == color:
                cnt += 1; rr += dr; cc += dc
            rr, cc = r - dr, c - dc
            while 0 <= rr < SIZE and 0 <= cc < SIZE and self.grid[rr][cc] == color:
                cnt += 1; rr -= dr; cc -= dc
            if cnt >= 5:
                return True
        return False

    def check_win(self):
        if not self.moves:
            return EMPTY
        r, c, col = self.moves[-1]
        return col if self.has_five(r, c, col) else EMPTY

    def is_full(self):
        return len(self.moves) == SIZE * SIZE

    # ----- 显示 -----
    COLS = 'ABCDEFGHIJKLMNO'

    def col_label(self, c):
        return self.COLS[c] if c < len(self.COLS) else str(c)

    def __str__(self):
        lines = ['   ' + ' '.join(self.col_label(c) for c in range(SIZE))]
        CH = {EMPTY: '.', BLACK: 'X', WHITE: 'O'}
        for r in range(SIZE):
            lines.append(f'{r:2} ' + ' '.join(CH[self.grid[r][c]] for c in range(SIZE)))
        side_name = 'BLACK(X)' if self.side == BLACK else 'WHITE(O)'
        lines.append(f'  side to move: {side_name}')
        return '\n'.join(lines)

    def copy(self):
        b = Board.__new__(Board)
        b.grid = [row[:] for row in self.grid]
        b.side = self.side
        b.moves = list(self.moves)
        b.zobrist_table = self.zobrist_table
        b.zhash = self.zhash
        b.line_vals = [row[:] for row in self.line_vals]
        b.line_sc = [row[:] for row in self.line_sc]
        b.total = list(self.total)
        return b
