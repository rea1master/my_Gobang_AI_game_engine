"""
五子棋 AI —— 图形界面后端（纯标准库，零依赖）

用 Python 内置 http.server 提供网页与 AI API，浏览器里鼠标点击落子。
运行：python gomoku/web.py   （会自动打开浏览器）

接口：
  GET  /                    -> 前端页面
  GET  /api/new             -> 开始新对局
  GET  /api/state           -> 当前局面状态
  POST /api/move            -> 玩家落子 {r,c}，若 AI 执白会自动回应
  POST /api/ai              -> 让 AI 走当前一步（换边/代走用）
  POST /api/undo            -> 悔棋（撤销玩家+AI 各一步）
  POST /api/set             -> 设置（先后手、AI 深度、时限）
"""

import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# 保证 gomoku 模块可导入（VSCode 直接运行本文件也可）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from board import Board, BLACK, WHITE, EMPTY, SIZE
from engine import GomokuAI, LEVELS


WEB_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- 全局对局状态 ----
state = {
    'board': Board(),
    'ai': GomokuAI(level='advanced'),
    'human_color': BLACK,     # 玩家执黑
    'game_over': False,
    'winner': EMPTY,
    'history': [],            # 落子历史 [(r,c,color), ...] 用于前端重放
}

LOCK = threading.Lock()


# ============================================================
#  AI 观战模式：两个 AI 互相对弈，按「继续」才走一子
# ============================================================

duel = {
    'board': Board(),
    'black': GomokuAI(level='advanced'),
    'white': GomokuAI(level='normal'),
    'lb': 'advanced',
    'lw': 'normal',
    'over': False,
    'winner': EMPTY,
    'log': [],          # 每手记录
}


def duel_new(lb='advanced', lw='normal'):
    """开一局新的 AI 对 AI"""
    lb = lb if lb in LEVELS else 'advanced'
    lw = lw if lw in LEVELS else 'normal'
    duel['board'] = Board()
    duel['black'] = GomokuAI(level=lb)
    duel['black'].reset()
    duel['white'] = GomokuAI(level=lw)
    duel['white'].reset()
    duel['lb'], duel['lw'] = lb, lw
    duel['over'] = False
    duel['winner'] = EMPTY
    duel['log'] = []


def duel_step():
    """让当前该走的一方走一子；返回是否真的走了"""
    b = duel['board']
    if duel['over']:
        return False
    color = b.side
    ai = duel['black'] if color == BLACK else duel['white']
    r, c = ai.decide(b)
    st = dict(ai.last_stats)
    b.make_move(r, c)

    w = b.check_win()
    if w != EMPTY:
        duel['over'] = True
        duel['winner'] = w
    elif b.is_full():
        duel['over'] = True
        duel['winner'] = EMPTY

    duel['log'].append({
        'r': r, 'c': c, 'color': color,
        'reason': st.get('reason'),
        'depth': st.get('depth'),
        'nodes': st.get('nodes'),
        'time': st.get('time'),
        'score': st.get('score'),
    })
    return True


def duel_state():
    b = duel['board']
    return {
        'grid': [[b.get(r, c) for c in range(SIZE)] for r in range(SIZE)],
        'side': b.side,
        'move_count': b.move_count,
        'over': duel['over'],
        'winner': duel['winner'],
        'levels': {'black': duel['lb'], 'white': duel['lw']},
        'level_names': {'black': LEVELS[duel['lb']]['name'],
                        'white': LEVELS[duel['lw']]['name']},
        'last': duel['log'][-1] if duel['log'] else None,
    }


def reset_game():
    state['board'] = Board()
    state['ai'].reset()
    state['game_over'] = False
    state['winner'] = EMPTY
    state['history'] = []


def board_to_json(b):
    """把棋盘转成前端可用的结构"""
    grid = [[b.get(r, c) for c in range(SIZE)] for r in range(SIZE)]
    return {
        'grid': grid,
        'side': b.side,
        'move_count': b.move_count,
        'game_over': state['game_over'],
        'winner': state['winner'],
        'human_color': state['human_color'],
        'difficulty': state['ai'].level,
        'difficulty_name': state['ai'].level_name,
        'last_move': list(b.moves[-1][:2]) if b.moves else None,
        'stats': state['ai'].last_stats,
    }


def do_human_move(r, c):
    """玩家落子；返回是否触发游戏结束"""
    b = state['board']
    if state['game_over']:
        return False
    if b.side != state['human_color']:
        return False
    if not (0 <= r < SIZE and 0 <= c < SIZE):
        return False
    if b.get(r, c) != EMPTY:
        return False

    b.make_move(r, c)
    state['history'].append((r, c, board_color_of_last(b)))
    return True


def board_color_of_last(b):
    """返回上一步落子颜色（用于记录）"""
    if not b.moves:
        return EMPTY
    return b.moves[-1][2]


def ai_move():
    """让 AI 走一步；返回是否结束"""
    b = state['board']
    if state['game_over']:
        return
    r, c = state['ai'].decide(b)
    b.make_move(r, c)
    state['history'].append((r, c, b.moves[-1][2]))


