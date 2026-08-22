# -*- coding: utf-8 -*-
"""
SajetMES 密码管理器 + 一键自动登录
UI      : iOS 26 Liquid Glass (PySide6 / Qt6)
Author  : ICT-Andy
Version : 2.0.0
本软件仅供技术研究与学习交流使用，请勿用于任何商业或非法用途。
"""
import os
import sys
import json
import time
import hmac
import hashlib
import getpass
import platform
import subprocess
import traceback

# ============================================================
#  常量 / 路径（修复：固定应用数据目录，不再依赖 sys.argv[0]）
# ============================================================
APP_NAME = "SajetMES 密码管理器"
APP_SUBTITLE = "安全管理账号，一键登录 MES"
APP_VERSION = "2.0.0"
APP_AUTHOR = "ICT-Andy"


def get_app_data_dir() -> str:
    """稳定可靠的应用数据目录，兼容脚本运行 / PyInstaller onefile/onedir / 快捷方式。"""
    base = (os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or os.path.expanduser("~"))
    d = os.path.join(base, "SajetMESVault")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        # 极端情况下退回用户主目录
        d = os.path.join(os.path.expanduser("~"), "SajetMESVault")
        os.makedirs(d, exist_ok=True)
    return d


def resource_dir() -> str:
    """资源目录（图标随程序发布）。PyInstaller onefile 用 _MEIPASS。"""
    return getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.abspath(sys.argv[0])))


APP_DATA_DIR = get_app_data_dir()
VAULT_PATH = os.path.join(APP_DATA_DIR, "vault.dat")
CONFIG_PATH = os.path.join(APP_DATA_DIR, "config.json")
ICON_PATH = os.path.join(resource_dir(), "app.ico")

# 旧版本可能把文件写在程序运行目录，做一次兼容迁移
_LEGACY_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LEGACY_CONFIG = os.path.join(_LEGACY_DIR, "config.json")
LEGACY_VAULT = os.path.join(_LEGACY_DIR, "vault.dat")

print("[SajetVault] 数据目录 :", APP_DATA_DIR)
print("[SajetVault] 配置文件 :", CONFIG_PATH)
print("[SajetVault] 密码库   :", VAULT_PATH)


# ============================================================
#  加密核心（保持不变：机器绑定，免主密码）
# ============================================================
def _machine_key() -> str:
    raw = (platform.node() + "|" + getpass.getuser() + "|SajetVault").encode()
    return hashlib.sha256(raw).hexdigest()


def _derive(salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", _machine_key().encode(),
                               salt, 100_000, dklen=64)


def _keystream(key: bytes, nonce: bytes, n: int) -> bytes:
    out, c = bytearray(), 0
    while len(out) < n:
        out.extend(hmac.new(key, nonce + c.to_bytes(8, "big"),
                            hashlib.sha256).digest())
        c += 1
    return bytes(out[:n])


def encrypt(data: bytes) -> bytes:
    salt, nonce = os.urandom(16), os.urandom(16)
    k = _derive(salt)
    ek, mk = k[:32], k[32:]
    ct = bytes(a ^ b for a, b in zip(data, _keystream(ek, nonce, len(data))))
    mac = hmac.new(mk, salt + nonce + ct, hashlib.sha256).digest()
    return salt + nonce + mac + ct


def decrypt(blob: bytes) -> bytes:
    if len(blob) < 64:
        raise ValueError("文件损坏")
    salt, nonce, mac, ct = blob[:16], blob[16:32], blob[32:64], blob[64:]
    k = _derive(salt)
    ek, mk = k[:32], k[32:]
    if not hmac.compare_digest(mac,
                               hmac.new(mk, salt + nonce + ct,
                                        hashlib.sha256).digest()):
        raise ValueError("数据校验失败（文件可能被复制到其它机器或已损坏）")
    return bytes(a ^ b for a, b in zip(ct, _keystream(ek, nonce, len(ct))))


# ============================================================
#  账号库读写（保持格式；仅增加旧目录兼容迁移）
# ============================================================
def load_vault() -> list:
    path = VAULT_PATH
    if not os.path.exists(path) and os.path.exists(LEGACY_VAULT):
        path = LEGACY_VAULT  # 兼容读取旧位置（同机器可解密）
    if not os.path.exists(path):
        return []
    try:
        data = json.loads(decrypt(open(path, "rb").read()).decode())
        if path == LEGACY_VAULT:      # 迁移到新目录
            try:
                save_vault(data)
            except Exception:
                pass
        return data
    except Exception:
        return []


def save_vault(entries: list):
    tmp = VAULT_PATH + ".tmp"
    with open(tmp, "wb") as f:
        f.write(encrypt(json.dumps(entries, ensure_ascii=False).encode()))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, VAULT_PATH)


# ============================================================
#  配置读写（修复：固定目录 + 原子写 + 明确错误 + 旧配置兼容）
# ============================================================
def load_config() -> dict:
    cfg = {"mes_path": "", "proc_name": "SajetMES.exe", "auto_launch": True}
    src = None
    if os.path.exists(CONFIG_PATH):
        src = CONFIG_PATH
    elif os.path.exists(LEGACY_CONFIG):
        src = LEGACY_CONFIG
    if src:
        try:
            with open(src, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
            print("[SajetVault] 已读取配置:", src)
        except Exception as e:
            print("[SajetVault] 读取配置失败:", e)
    if src == LEGACY_CONFIG:           # 迁移旧配置到固定目录
        try:
            save_config(cfg)
            print("[SajetVault] 旧配置已迁移到:", CONFIG_PATH)
        except Exception as e:
            print("[SajetVault] 迁移配置失败:", e)
    return cfg


def save_config(cfg: dict):
    """原子写入，失败向上抛出，由 UI 层提示。"""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CONFIG_PATH)


