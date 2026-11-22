import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board, BLACK, WHITE, EMPTY
from engine import GomokuAI

# 模拟：人类走 H8，AI 应，再人类走 G8，AI 应 —— 验证默认参数能开局
board = Board()
ai = GomokuAI(time_limit=1.0, max_depth=8)
ai.reset()

board.make_move(7, 7)  # 人走 H8
m = ai.decide(board)
print(f"AI response 1: {m} | {ai.stats_summary()}")
board.make_move(*m)

board.make_move(7, 8)  # 人走 I8
m = ai.decide(board)
print(f"AI response 2: {m} | {ai.stats_summary()}")
board.make_move(*m)

print("Default-config startup test PASSED.")
