"""
AI 引擎封装：主决策入口

决策流程（按顺序，命中即返回）：
1. 立即胜（己方一步成五）
2. 立即堵（对手一步成五）
3. VCF 连续冲四求证（仅进阶/不可能）
4. VCT 双威胁检测（仅进阶/不可能）
5. 防守：对手活三 → 封堵（仅进阶/不可能）
6. 迭代加深 Alpha-Beta 搜索
7. 难度弱化：按 blunder 概率从前几名随机选一个（普通难度用）

三档难度（LEVELS）：
  normal      普通人约 60% 胜率 —— 浅搜索 + 关闭战术 + 随机失误
  advanced    普通人约 30% 胜率 —— 中等搜索 + 全战术
  impossible  尽最大努力取胜      —— 深搜索 + 长时限 + 全战术
"""

import random
import time
from board import EMPTY, BLACK, WHITE
from movegen import (find_winning_move, find_blocking_moves, ordered_moves,
                     generate_candidates)
from search import iterative_deepening, reset_stats, tt, TTEntry, TT_SIZE
from vcf import find_vcf, vct_check
from evaluate import open_four_points, point_value

# 难度配置
LEVELS = {
    'normal': {
        'name': '普通',
        'depth': 3,          # 浅搜索（2~3 层）
        'time': 0.15,
        'vcf': False,
        'vct': False,
        'defense': False,    # 不主动防活三
        'blunder': 0.15,     # 15% 概率不选最优，从前 5 名里随机
        'topn': 5,
        'cands': 10,
    },
    'advanced': {
        'name': '进阶',
        'depth': 6,
        'time': 0.95,
        'vcf': True,
        'vct': True,
        'defense': True,
        'blunder': 0.06,
        'topn': 3,
        'cands': 16,
        'counter_vct': False,
    },
    'impossible': {
        'name': '不可能',
        'depth': 12,
        'time': 3.00,
        'vcf': True,
        'vct': True,
        'defense': True,
        'blunder': 0.0,
        'topn': 1,
        'cands': 22,
        'counter_vct': True,
    },
}

LEVEL_KEYS = ['normal', 'advanced', 'impossible']