# ============================================================
#  登录核心（完全保持不变）
# ============================================================
def find_login_window(proc_name: str):
    import ctypes
    import ctypes.wintypes as wt
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    HWND, LPARAM, DWORD = wt.HWND, wt.LPARAM, wt.DWORD
    WNDENUM = ctypes.WINFUNCTYPE(wt.BOOL, HWND, LPARAM)
    user32.EnumWindows.argtypes = [WNDENUM, LPARAM]
    user32.EnumChildWindows.argtypes = [HWND, WNDENUM, LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
    user32.GetWindowThreadProcessId.restype = DWORD
    user32.GetClassNameW.argtypes = [HWND, wt.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [HWND]
    PQLI = 0x1000
    kernel32.OpenProcess.argtypes = [DWORD, wt.BOOL, DWORD]
    kernel32.OpenProcess.restype = HWND
    kernel32.CloseHandle.argtypes = [HWND]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        HWND, DWORD, wt.LPWSTR, ctypes.POINTER(DWORD)]

    def cls(h):
        b = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, b, 256)
        return b.value

    def pname(pid):
        hp = kernel32.OpenProcess(PQLI, False, pid)
        if not hp:
            return ""
        try:
            sz = DWORD(1024)
            b = ctypes.create_unicode_buffer(1024)
            if kernel32.QueryFullProcessImageNameW(hp, 0, b, ctypes.byref(sz)):
                return os.path.basename(b.value)
            return ""
        finally:
            kernel32.CloseHandle(hp)

    found = [None]

    def on_top(h, _):
        if not user32.IsWindowVisible(h):
            return True
        pid = DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pname(pid.value).lower() != proc_name.lower():
            return True
        edits = []

        def oc(ch, _2):
            if "EDIT" in cls(ch).upper():
                edits.append(ch)
            return True
        user32.EnumChildWindows(h, WNDENUM(oc), 0)
        if len(edits) >= 2:
            found[0] = h
            return False
        return True

    user32.EnumWindows(WNDENUM(on_top), 0)
    return found[0]


def _login_api(win):
    import ctypes
    import ctypes.wintypes as wt
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, BM_CLICK = \
        0x000C, 0x000D, 0x000E, 0x00F5
    HWND, UINT, WPARAM, LPARAM = wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM
    LRESULT = wt.LPARAM
    SendStr = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM,
                                 ctypes.c_wchar_p)(("SendMessageW", user32))
    SendBuf = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM,
                                 ctypes.c_wchar_p)(("SendMessageW", user32))
    SendInt = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM,
                                 LPARAM)(("SendMessageW", user32))
    WNDENUM = ctypes.WINFUNCTYPE(wt.BOOL, HWND, LPARAM)
    user32.EnumChildWindows.argtypes = [HWND, WNDENUM, LPARAM]
    user32.GetClassNameW.argtypes = [HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.argtypes = [HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wt.RECT)]
    user32.SetForegroundWindow.argtypes = [HWND]

    def cls(h):
        b = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, b, 256)
        return b.value

    def wtext(h):
        b = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(h, b, 512)
        return b.value

    def top(h):
        r = wt.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        return r.top

    return (user32, SendStr, SendBuf, SendInt, WNDENUM, cls, wtext, top,
            WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, BM_CLICK)


def sajet_login(account, password, cfg) -> tuple:
    try:
        proc = cfg.get("proc_name", "SajetMES.exe")
        win = find_login_window(proc)

        # 没找到登录框 → 自动拉起 MES
        if not win:
            path = cfg.get("mes_path", "")
            if cfg.get("auto_launch", True) and path and os.path.exists(path):
                try:
                    subprocess.Popen([path], cwd=os.path.dirname(path))
                except Exception as e:
                    return False, f"启动 MES 失败：{e}"
                for _ in range(60):
                    time.sleep(0.5)
                    win = find_login_window(proc)
                    if win:
                        break
                if not win:
                    return False, "已启动 MES，但 30 秒内未检测到登录框"
            else:
                return False, ("未找到 MES 登录框。请先在『设置』里配置 "
                               "MES 程序路径，或手动打开登录框后再试。")

        import ctypes
        (user32, SendStr, SendBuf, SendInt, WNDENUM, cls, wtext, top,
         WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH, BM_CLICK) = _login_api(win)

        edits, btn = [], [None]

        def oc(ch, _):
            c = cls(ch).upper()
            if "EDIT" in c:
                edits.append((top(ch), ch))
            elif "BUTTON" in c and wtext(ch).strip().lower() == "login":
                btn[0] = ch
            return True
        user32.EnumChildWindows(win, WNDENUM(oc), 0)
        edits.sort()
        if len(edits) < 2:
            return False, f"输入框数量异常：{len(edits)}"

        acc_h, pwd_h = edits[0][1], edits[1][1]
        SendStr(acc_h, WM_SETTEXT, 0, account)
        time.sleep(0.15)
        SendStr(pwd_h, WM_SETTEXT, 0, password)
        time.sleep(0.15)

        n = SendInt(acc_h, WM_GETTEXTLENGTH, 0, 0)
        b = ctypes.create_unicode_buffer(int(n) + 1)
        SendBuf(acc_h, WM_GETTEXT, int(n) + 1, ctypes.cast(b, ctypes.c_wchar_p))
        if b.value != account:
            return False, "账号写入失败（WM_SETTEXT 被拦截）"

        if btn[0]:
            try:
                user32.SetForegroundWindow(win)
            except Exception:
                pass
            time.sleep(0.1)
            SendInt(btn[0], BM_CLICK, 0, 0)
            return True, "已填入账号密码并点击 Login"
        return True, "已填入账号密码（未找到 Login 按钮，请手动点）"
    except Exception:
        return False, "登录异常：\n" + traceback.format_exc()


# ============================================================
#  以下为全新 UI 层（PySide6 / Liquid Glass）
# ============================================================
from PySide6.QtCore import (Qt, QRectF, QRect, QPoint, QPointF, QSize, QTimer,
                            QByteArray, QPropertyAnimation, QEasingCurve,
                            Property, Signal, QEventLoop)
from PySide6.QtGui import (QPainter, QColor, QLinearGradient, QRadialGradient,
                           QBrush, QPen, QPainterPath, QFont, QIcon, QPixmap,
                           QFontMetrics)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                               QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QScrollArea, QLineEdit, QDialog,
                               QGraphicsDropShadowEffect, QGraphicsBlurEffect,
                               QFileDialog, QSizePolicy)
try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except Exception:
    _HAS_SVG = False

# ---------- 配色（Liquid Glass 亮色）----------
COL_TEXT = QColor("#1c1c1e")
COL_SUB = QColor("#6e6e73")
COL_ACCENT = QColor("#0a84ff")
COL_ACCENT_HI = QColor("#4aa3ff")
COL_DANGER = QColor("#ff453a")
COL_LINE = QColor(60, 60, 67, 40)
FONT_FAMILY = "Segoe UI"

