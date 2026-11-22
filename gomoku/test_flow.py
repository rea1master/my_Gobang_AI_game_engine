import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import Board, BLACK, WHITE
from engine import GomokuAI

b = Board()
ai = GomokuAI(time_limit=0.5, max_depth=6)
ai.reset()

# 人类走天元
b.make_move(7, 7)
print("Human: (7,7)")

# AI 回应
m = ai.decide(b)
b.make_move(*m)
side_label = "BLACK" if b.side == WHITE else "WHITE"
print(f"AI ({side_label}): {m}  |  {ai.stats_summary()}")

# 再走几步
for i in range(4):
    m = ai.decide(b)
    b.make_move(*m)
    side_label = "BLACK" if b.side == WHITE else "WHITE"
    print(f"AI ({side_label}): {m}  |  {ai.stats_summary()}")
    w = b.check_win()
    if w:
        break

print(f"Final moves: {b.move_count}, winner: {w}")
print("Interactive flow test PASSED.")
