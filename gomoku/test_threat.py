import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board, BLACK, WHITE, EMPTY
from engine import GomokuAI
from evaluate import is_double_threat, open_four_points, quick_threat


def show(tag, b):
    print(f'--- {tag} ---')
    print(b)


# 用例1：黑棋斜线活三 (4,4)(5,5)(6,6)，两端 (3,3)(7,7) 空，轮到白
b = Board()
for p in [(4, 4), (5, 5), (6, 6)]:
    b.grid[p[0]][p[1]] = BLACK
b.grid[0][0] = WHITE
b.grid[14][14] = WHITE
b.side = WHITE
b.moves = [(0, 0, WHITE), (4, 4, BLACK), (14, 14, WHITE), (5, 5, BLACK), (6, 6, BLACK)]

danger = open_four_points(b.grid, BLACK)
print(f'黑方活四威胁点(活三两端): {danger}')
assert set(danger) >= {(3, 3), (7, 7)}, danger

ai = GomokuAI(time_limit=1.0, max_depth=6)
ai.reset()
m = ai.decide(b)
print(f'AI 应对斜线活三 -> {m} | {ai.stats_summary()}')
assert m in [(3, 3), (7, 7)], f'AI 没堵活三！走了 {m}'

# 用例2：同时有两个方向的活三（双活三），应识别为双威胁
b2 = Board()
b2.grid[7][7] = BLACK
b2.grid[7][5] = BLACK
b2.grid[7][6] = BLACK      # 横向活三
b2.grid[5][7] = BLACK
b2.grid[6][7] = BLACK      # 纵向活三
b2.side = WHITE
b2.moves = [(7, 5, BLACK), (7, 6, BLACK), (7, 7, BLACK), (5, 7, BLACK), (6, 7, BLACK)]
t = quick_threat(b2.grid, 7, 9, BLACK)
print(f'黑在(7,9)的威胁等级: {t}')

# 用例3：AI 搜索深度与速度
b3 = Board()
b3.make_move(7, 7)
ai2 = GomokuAI(time_limit=1.0, max_depth=8)
ai2.reset()
m3 = ai2.decide(b3)
print(f'空盘应手 -> {m3} | {ai2.stats_summary()}')

print('\nALL THREAT TESTS PASSED')