class GomokuAI:
    """五子棋 AI 引擎

    构造方式（两种都支持）：
        GomokuAI(level='advanced')                       # 按难度档位（推荐）
        GomokuAI(time_limit=1.0, max_depth=8)            # 直接指定参数（兼容旧代码）
    同时给 time_limit/max_depth 时，它们会覆盖难度档位里的对应值。
    """

    def __init__(self, level='advanced', rng_seed=None,
                 time_limit=None, max_depth=None):
        self.level = level if level in LEVELS else 'advanced'
        self.rng = random.Random(rng_seed)
        # 显式指定的参数优先于档位默认值
        self._override_time = time_limit
        self._override_depth = max_depth
        self.last_stats = {}
        self._apply_level()

    # ---- 难度 ----
    def set_level(self, level):
        if level in LEVELS:
            self.level = level
            self._apply_level()
            return True
        return False

    def _apply_level(self):
        cfg = LEVELS[self.level]
        self.max_depth = self._override_depth if self._override_depth is not None else cfg['depth']
        self.time_limit = self._override_time if self._override_time is not None else cfg['time']
        self.use_vcf = cfg['vcf']
        self.use_vct = cfg['vct']
        self.use_defense = cfg['defense']
        self.blunder = cfg['blunder']
        self.topn = cfg['topn']
        self.max_cands = cfg['cands']
        self.counter_vct = cfg.get('counter_vct', False)

    @property
    def level_name(self):
        return LEVELS[self.level]['name']

    def reset(self):
        """重置状态（新对局开始时调用）"""
        global tt
        tt = [TTEntry() for _ in range(TT_SIZE)]
        self.last_stats = {}

    # ---- 主决策 ----
    def decide(self, board):
        """
        根据当前局面返回 (row, col)。
        """
        import search as srch

        self.last_stats = {}
        t0 = time.time()
        side = board.side

        # ---- 1. 立即胜 ----
        wm = find_winning_move(board)
        if wm:
            self.last_stats = {'reason': 'immediate_win', 'move': wm,
                               'time': time.time() - t0, 'depth': 0, 'nodes': 0}
            return wm

        # ---- 2. 立即堵 ----
        blocks = find_blocking_moves(board)
        if len(blocks) == 1:
            self.last_stats = {'reason': 'block', 'move': blocks[0],
                               'time': time.time() - t0, 'depth': 0, 'nodes': 0}
            return blocks[0]
        if len(blocks) > 1:
            # 多个成五点：选一个能同时形成自己威胁的，否则随便堵一个
            best, bestv = blocks[0], -1
            for p in blocks:
                v = point_value(board.grid, p[0], p[1], side)
                if v > bestv:
                    best, bestv = p, v
            self.last_stats = {'reason': 'block_multi', 'move': best,
                               'time': time.time() - t0, 'depth': 0, 'nodes': 0}
            return best

        cands = generate_candidates(board)

        # ---- 3. VCF ----
        if self.use_vcf:
            ok, vcf_path = find_vcf(board, side)
            if ok and len(vcf_path) > 0:
                self.last_stats = {'reason': 'vcf', 'move': vcf_path[0],
                                   'time': time.time() - t0,
                                   'vcf_len': len(vcf_path)}
                return vcf_path[0]

        # ---- 4. VCT（一手造出双威胁 = 必胜）----
        if self.use_vct:
            ok, vt_move = vct_check(board, side)
            if ok:
                self.last_stats = {'reason': 'vct', 'move': vt_move,
                                   'time': time.time() - t0}
                return vt_move

        # ---- 5. 防守 ----
        opp = board.opponent()
        if self.use_defense:
            # 5a. 对手有一手双威胁（四三/双三/四四）时，抢先占掉那个点
            if self.counter_vct:
                ok_o, mv_o = vct_check(board, opp)
                if ok_o and board.grid[mv_o[0]][mv_o[1]] == EMPTY:
                    self.last_stats = {'reason': 'block_double_threat', 'move': mv_o,
                                       'time': time.time() - t0}
                    return mv_o

            # 5b. 对手已有活三（下一步能成活四），我方又无四可抢先 → 堵
            my_four = open_four_points(board.grid, side, cands)
            if not my_four:
                danger = open_four_points(board.grid, opp, cands)
                if danger:
                    best = max(danger, key=lambda rc: point_value(board.grid, rc[0], rc[1], side))
                    self.last_stats = {'reason': 'defend_open3', 'move': best,
                                       'time': time.time() - t0,
                                       'threats': len(danger)}
                    return best

        # ---- 6. 搜索 ----
        reset_stats()
        srch.start_time = time.time()
        srch.time_limit = self.time_limit

        best_move, score, depth = iterative_deepening(
            board, self.max_depth, self.time_limit)

        # ---- 7. 难度弱化：故意失误 ----
        if self.blunder > 0 and self.topn > 1 and self.rng.random() < self.blunder:
            pool = ordered_moves(board, max_moves=self.topn, light=False)
            # 排除立即送死的点（保留一点"像人"的合理性）
            pool = [m for m in pool if m != best_move]
            if pool:
                best_move = self.rng.choice(pool)
                self.last_stats = {'reason': 'blunder', 'move': best_move,
                                   'score': score, 'depth': depth,
                                   'nodes': srch.nodes_searched,
                                   'tt_hits': srch.tt_hits,
                                   'time': time.time() - t0}
                return best_move

        if best_move is None:
            moves = ordered_moves(board, 1)
            best_move = moves[0] if moves else (7, 7)

        self.last_stats = {
            'reason': 'search',
            'move': best_move,
            'score': score,
            'depth': depth,
            'nodes': srch.nodes_searched,
            'tt_hits': srch.tt_hits,
            'time': time.time() - t0,
        }
        return best_move

    def stats_summary(self):
        """返回上一步的统计摘要字符串"""
        if not self.last_stats:
            return 'N/A'
        s = self.last_stats
        parts = [f"reason={s.get('reason', '?')}"]
        if 'depth' in s:
            parts.append(f"depth={s['depth']}")
        if 'score' in s:
            parts.append(f"score={s.get('score', 0):+d}")
        if 'nodes' in s:
            parts.append(f"nodes={s['nodes']}")
        if 'tt_hits' in s:
            parts.append(f"TT_hits={s['tt_hits']}")
        if 'time' in s:
            parts.append(f"time={s['time']*1000:.0f}ms")
        if 'vcf_len' in s:
            parts.append(f"VCF_len={s['vcf_len']}")
        if 'threats' in s:
            parts.append(f"threats={s['threats']}")
        return '  '.join(parts)