# ---------- 线性图标（SF Symbols / Lucide 风格，非 Emoji）----------
_ICON_BODY = {
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4.5 20c0-4 3.5-6 7.5-6s7.5 2 7.5 6"/>',
    "key": '<circle cx="8" cy="15" r="4.2"/><path d="M11 12.2 20 3.2"/><path d="M17 6l2.4 2.4"/><path d="M14.6 8.4 17 10.8"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.1 5.1l2.1 2.1M16.8 16.8l2.1 2.1M18.9 5.1l-2.1 2.1M7.2 16.8l-2.1 2.1"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 7.6v.2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "pencil": '<path d="M4 20l4-1L19 8a2 2 0 0 0-3-3L5 16l-1 4z"/><path d="M14.5 6.5l3 3"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V4.5h6V7"/><path d="M6.5 7l1 12.5h9l1-12.5"/><path d="M10 10.5v6M14 10.5v6"/>',
    "login": '<path d="M14 4h3.5A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5H14"/><path d="M4 12h11"/><path d="M11 8l4 4-4 4"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 6.5"/>',
    "chevron": '<path d="M9.5 6l6 6-6 6"/>',
    "folder": '<path d="M3 7.5A2 2 0 0 1 5 5.5h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "shield": '<path d="M12 3l7.5 3v5.5c0 4.5-3.2 8-7.5 9.5-4.3-1.5-7.5-5-7.5-9.5V6z"/>',
}


def icon_pixmap(name: str, color: QColor, size: int = 22) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    body = _ICON_BODY.get(name, "")
    if _HAS_SVG and body:
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
               f'fill="none" stroke="{color.name()}" stroke-width="1.9" '
               f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
        r = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        r.render(p, QRectF(0, 0, size, size))
        p.end()
    return pm


def add_shadow(widget, blur=40, dy=14, alpha=55):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(20, 30, 70, alpha))
    widget.setGraphicsEffect(eff)
    return eff


# ============================================================
#  背景层：柔和渐变 + 多个模糊彩色光团
# ============================================================
class GlassBackground(QWidget):
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        # 主渐变
        g = QLinearGradient(0, 0, w, h)
        g.setColorAt(0.0, QColor("#eef1f8"))
        g.setColorAt(0.5, QColor("#e8edf6"))
        g.setColorAt(1.0, QColor("#e6ecf4"))
        p.fillRect(self.rect(), QBrush(g))
        # 柔和彩色光团（径向渐变本身即柔和，模拟 blur 光晕）
        orbs = [
            (w * 0.16, h * 0.14, max(w, h) * 0.45, QColor(120, 170, 255, 90)),
            (w * 0.92, h * 0.10, max(w, h) * 0.40, QColor(190, 150, 255, 80)),
            (w * 0.85, h * 0.90, max(w, h) * 0.50, QColor(255, 170, 210, 70)),
            (w * 0.10, h * 0.92, max(w, h) * 0.42, QColor(150, 225, 255, 75)),
        ]
        for cx, cy, rad, col in orbs:
            rg = QRadialGradient(cx, cy, rad)
            rg.setColorAt(0.0, col)
            transparent = QColor(col)
            transparent.setAlpha(0)
            rg.setColorAt(1.0, transparent)
            p.fillRect(self.rect(), QBrush(rg))
        p.end()


# ============================================================
#  玻璃面板（第一/第二层）：半透明 + 高光边 + 圆角
# ============================================================
class GlassPanel(QWidget):
    def __init__(self, parent=None, radius=26, fill_alpha=150, tint=None):
        super().__init__(parent)
        self._radius = radius
        self._alpha = fill_alpha
        self._tint = tint or QColor(255, 255, 255)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)
        # 玻璃主体（半透明，透出背景色）
        base = QColor(self._tint)
        base.setAlpha(self._alpha)
        # 顶部到底部轻微渐变，增加体积感
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        top = QColor(255, 255, 255, min(255, self._alpha + 40))
        bot = QColor(self._tint.red(), self._tint.green(), self._tint.blue(),
                     max(0, self._alpha - 20))
        g.setColorAt(0.0, top)
        g.setColorAt(1.0, bot)
        p.fillPath(path, QBrush(g))
        # 高光边缘（顶部亮，整体细描边）
        p.setPen(QPen(QColor(255, 255, 255, 170), 1.4))
        p.drawPath(path)
        # 顶部内高光弧
        hi = QPainterPath()
        hr = QRectF(r.left() + 6, r.top() + 2, r.width() - 12, r.height() * 0.5)
        hi.addRoundedRect(hr, self._radius, self._radius)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
        p.drawLine(QPointF(r.left() + self._radius, r.top() + 1.5),
                   QPointF(r.right() - self._radius, r.top() + 1.5))
        p.end()


