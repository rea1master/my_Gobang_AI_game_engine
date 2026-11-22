"""
VCF / VCT 威胁空间搜索

VCF (Victory by Continuous Four)：只用冲四作为攻击手段，
对手每一步都只有唯一应手，构成构造性必胜证明（sound）。
"""

from board import SIZE, EMPTY, BLACK, WHITE
from evaluate import win_one_points
from movegen import generate_candidates

VCF_MAX_DEPTH = 12


def four_moves(board, color):
    """
    找出当前局面所有"落子后即成冲四/活四"的空点。
    返回 [(row, col, kind), ...]，kind = 'L4o' | 'L4s'
    """
    result = []
    for r, c in generate_candidates(board):
        board.grid[r][c] = color
        wps = win_one_points(board.grid, r, c, color)
        board.grid[r][c] = EMPTY
        if len(wps) >= 2:
            result.append((r, c, 'L4o'))
        elif len(wps) == 1:
            result.append((r, c, 'L4s'))
    return result


def vcf_search(board, color, depth):
    """
    VCF 递归搜索。
    返回 (True, [(r,c), ...]) 或 (False, [])。
    """
    if depth == 0:
        return False, []

    opp = WHITE if color == BLACK else BLACK
    fours = four_moves(board, color)

    for r, c, kind in fours:
        # 活四：直接必胜
        if kind == 'L4o':
            return True, [(r, c)]

        # 冲四：拿到唯一点
        board.grid[r][c] = color
        wps = win_one_points(board.grid, r, c, color)
        board.grid[r][c] = EMPTY
        if len(wps) != 1:
            continue
        qr, qc = list(wps)[0]

        # 落攻击 + 对手被迫防守
        board.grid[r][c] = color
        board.grid[qr][qc] = opp

        # 检查这一步之后是否下一步就直接赢
        can_win = False
        win_move = None
        for nr, nc in generate_candidates(board):
            board.grid[nr][nc] = color
            if board.has_five(nr, nc, color):
                board.grid[nr][nc] = EMPTY
                can_win = True
                win_move = (nr, nc)
                break
            board.grid[nr][nc] = EMPTY

        if can_win:
            board.grid[r][c] = EMPTY
            board.grid[qr][qc] = EMPTY
            return True, [(r, c), win_move]

        # 递归
        sub_ok, sub_path = vcf_search(board, color, depth - 1)
        board.grid[r][c] = EMPTY
        board.grid[qr][qc] = EMPTY

        if sub_ok:
            return True, [(r, c)] + sub_path

    return False, []


def find_vcf(board, color=None):
    """顶层 VCF 入口"""
    if color is None:
        color = board.side
    return vcf_search(board, color, VCF_MAX_DEPTH)


def vct_check(board, color):
    """
    简化 VCT：检查是否存在一个着法落子后形成双威胁（双三/四三/四四）。
    返回 (True, (r,c)) 或 (False, None)。
    """
    from evaluate import is_double_threat
    opp = WHITE if color == BLACK else BLACK

    for r, c in generate_candidates(board):
        if not is_double_threat(board.grid, r, c, color):
            continue
        # 确保对手无法反杀
        board.grid[r][c] = color
        blocked = False
        for nr, nc in generate_candidates(board):
            board.grid[nr][nc] = opp
            if board.has_five(nr, nc, opp):
                blocked = True
                board.grid[nr][nc] = EMPTY
                break
            board.grid[nr][nc] = EMPTY
        board.grid[r][c] = EMPTY
        if not blocked:
            return True, (r, c)

    return False, None