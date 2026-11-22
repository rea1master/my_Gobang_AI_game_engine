"""
场景测试：真正两端全开的活三，AI 是否必堵。
每个场景构造好后直接问 AI，检查落点是否落在合理防守点集合里。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board, BLACK, WHITE, EMPTY, SIZE
from engine import GomokuAI
from evaluate import open_four_points


def build(black_pts, white_pts, side):
    b = Board()
    for (r, c) in black_pts:
        b.grid[r][c] = BLACK
    for (r, c) in white_pts:
        b.grid[r][c] = WHITE
    # 直接改 grid 后重建增量估值
    for (r, c) in list(black_pts) + list(white_pts):
        b._refresh_cell_lines(r, c, b.grid[r][c])
    b.moves = [(r, c, BLACK) for (r, c) in black_pts] + [(r, c, WHITE) for (r, c) in white_pts]
    b.side = side
    return b


CASES = [
    ('横向活三', [(7, 5), (7, 6), (7, 7)], [(2, 12), (3, 12), (3, 11)], {(7, 4), (7, 8)}),
    ('纵向活三', [(5, 7), (6, 7), (7, 7)], [(12, 2), (12, 3), (11, 3)], {(4, 7), (8, 7)}),
    ('主对角活三', [(5, 5), (6, 6), (7, 7)], [(2, 12), (3, 12), (3, 11)], {(4, 4), (8, 8)}),
    ('副对角活三', [(5, 9), (6, 8), (7, 7)], [(12, 2), (12, 3), (11, 3)], {(4, 10), (8, 6)}),
    ('跳活三 X_XX', [(7, 5), (7, 6), (7, 8)], [(2, 12), (3, 12), (3, 11)], {(7, 7), (7, 9), (7, 4)}),
]

ai = GomokuAI(time_limit=1.0, max_depth=6)
ok_all = True
for name, black_pts, white_pts, expect in CASES:
    b = build(black_pts, white_pts, WHITE)
    danger = set(open_four_points(b.grid, BLACK))
    ai.reset()
    mv = ai.decide(b)
    good = mv in danger or mv in expect
    ok_all &= good
    print(f'{name}: AI -> {mv}, 防守点集={sorted(danger)}, 判定={"OK" if good else "FAIL"} | {ai.stats_summary()}')

print('\n结果:', 'ALL PASSED' if ok_all else 'HAS FAILURES')