# ============================================================
#  导航按钮（左侧玻璃侧栏内）：hover / 选中 半透明高亮
# ============================================================
class NavButton(QWidget):
    clicked = Signal(str)

    def __init__(self, key, icon, text, parent=None):
        super().__init__(parent)
        self.key = key
        self.icon = icon
        self.text = text
        self.active = False
        self._hover = 0.0
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"hover", self)
        self._anim.setDuration(160)

    def getHover(self):
        return self._hover

    def setHover(self, v):
        self._hover = v
        self.update()

    hover = Property(float, getHover, setHover)

    def set_active(self, a):
        self.active = a
        self.update()

    def enterEvent(self, _):
        self._anim.stop(); self._anim.setEndValue(1.0); self._anim.start()

    def leaveEvent(self, _):
        self._anim.stop(); self._anim.setEndValue(0.0); self._anim.start()

    def mousePressEvent(self, _):
        self.clicked.emit(self.key)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(6, 4, self.width() - 12, self.height() - 8)
        if self.active:
            fill = QColor(COL_ACCENT.red(), COL_ACCENT.green(),
                          COL_ACCENT.blue(), 46)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor(255, 255, 255, 120), 1))
            p.drawRoundedRect(r, 14, 14)
        elif self._hover > 0.01:
            a = int(40 * self._hover)
            p.setBrush(QBrush(QColor(255, 255, 255, a)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 14, 14)
        col = COL_ACCENT if self.active else COL_TEXT
        pm = icon_pixmap(self.icon, col, 22)
        p.drawPixmap(int(r.left() + 12), int(r.center().y() - 11), pm)
        p.setPen(QPen(col))
        f = QFont(FONT_FAMILY, 11)
        f.setWeight(QFont.DemiBold if self.active else QFont.Normal)
        p.setFont(f)
        p.drawText(QRectF(r.left() + 44, r.top(), r.width() - 48, r.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.text)
        p.end()


# ============================================================
#  通用玻璃按钮（ghost / primary / danger）：hover 上浮 + 按下缩放
# ============================================================
class GlassButton(QWidget):
    clicked = Signal()

    def __init__(self, text, icon=None, kind="ghost", big=False, parent=None):
        super().__init__(parent)
        self.text = text
        self.icon = icon
        self.kind = kind
        self.big = big
        self._hover = 0.0
        self._press = 0.0
        h = 56 if big else 42
        self.setMinimumHeight(h)
        self.setCursor(Qt.PointingHandCursor)
        f = QFont(FONT_FAMILY, 12 if big else 10)
        f.setWeight(QFont.DemiBold)
        fm = QFontMetrics(f)
        base_w = fm.horizontalAdvance(text) + (36 if icon else 0) + 40
        if big:
            self.setMinimumWidth(max(base_w, 260))
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setFixedWidth(base_w)
        self._ah = QPropertyAnimation(self, b"hover", self); self._ah.setDuration(150)
        self._ap = QPropertyAnimation(self, b"press", self); self._ap.setDuration(90)
        if kind == "primary":
            add_shadow(self, blur=34, dy=10,
                       alpha=90 if big else 60)

    def getHover(self): return self._hover
    def setHover(self, v): self._hover = v; self.update()
    hover = Property(float, getHover, setHover)

    def getPress(self): return self._press
    def setPress(self, v): self._press = v; self.update()
    press = Property(float, getPress, setPress)

    def enterEvent(self, _):
        self._ah.stop(); self._ah.setEndValue(1.0); self._ah.start()

    def leaveEvent(self, _):
        self._ah.stop(); self._ah.setEndValue(0.0); self._ah.start()

    def mousePressEvent(self, _):
        self._ap.stop(); self._ap.setEndValue(1.0); self._ap.start()

    def mouseReleaseEvent(self, e):
        self._ap.stop(); self._ap.setEndValue(0.0); self._ap.start()
        if self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def _palette(self):
        if self.kind == "primary":
            base = QColor(COL_ACCENT)
            hov = QColor(COL_ACCENT_HI)
            fg = QColor("#ffffff")
        elif self.kind == "danger":
            base = QColor(255, 255, 255, 150)
            hov = QColor(COL_DANGER)
            fg = QColor(COL_DANGER)
        else:  # ghost
            base = QColor(255, 255, 255, 150)
            hov = QColor(255, 255, 255, 220)
            fg = QColor(COL_TEXT)
        return base, hov, fg

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        lift = (3.0 if self.kind == "primary" else 1.5) * self._hover
        inset = 1.0 + self._press * 1.5
        r = QRectF(inset, inset - lift, self.width() - inset * 2,
                   self.height() - inset * 2)
        base, hov, fg = self._palette()

        def mix(c1, c2, t):
            return QColor(int(c1.red() + (c2.red() - c1.red()) * t),
                          int(c1.green() + (c2.green() - c1.green()) * t),
                          int(c1.blue() + (c2.blue() - c1.blue()) * t),
                          int(c1.alpha() + (c2.alpha() - c1.alpha()) * t))
        fill = mix(base, hov, self._hover)
        radius = r.height() / 2
        if self.kind == "primary":
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0.0, mix(fill, QColor("#ffffff"), 0.18))
            g.setColorAt(1.0, fill)
            p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(QPen(QColor(255, 255, 255, 120), 1))
            p.drawRoundedRect(r, radius, radius)
        else:
            p.setBrush(QBrush(fill))
            border = COL_DANGER if (self.kind == "danger" and self._hover > 0.4) \
                else QColor(255, 255, 255, 180)
            p.setPen(QPen(border, 1.2))
            p.drawRoundedRect(r, radius, radius)
        # 危险按钮 hover 时文字变白
        if self.kind == "danger" and self._hover > 0.4:
            fg = QColor("#ffffff")
        f = QFont(FONT_FAMILY, 12 if self.big else 10)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        fm = QFontMetrics(f)
        tw = fm.horizontalAdvance(self.text)
        ic = 24 if self.big else 20
        gap = 10
        total = tw + (ic + gap if self.icon else 0)
        x = r.center().x() - total / 2
        cy = r.center().y()
        if self.icon:
            p.drawPixmap(int(x), int(cy - ic / 2),
                         icon_pixmap(self.icon, fg, ic))
            x += ic + gap
        p.setPen(QPen(fg))
        p.drawText(QRectF(x, r.top(), tw + 4, r.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.text)
        p.end()


# ============================================================
#  iOS 滑动开关
# ============================================================
class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self.setFixedSize(52, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def getPos(self): return self._pos
    def setPos(self, v): self._pos = v; self.update()
    pos = Property(float, getPos, setPos)

    def isChecked(self): return self._checked

    def setChecked(self, v):
        self._checked = bool(v)
        self._anim.stop()
        self._anim.setEndValue(1.0 if v else 0.0)
        self._anim.start()

    def mousePressEvent(self, _):
        self.setChecked(not self._checked)
        self.toggled.emit(self._checked)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        track = QRectF(1, 3, 50, 24)
        off = QColor(120, 120, 128, 90)
        on = QColor(52, 199, 89)
        col = QColor(int(off.red() + (on.red() - off.red()) * self._pos),
                     int(off.green() + (on.green() - off.green()) * self._pos),
                     int(off.blue() + (on.blue() - off.blue()) * self._pos))
        p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(track, 12, 12)
        kx = 4 + self._pos * 22
        p.setBrush(QBrush(QColor("#ffffff")))
        p.setPen(QPen(QColor(0, 0, 0, 25), 1))
        p.drawEllipse(QRectF(kx, 4, 22, 22))
        p.end()


# ============================================================
#  账号行（玻璃、hover、选中半透明蓝）
# ============================================================
class AccountRow(QWidget):
    picked = Signal(int)
    activated = Signal(int)

    def __init__(self, idx, entry, selected=False, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.entry = entry
        self.selected = selected
        self._hover = 0.0
        self.setMinimumHeight(72)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"hover", self)
        self._anim.setDuration(150)

    def getHover(self): return self._hover
    def setHover(self, v): self._hover = v; self.update()
    hover = Property(float, getHover, setHover)

    def enterEvent(self, _):
        self._anim.stop(); self._anim.setEndValue(1.0); self._anim.start()

    def leaveEvent(self, _):
        self._anim.stop(); self._anim.setEndValue(0.0); self._anim.start()

    def mousePressEvent(self, _):
        self.picked.emit(self.idx)

    def mouseDoubleClickEvent(self, _):
        self.activated.emit(self.idx)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(8, 5, self.width() - 16, self.height() - 10)
        if self.selected:
            fill = QColor(COL_ACCENT.red(), COL_ACCENT.green(),
                          COL_ACCENT.blue(), 40)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor(COL_ACCENT.red(), COL_ACCENT.green(),
                                 COL_ACCENT.blue(), 130), 1.2))
            p.drawRoundedRect(r, 16, 16)
        elif self._hover > 0.01:
            p.setBrush(QBrush(QColor(255, 255, 255, int(120 * self._hover))))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 16, 16)
        # 头像圆
        av = QRectF(r.left() + 12, r.center().y() - 21, 42, 42)
        g = QLinearGradient(av.topLeft(), av.bottomRight())
        g.setColorAt(0.0, COL_ACCENT_HI)
        g.setColorAt(1.0, COL_ACCENT)
        p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
        p.drawEllipse(av)
        letter = (self.entry.get("name") or "?")[0].upper()
        p.setPen(QPen(QColor("#ffffff")))
        pf = QFont(FONT_FAMILY, 15); pf.setWeight(QFont.DemiBold)
        p.setFont(pf)
        p.drawText(av, Qt.AlignCenter, letter)
        # 文本
        tx = av.right() + 14
        name = self.entry.get("name", "")
        sub = self.entry.get("account", "")
        if self.entry.get("note"):
            sub += "   ·   " + self.entry["note"]
        p.setPen(QPen(COL_TEXT))
        nf = QFont(FONT_FAMILY, 12); nf.setWeight(QFont.DemiBold)
        p.setFont(nf)
        p.drawText(QRectF(tx, r.top() + 12, r.width() - (tx - r.left()) - 44, 22),
                   Qt.AlignVCenter | Qt.AlignLeft, name)
        p.setPen(QPen(COL_SUB))
        p.setFont(QFont(FONT_FAMILY, 9))
        p.drawText(QRectF(tx, r.top() + 34, r.width() - (tx - r.left()) - 44, 20),
                   Qt.AlignVCenter | Qt.AlignLeft, sub)
        # 右侧状态图标
        ic = "check" if self.selected else "chevron"
        col = COL_ACCENT if self.selected else COL_SUB
        p.drawPixmap(int(r.right() - 30), int(r.center().y() - 10),
                     icon_pixmap(ic, col, 20))
        p.end()


