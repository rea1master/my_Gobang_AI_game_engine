"""
棋盘内部结构演示：把 board.py 里的数据结构逐层打印出来，直接看真值。

运行：python gomoku/demo_board.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board import (Board, SIZE, EMPTY, BLACK, WHITE, LINES, CELL_LINES)


def title(t):
    print()
    print('=' * 60)
    print(t)
    print('=' * 60)


# ---------------- 1. grid 就是一张表格 ----------------
title('1. grid：15 行 × 15 列的表格')
b = Board()
print('grid 的类型：', type(b.grid), '，长度：', len(b.grid), '，每行长度：', len(b.grid[0]))
print()
print('行列下标长这样（只画左上角 5×5）：')
print('       列0 列1 列2 列3 列4')
for r in range(5):
    row = '  '.join(str(b.grid[r][c]) for c in range(5))
    print(f'  行{r}   {row}')
print()
print('读一个格子：grid[2][3] =', b.grid[2][3], '（0 表示空）')

# ---------------- 2. 为什么不能写 [[0]*15]*15 ----------------
title('2. 为什么初始化要写 for 循环')
print('正确写法： [[0]*15 for _ in range(15)]  → 15 行，各自独立')
good = [[0] * 3 for _ in range(3)]
good[0][0] = 9
print('  改 good[0][0]=9 后：', good)

print()
print('错误写法： [[0]*3]*3  → 3 个引用指向同一个列表')
bad = [[0] * 3] * 3
bad[0][0] = 9
print('  改 bad[0][0]=9 后： ', bad, ' ← 三行全变了！')

# ---------------- 3. 三个状态变量 ----------------
title('3. 三个状态变量：grid / side / moves')
b = Board()
print(f'开局：side={b.side}(黑)，moves={b.moves}')

b.make_move(7, 7)
print(f'黑走 (7,7) 后：side={b.side}(白)，moves={b.moves}')

b.make_move(8, 6)
print(f'白走 (8,6) 后：side={b.side}(黑)，moves={b.moves}')

b.unmake_move()
print(f'撤销一步后：  side={b.side}(白)，moves={b.moves}  ← 回到上一步的状态')

# ---------------- 4. Zobrist 表为什么是三维 ----------------
title('4. zobrist_table：为什么是 [15][15][2]')
print('225 个格子 × 2 种颜色 = 450 个随机数')
print('zobrist_table[7][7][0] =', b.zobrist_table[7][7][0], '← (7,7) 放【黑】对应的随机数')
print('zobrist_table[7][7][1] =', b.zobrist_table[7][7][1], '← (7,7) 放【白】对应的随机数')
print('两个数不同，因为“黑在(7,7)”和“白在(7,7)”是两个不同事件')

# ---------------- 5. 72 条线 ----------------
title('5. LINES：全盘 72 条线')
print('总条数：', len(LINES))
print('第 0 条（第 0 行）：', LINES[0][:5], '...')
print('第 15 条（第 0 列）：', LINES[15][:5], '...')
print()
print('经过 (7,7) 的 4 条线（线号, 在这条线上的位置）：')
print('  CELL_LINES[(7,7)] =', CELL_LINES[(7, 7)])

# ---------------- 6. 一条线的内容与分值 ----------------
title('6. line_vals / line_sc / total 是什么关系')
b = Board()
b.make_move(7, 7)
b.make_move(0, 0)

li, pos = CELL_LINES[(7, 7)][0]      # (7,7) 所在的第一条线
print(f'取线号 {li}（这是第 7 行），(7,7) 在其中的位置 {pos}')
print('这条线的内容 line_vals[li] =', b.line_vals[li])
print('这条线的分值 line_sc[li]   =', b.line_sc[li], '  ← [黑分, 白分]')
print('全盘总分 total            =', b.total, '  ← [黑总分, 白总分]')

b.make_move(7, 8)   # 黑再下一子，和 (7,7) 连成两子
print()
print('黑再走 (7,8) 后：')
print('  同一条线内容 line_vals[li] =', b.line_vals[li])
print('  同一条线分值 line_sc[li]   =', b.line_sc[li])
print('  全盘总分 total            =', b.total)
print()
print('观察：只有经过 (7,8) 的那几条线被重算，其余线一个数都没动。')

# ---------------- 7. 一次落子的完整流程 ----------------
title('7. 落子时到底发生了什么（按代码顺序）')
b = Board()
print('落子前：side =', b.side, '，moves 数量 =', len(b.moves), '，total =', b.total)
b.make_move(7, 7)
print('落子后：side =', b.side, '，moves 数量 =', len(b.moves), '，total =', b.total)
print('moves 栈顶：', b.moves[-1], ' ← (行, 列, 颜色)')

print()
print('全部演示结束。')