def update_outcome():
    """更新 game_over / winner"""
    b = state['board']
    w = b.check_win()
    if w != EMPTY:
        state['game_over'] = True
        state['winner'] = w
    elif b.is_full():
        state['game_over'] = True
        state['winner'] = EMPTY


def maybe_ai_reply():
    """如果当前轮到 AI，则 AI 走一步并更新结果"""
    b = state['board']
    if not state['game_over'] and b.side != state['human_color']:
        ai_move()
        update_outcome()


# ---- HTTP 处理器 ----

class Server(ThreadingHTTPServer):
    # Windows 下 SO_REUSEADDR 会允许两个进程抢同一端口（请求被随机分派）。
    # 关掉它，端口被占时直接报错，让 main() 顺延到下一个端口。
    allow_reuse_address = False
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # 静默

    # ---- 工具 ----
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path):
        full = os.path.join(WEB_DIR, path)
        if not os.path.exists(full):
            self.send_error(404)
            return
        with open(full, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {}

    # ---- 路由 ----
    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path

        if p == '/' or p == '/index.html':
            self._send_html('web/index.html')
        elif p == '/duel' or p == '/duel.html':
            self._send_html('web/duel.html')
        elif p == '/api/new':
            with LOCK:
                reset_game()
                self._send_json({'ok': True, 'state': board_to_json(state['board'])})
        elif p == '/api/state':
            with LOCK:
                self._send_json({'ok': True, 'state': board_to_json(state['board'])})
        elif p == '/api/duel/state':
            with LOCK:
                self._send_json({'ok': True, 'state': duel_state()})
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        p = parsed.path

        if p == '/api/duel/new':
            # 开新的一局 AI 对战：{black: 档位, white: 档位}
            with LOCK:
                data = self._read_body()
                duel_new(data.get('black', 'advanced'), data.get('white', 'normal'))
                self._send_json({'ok': True, 'state': duel_state()})

        elif p == '/api/duel/step':
            # 按一次「继续」→ 只走一子
            with LOCK:
                moved = duel_step()
                self._send_json({'ok': moved, 'state': duel_state()})

        elif p == '/api/move':
            # 只落玩家的子，立即返回（前端先显示黑棋，再单独请求 AI 思考）
            with LOCK:
                data = self._read_body()
                r = data.get('r')
                c = data.get('c')
                ok = do_human_move(r, c)
                if ok:
                    update_outcome()
                self._send_json({'ok': ok, 'state': board_to_json(state['board'])})

        elif p == '/api/ai':
            # 让 AI 想一步并落子（玩家先看到自己的子，再等这一手返回）
            with LOCK:
                moved = False
                if not state['game_over'] and state['board'].side != state['human_color']:
                    ai_move()
                    update_outcome()
                    moved = True
                self._send_json({'ok': True, 'moved': moved,
                                 'state': board_to_json(state['board'])})

        elif p == '/api/undo':
            with LOCK:
                b = state['board']
                # 悔棋语义：撤销最近一轮（玩家一手 + AI 一手），回到玩家落子前的状态
                # 若当前轮到玩家（side==human_color），说明 AI 刚走完 → 撤 AI + 玩家共 2 步
                # 若当前轮到 AI（side!=human_color），说明玩家刚走完、AI 还没应 → 只撤玩家 1 步
                if b.side == state['human_color']:
                    # AI 已应，撤两步
                    steps = min(2, len(b.moves))
                else:
                    # AI 未应，只撤玩家一步
                    steps = min(1, len(b.moves))
                for _ in range(steps):
                    b.unmake_move()
                    if state['history']:
                        state['history'].pop()
                state['game_over'] = False
                state['winner'] = EMPTY
                self._send_json({'ok': True, 'state': board_to_json(state['board'])})

        elif p == '/api/set':
            with LOCK:
                data = self._read_body()
                if 'human_color' in data:
                    state['human_color'] = int(data['human_color'])
                if 'difficulty' in data:
                    state['ai'].set_level(str(data['difficulty']))
                reset_game()
                state['ai'].reset()
                self._send_json({'ok': True, 'state': board_to_json(state['board'])})

        else:
            self.send_error(404)


def main():
    # 端口被占用时自动往后找（避免上次没退干净导致启动失败）
    # 也可以用命令行指定端口：python gomoku/web.py 8800
    start_port = 8765
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        start_port = int(sys.argv[1])

    httpd = None
    port = None
    for try_port in range(start_port, start_port + 25):
        try:
            httpd = Server(('127.0.0.1', try_port), Handler)
            port = try_port
            break
        except OSError:
            print(f'  端口 {try_port} 被占用，尝试下一个…')
            continue

    if httpd is None:
        print(f'  [错误] {start_port}-{start_port+24} 全部被占用，请先关掉旧的进程。')
        return

    url = f'http://127.0.0.1:{port}/'
    print('=' * 52)
    print('  五子棋 AI —— 图形界面已启动')
    print(f'  请在浏览器打开: {url}')
    print('  按 Ctrl+C 退出')
    print('=' * 52)
    sys.stdout.flush()

    # 自动打开浏览器
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n  已退出。')


if __name__ == '__main__':
    main()