# ============================================================
#  玻璃弹窗基类（frameless + translucent + 阴影 + 居中）
# ============================================================
class GlassDialog(QDialog):
    def __init__(self, parent, title, width=420):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self._margin = 26
        self._w = width
        self.card = GlassPanel(self, radius=24, fill_alpha=210)
        add_shadow(self.card, blur=60, dy=22, alpha=110)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(24, 20, 24, 22)
        self.body.setSpacing(14)
        # 顶部标题条
        top = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                        f"font-size:17px;font-weight:600;")
        top.addWidget(t)
        top.addStretch(1)
        close = GlassButton("", icon="close", kind="ghost")
        close.setFixedSize(34, 34)
        close.clicked.connect(self.reject)
        top.addWidget(close)
        self.body.addLayout(top)

    def resizeEvent(self, _):
        self.card.setGeometry(self._margin, self._margin,
                              self.width() - self._margin * 2,
                              self.height() - self._margin * 2)

    def showEvent(self, e):
        super().showEvent(e)
        if self.parent():
            g = self.parent().geometry()
            self.move(g.center().x() - self.width() // 2,
                      g.center().y() - self.height() // 2)


def styled_lineedit(text="", password=False, placeholder=""):
    le = QLineEdit(text)
    if password:
        le.setEchoMode(QLineEdit.Password)
    le.setPlaceholderText(placeholder)
    le.setMinimumHeight(42)
    le.setStyleSheet(f"""
        QLineEdit {{
            background: rgba(255,255,255,0.55);
            border: 1px solid rgba(120,130,150,0.35);
            border-radius: 12px;
            padding: 8px 14px;
            font-family: '{FONT_FAMILY}';
            font-size: 13px;
            color: {COL_TEXT.name()};
            selection-background-color: {COL_ACCENT.name()};
        }}
        QLineEdit:focus {{
            border: 1.6px solid {COL_ACCENT.name()};
            background: rgba(255,255,255,0.78);
        }}
    """)
    return le


class AccountDialog(GlassDialog):
    def __init__(self, parent, title, data=None):
        super().__init__(parent, title, width=440)
        data = data or {}
        self.result_data = None
        grid = QVBoxLayout(); grid.setSpacing(12)
        self.fields = {}
        specs = [("name", "名称", False), ("account", "账号", False),
                 ("password", "密码", True), ("note", "备注", False)]
        for key, label, pw in specs:
            lab = QLabel(label)
            lab.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                              f"font-size:11px;font-weight:600;")
            le = styled_lineedit(data.get(key, ""), password=pw,
                                 placeholder="请输入" + label)
            grid.addWidget(lab)
            grid.addWidget(le)
            self.fields[key] = le
        self.body.addLayout(grid)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = GlassButton("取消", kind="ghost"); cancel.clicked.connect(self.reject)
        save = GlassButton("保存", icon="check", kind="primary")
        save.clicked.connect(self._save)
        row.addWidget(cancel); row.addWidget(save)
        self.body.addLayout(row)
        self.resize(self._w, 400)

    def _save(self):
        if not self.fields["name"].text().strip():
            self.fields["name"].setFocus()
            return
        self.result_data = {k: v.text() for k, v in self.fields.items()}
        self.accept()


class ConfirmDialog(GlassDialog):
    def __init__(self, parent, title, message, ok_text="删除", danger=True):
        super().__init__(parent, title, width=400)
        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                          f"font-size:13px;")
        self.body.addWidget(msg)
        self.body.addSpacing(4)
        row = QHBoxLayout(); row.addStretch(1)
        cancel = GlassButton("取消", kind="ghost"); cancel.clicked.connect(self.reject)
        ok = GlassButton(ok_text, kind="danger" if danger else "primary")
        ok.clicked.connect(self.accept)
        row.addWidget(cancel); row.addWidget(ok)
        self.body.addLayout(row)
        self.resize(self._w, 200)


class MessageDialog(GlassDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent, title, width=460)
        box = QScrollArea(); box.setWidgetResizable(True)
        box.setFrameShape(QScrollArea.NoFrame)
        box.setStyleSheet("QScrollArea{background:transparent;}")
        inner = QLabel(message)
        inner.setWordWrap(True)
        inner.setTextInteractionFlags(Qt.TextSelectableByMouse)
        inner.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                            f"font-size:12px;background:transparent;")
        box.setWidget(inner)
        box.setMinimumHeight(90)
        box.setMaximumHeight(320)
        self.body.addWidget(box)
        row = QHBoxLayout(); row.addStretch(1)
        ok = GlassButton("好", icon="check", kind="primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        self.body.addLayout(row)
        self.resize(self._w, 240)


# ============================================================
#  Toast 轻提示
# ============================================================
class Toast(QWidget):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._text = text
        f = QFont(FONT_FAMILY, 10); f.setWeight(QFont.DemiBold)
        fm = QFontMetrics(f)
        w = fm.horizontalAdvance(text) + 44
        self.setFixedSize(max(w, 160), 44)
        add_shadow(self, blur=30, dy=8, alpha=80)
        self._opacity = 0.0
        self._fade = QPropertyAnimation(self, b"opacityv", self)
        self._fade.setDuration(200)

    def getOp(self): return self._opacity
    def setOp(self, v): self._opacity = v; self.update()
    opacityv = Property(float, getOp, setOp)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setOpacity(self._opacity)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        p.setBrush(QBrush(QColor(30, 32, 40, 230)))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setPen(QPen(QColor("#ffffff")))
        p.setFont(QFont(FONT_FAMILY, 10, QFont.DemiBold))
        p.drawText(r, Qt.AlignCenter, self._text)
        p.end()

    def popup(self):
        par = self.parent()
        self.move(par.width() // 2 - self.width() // 2, par.height() - 90)
        self.show(); self.raise_()
        self._fade.stop(); self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0); self._fade.start()
        QTimer.singleShot(2200, self._out)

    def _out(self):
        self._fade.stop(); self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0); self._fade.start()
        self._fade.finished.connect(self.deleteLater)


# ============================================================
#  主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1020, 700)
        self.setMinimumSize(920, 620)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        self.cfg = load_config()
        self.entries = load_vault()
        self.sel_idx = None
        self.row_widgets = []

        self.bg = GlassBackground()
        self.setCentralWidget(self.bg)

        # body 容器（模态时对其做模糊）
        self.body = QWidget(self.bg)
        root = QHBoxLayout(self.body)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(18)

        self._build_sidebar(root)
        self._build_content(root)

        # 背景 + body 填充
        outer = QVBoxLayout(self.bg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.body)

        # 模态遮罩
        self.dim = QWidget(self.bg)
        self.dim.setStyleSheet("background: rgba(10,15,30,0.32);")
        self.dim.hide()

        self._select_page("accounts")
        self._refresh_accounts()

    # ---- 侧边栏（第一层玻璃）----
    def _build_sidebar(self, root):
        self.sidebar = GlassPanel(radius=28, fill_alpha=130)
        self.sidebar.setFixedWidth(214)
        add_shadow(self.sidebar, blur=44, dy=16, alpha=60)
        lay = QVBoxLayout(self.sidebar)
        lay.setContentsMargins(14, 22, 14, 18)
        lay.setSpacing(6)

        # Logo
        logo_row = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(self._make_logo(44))
        logo_row.addWidget(logo)
        title_box = QVBoxLayout(); title_box.setSpacing(0)
        t1 = QLabel("SajetMES")
        t1.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                         f"font-size:14px;font-weight:700;")
        t2 = QLabel("密码管理器")
        t2.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                         f"font-size:10px;")
        title_box.addWidget(t1); title_box.addWidget(t2)
        logo_row.addLayout(title_box); logo_row.addStretch(1)
        lay.addLayout(logo_row)
        lay.addSpacing(18)

        self.nav = {}
        for key, icon, text in [("accounts", "user", "账号"),
                                ("settings", "settings", "设置"),
                                ("about", "info", "关于")]:
            b = NavButton(key, icon, text)
            b.clicked.connect(self._select_page)
            lay.addWidget(b)
            self.nav[key] = b
        lay.addStretch(1)
        sign = QLabel(f"© {APP_AUTHOR}   ·   v{APP_VERSION}")
        sign.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                           f"font-size:9px;")
        lay.addWidget(sign)
        root.addWidget(self.sidebar)

    def _make_logo(self, size):
        pm = QPixmap(size, size); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
        g = QLinearGradient(0, 0, size, size)
        g.setColorAt(0.0, COL_ACCENT_HI); g.setColorAt(1.0, COL_ACCENT)
        p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
        p.drawPixmap(int(size * 0.2), int(size * 0.2),
                     icon_pixmap("key", QColor("#ffffff"), int(size * 0.6)))
        p.end()
        return pm

    # ---- 内容区（第二层玻璃）----
    def _build_content(self, root):
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_accounts())   # 0
        self.stack.addWidget(self._page_settings())   # 1
        self.stack.addWidget(self._page_about())      # 2
        root.addWidget(self.stack, 1)

    def _select_page(self, key):
        idx = {"accounts": 0, "settings": 1, "about": 2}[key]
        self.stack.setCurrentIndex(idx)
        for k, b in self.nav.items():
            b.set_active(k == key)

    # ================= 账号页 =================
    def _page_accounts(self):
        page = GlassPanel(radius=26, fill_alpha=175)
        add_shadow(page, blur=48, dy=18, alpha=55)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 22, 26, 22)
        lay.setSpacing(14)

        # 顶部标题 + 账号数徽标
        head = QHBoxLayout()
        tbox = QVBoxLayout(); tbox.setSpacing(2)
        h1 = QLabel(APP_NAME)
        h1.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                         f"font-size:24px;font-weight:700;")
        h2 = QLabel(APP_SUBTITLE)
        h2.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                         f"font-size:11px;")
        tbox.addWidget(h1); tbox.addWidget(h2)
        head.addLayout(tbox); head.addStretch(1)
        self.count_badge = QLabel("")
        self.count_badge.setStyleSheet(
            f"color:{COL_ACCENT.name()};font-family:'{FONT_FAMILY}';"
            f"font-size:11px;font-weight:600;background:rgba(10,132,255,0.12);"
            f"padding:6px 14px;border-radius:12px;")
        head.addWidget(self.count_badge, 0, Qt.AlignVCenter)
        lay.addLayout(head)

        # 账号列表滚动区
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea{background:transparent;}
            QScrollBar:vertical{background:transparent;width:8px;margin:4px;}
            QScrollBar::handle:vertical{background:rgba(120,130,150,0.4);
                border-radius:4px;min-height:30px;}
            QScrollBar::add-line,QScrollBar::sub-line{height:0;}
        """)
        self.list_host = QWidget()
        self.list_host.setStyleSheet("background:transparent;")
        self.list_lay = QVBoxLayout(self.list_host)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(2)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(self.list_host)
        lay.addWidget(self.scroll, 1)

        # 操作按钮
        act = QHBoxLayout(); act.setSpacing(10)
        b_add = GlassButton("新增", icon="plus", kind="ghost")
        b_edit = GlassButton("编辑", icon="pencil", kind="ghost")
        b_del = GlassButton("删除", icon="trash", kind="danger")
        b_add.clicked.connect(self._add)
        b_edit.clicked.connect(self._edit)
        b_del.clicked.connect(self._del)
        act.addWidget(b_add); act.addWidget(b_edit); act.addWidget(b_del)
        act.addStretch(1)
        lay.addLayout(act)

        # 核心：一键登录
        self.login_btn = GlassButton("一键登录", icon="login",
                                     kind="primary", big=True)
        self.login_btn.clicked.connect(self._login)
        lay.addWidget(self.login_btn)

        self.acc_status = QLabel("就绪")
        self.acc_status.setStyleSheet(
            f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';font-size:10px;")
        self.acc_status.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.acc_status)
        return page

    def _refresh_accounts(self):
        # 清空旧行
        for w in self.row_widgets:
            self.list_lay.removeWidget(w)
            w.deleteLater()
        self.row_widgets = []
        # 移除 empty 占位
        if hasattr(self, "_empty") and self._empty is not None:
            self.list_lay.removeWidget(self._empty)
            self._empty.deleteLater()
            self._empty = None

        if not self.entries:
            self._empty = QLabel("暂无账号，点『新增』添加第一个")
            self._empty.setAlignment(Qt.AlignCenter)
            self._empty.setStyleSheet(
                f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                f"font-size:12px;padding:40px;")
            self.list_lay.insertWidget(0, self._empty)
        else:
            for idx, e in enumerate(self.entries):
                row = AccountRow(idx, e, selected=(idx == self.sel_idx))
                row.picked.connect(self._select_account)
                row.activated.connect(self._activate_account)
                self.list_lay.insertWidget(idx, row)
                self.row_widgets.append(row)
        self.count_badge.setText(f"共 {len(self.entries)} 个账号")

    def _select_account(self, idx):
        self.sel_idx = idx
        for i, row in enumerate(self.row_widgets):
            row.selected = (i == idx)
            row.update()

    def _activate_account(self, idx):
        self.sel_idx = idx
        self._select_account(idx)
        self._login()

    def _add(self):
        dlg = AccountDialog(self, "新增账号")
        if self._exec_modal(dlg) == QDialog.Accepted and dlg.result_data:
            self.entries.append(dlg.result_data)
            save_vault(self.entries)
            self.sel_idx = len(self.entries) - 1
            self._refresh_accounts()
            self._toast("账号已添加")

    def _edit(self):
        if self.sel_idx is None:
            self._toast("请先选中一个账号"); return
        dlg = AccountDialog(self, "编辑账号", self.entries[self.sel_idx])
        if self._exec_modal(dlg) == QDialog.Accepted and dlg.result_data:
            self.entries[self.sel_idx] = dlg.result_data
            save_vault(self.entries)
            self._refresh_accounts()
            self._toast("已保存修改")

    def _del(self):
        if self.sel_idx is None:
            self._toast("请先选中一个账号"); return
        name = self.entries[self.sel_idx].get("name", "")
        dlg = ConfirmDialog(self, "删除账号", f"确定要删除账号 “{name}” 吗？\n此操作不可恢复。")
        if self._exec_modal(dlg) == QDialog.Accepted:
            del self.entries[self.sel_idx]
            save_vault(self.entries)
            self.sel_idx = None
            self._refresh_accounts()
            self._toast("账号已删除")

    def _login(self):
        if self.sel_idx is None:
            self._toast("请先选中一个账号"); return
        e = self.entries[self.sel_idx]
        self.acc_status.setText("正在登录（未打开会自动启动 MES）…")
        QApplication.processEvents()
        ok, msg = sajet_login(e.get("account", ""), e.get("password", ""),
                              self.cfg)
        self.acc_status.setText(msg.splitlines()[0])
        if ok:
            self._toast(msg.splitlines()[0])
        else:
            self._exec_modal(MessageDialog(self, "登录失败", msg))

    # ================= 设置页 =================
    def _page_settings(self):
        wrap = QWidget()
        outer = QVBoxLayout(wrap)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        title = QLabel("设置")
        title.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                            f"font-size:24px;font-weight:700;")
        outer.addWidget(title)

        # 分组一：MES 程序
        g1 = GlassPanel(radius=22, fill_alpha=175)
        add_shadow(g1, blur=40, dy=14, alpha=45)
        l1 = QVBoxLayout(g1)
        l1.setContentsMargins(24, 20, 24, 20); l1.setSpacing(10)
        cap1 = QLabel("MES 程序")
        cap1.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                           f"font-size:14px;font-weight:600;")
        l1.addWidget(cap1)

        lab_p = QLabel("SajetMES.exe 路径")
        lab_p.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                            f"font-size:11px;font-weight:600;")
        l1.addWidget(lab_p)
        prow = QHBoxLayout(); prow.setSpacing(10)
        self.ed_path = styled_lineedit(self.cfg.get("mes_path", ""),
                                       placeholder="选择 SajetMES.exe 完整路径")
        self.ed_path.setCursorPosition(0)
        self.ed_path.setToolTip(self.cfg.get("mes_path", ""))
        browse = GlassButton("浏览", icon="folder", kind="ghost")
        browse.clicked.connect(self._browse)
        prow.addWidget(self.ed_path, 1); prow.addWidget(browse)
        l1.addLayout(prow)

        self.path_status = QLabel("")
        self.path_status.setStyleSheet(
            f"font-family:'{FONT_FAMILY}';font-size:11px;")
        l1.addWidget(self.path_status)
        outer.addWidget(g1)

        # 分组二：自动登录设置
        g2 = GlassPanel(radius=22, fill_alpha=175)
        add_shadow(g2, blur=40, dy=14, alpha=45)
        l2 = QVBoxLayout(g2)
        l2.setContentsMargins(24, 20, 24, 20); l2.setSpacing(12)
        cap2 = QLabel("自动登录设置")
        cap2.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                           f"font-size:14px;font-weight:600;")
        l2.addWidget(cap2)

        lab_proc = QLabel("进程名（用于查找登录窗口）")
        lab_proc.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                               f"font-size:11px;font-weight:600;")
        l2.addWidget(lab_proc)
        self.ed_proc = styled_lineedit(self.cfg.get("proc_name", "SajetMES.exe"))
        l2.addWidget(self.ed_proc)

        srow = QHBoxLayout()
        sl = QLabel("登录框未打开时自动启动 MES")
        sl.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                         f"font-size:12px;")
        srow.addWidget(sl); srow.addStretch(1)
        self.sw_auto = ToggleSwitch(self.cfg.get("auto_launch", True))
        srow.addWidget(self.sw_auto)
        l2.addLayout(srow)
        outer.addWidget(g2)

        # 保存按钮
        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save = GlassButton("保存设置", icon="check", kind="primary")
        save.clicked.connect(self._save_settings)
        save_row.addWidget(save)
        outer.addLayout(save_row)
        outer.addStretch(1)

        self._update_path_status()
        return wrap

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "选择 SajetMES 主程序", "",
            "可执行程序 (*.exe);;所有文件 (*.*)")
        if p:
            self.ed_path.setText(p)
            self.ed_path.setCursorPosition(0)
            self.ed_path.setToolTip(p)
            base = os.path.basename(p)
            if base:
                self.ed_proc.setText(base)
            self._update_path_status()

    def _update_path_status(self):
        path = self.ed_path.text().strip()
        if not path:
            self.path_status.setText("未选择程序")
            self.path_status.setStyleSheet(
                f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';font-size:11px;")
        elif os.path.exists(path):
            self.path_status.setText(f"✓ 已选择 {os.path.basename(path)}  ·  程序文件有效")
            self.path_status.setStyleSheet(
                f"color:#1a9e4b;font-family:'{FONT_FAMILY}';font-size:11px;font-weight:600;")
        else:
            self.path_status.setText("⚠ 路径无效：文件不存在")
            self.path_status.setStyleSheet(
                f"color:{COL_DANGER.name()};font-family:'{FONT_FAMILY}';font-size:11px;font-weight:600;")

    def _save_settings(self):
        new_cfg = {
            "mes_path": self.ed_path.text().strip(),
            "proc_name": self.ed_proc.text().strip() or "SajetMES.exe",
            "auto_launch": self.sw_auto.isChecked(),
        }
        try:
            save_config(new_cfg)          # 原子写入固定目录
            self.cfg = new_cfg            # 立即更新内存
            self._update_path_status()
            self._toast("设置已保存")
            # 简短显示保存位置
            self.path_status.setText(f"✓ 已保存到 {CONFIG_PATH}")
            self.path_status.setStyleSheet(
                f"color:#1a9e4b;font-family:'{FONT_FAMILY}';font-size:11px;font-weight:600;")
            QTimer.singleShot(3500, self._update_path_status)
        except Exception as e:
            self._exec_modal(MessageDialog(
                self, "保存失败",
                f"配置无法写入：\n{CONFIG_PATH}\n\n错误：{e}"))

    # ================= 关于页 =================
    def _page_about(self):
        wrap = QWidget()
        outer = QVBoxLayout(wrap)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(16)
        title = QLabel("关于")
        title.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                            f"font-size:24px;font-weight:700;")
        outer.addWidget(title)

        card = GlassPanel(radius=24, fill_alpha=185)
        add_shadow(card, blur=44, dy=16, alpha=50)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(30, 30, 30, 26); cl.setSpacing(8)
        cl.setAlignment(Qt.AlignHCenter)

        logo = QLabel(); logo.setPixmap(self._make_logo(76))
        logo.setAlignment(Qt.AlignHCenter)
        cl.addWidget(logo, 0, Qt.AlignHCenter)

        name = QLabel(APP_NAME)
        name.setAlignment(Qt.AlignHCenter)
        name.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                           f"font-size:16px;font-weight:700;")
        cl.addWidget(name)
        ver = QLabel(f"版本 {APP_VERSION}")
        ver.setAlignment(Qt.AlignHCenter)
        ver.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';font-size:11px;")
        cl.addWidget(ver)
        author = QLabel(f"作者：{APP_AUTHOR}")
        author.setAlignment(Qt.AlignHCenter)
        author.setStyleSheet(f"color:{COL_TEXT.name()};font-family:'{FONT_FAMILY}';"
                             f"font-size:12px;")
        cl.addWidget(author)
        cl.addSpacing(10)

        for line in [
            "本软件仅供技术研究与学习交流使用。",
            "严禁用于任何商业用途或违反相关规定的场景。",
            "使用本软件所产生的一切后果由使用者自行承担。",
            "账号数据经机器绑定加密，存储于本地。",
            f"数据目录：{APP_DATA_DIR}",
        ]:
            lb = QLabel(line); lb.setAlignment(Qt.AlignHCenter); lb.setWordWrap(True)
            lb.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';"
                             f"font-size:10px;")
            cl.addWidget(lb)
        cl.addSpacing(8)
        cp = QLabel(f"© 2026 {APP_AUTHOR}. All rights reserved.")
        cp.setAlignment(Qt.AlignHCenter)
        cp.setStyleSheet(f"color:{COL_SUB.name()};font-family:'{FONT_FAMILY}';font-size:9px;")
        cl.addWidget(cp)

        outer.addWidget(card)
        outer.addStretch(1)
        return wrap

    # ---- 模态：dim + 背景模糊 ----
    def _exec_modal(self, dialog):
        self.dim.setGeometry(self.bg.rect())
        self.dim.show(); self.dim.raise_()
        blur = None
        try:
            blur = QGraphicsBlurEffect(self.body)
            blur.setBlurRadius(14)
            self.body.setGraphicsEffect(blur)
        except Exception:
            blur = None
        try:
            result = dialog.exec()
        finally:
            self.dim.hide()
            if blur is not None:
                self.body.setGraphicsEffect(None)
        return result

    def _toast(self, text):
        Toast(self.bg, text).popup()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "dim"):
            self.dim.setGeometry(self.bg.rect())


# ============================================================
#  Windows 11 视觉增强（圆角，安全 try）
# ============================================================
def enable_win_effects(win):
    try:
        import ctypes
        hwnd = int(win.winId())
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        val = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont(FONT_FAMILY, 10))
    win = MainWindow()
    win.show()
    enable_win_effects(win)
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        # 兜底提示（避免静默崩溃）
        try:
            from PySide6.QtWidgets import QApplication as _QA, QMessageBox
            if _QA.instance() is None:
                _QA(sys.argv)
            QMessageBox.critical(None, "程序异常", traceback.format_exc())
        except Exception:
            input("程序异常，按回车退出…")
