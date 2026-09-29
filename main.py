import sys
import os
import json
from datetime import datetime

from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QTime, QPropertyAnimation, QEasingCurve,
    QUrl, QSize, QRect
)
from PyQt6.QtGui import (
    QAction, QIcon, QPixmap, QPainter, QColor, QFont,
    QCursor, QGuiApplication
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QMenu, QSystemTrayIcon, QInputDialog,
    QFileDialog, QMessageBox, QGraphicsOpacityEffect, QFrame,
    QDialog, QTimeEdit, QListWidget, QListWidgetItem, QDialogButtonBox,
    QAbstractItemView, QSizePolicy
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


# ==================== 配置 ====================
def get_base_dir():
    """程序所在目录（打包后是 exe 所在目录，直接跑是 py 所在目录）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(get_base_dir(), "focus_timer_config.json")
DEFAULT_INTERVAL_MIN = 20
EDGE_TRIGGER = 8
HIDE_WIDTH = 6
EDGE_POLL_MS = 120

BG_NORMAL = "#2b2b2b"
BG_WARN   = "#c0392b"
FG_NORMAL = "#e0e0e0"
FG_WARN   = "#ffffff"

MENU_QSS = """
QMenu {
    background: #2b2b2b;
    color: #e0e0e0;
    border: 1px solid #444444;
    border-radius: 6px;
    padding: 4px;
    font-family: "Microsoft YaHei";
    font-size: 11px;
}
QMenu::item {
    padding: 5px 20px 5px 14px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #c0392b;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #444444;
    margin: 4px 8px;
}
"""


# ==================== 定点闹钟对话框 ====================
class FixedAlarmDialog(QDialog):
    """管理定点闹钟列表：增加、删除、修改"""

    def __init__(self, alarms, parent=None):
        super().__init__(parent)
        self.alarms = list(alarms)
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        self.setWindowTitle("定点闹钟")
        self.setModal(True)
        self.resize(380, 480)
        self.setStyleSheet("""
            QDialog {
                background: #2b2b2b;
            }
            QLabel {
                color: #e0e0e0;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QLabel#hint {
                color: #aaaaaa;
                font-family: "Microsoft YaHei";
                font-size: 10px;
                padding: 2px 0;
            }
            QListWidget {
                background: #1f1f1f;
                color: #e0e0e0;
                border: 1px solid #444444;
                border-radius: 8px;
                font-family: Consolas, "Microsoft YaHei";
                font-size: 18px;
                padding: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background: #c0392b;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background: #3a3a3a;
            }
            QTimeEdit {
                background: #1f1f1f;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 6px 10px;
                font-family: Consolas, "Microsoft YaHei";
                font-size: 20px;
                font-weight: bold;
                selection-background-color: #c0392b;
            }
            QTimeEdit::up-button, QTimeEdit::down-button {
                width: 20px;
                background: #3a3a3a;
                border: none;
            }
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {
                background: #555555;
            }
            QPushButton {
                background: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background: #555555;
                color: #ffffff;
            }
            QPushButton#primary {
                background: #c0392b;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#primary:hover {
                background: #e04a3a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("已设置的定点闹钟")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self._load_to_edit)
        layout.addWidget(self.list_widget, stretch=1)

        op_row = QHBoxLayout()
        op_row.setSpacing(8)

        btn_edit = QPushButton("更新选中")
        btn_edit.clicked.connect(self._edit_selected)
        op_row.addWidget(btn_edit)

        btn_del = QPushButton("删除选中")
        btn_del.clicked.connect(self._delete_selected)
        op_row.addWidget(btn_del)

        op_row.addStretch()
        layout.addLayout(op_row)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(QTime(9, 0, 0))
        self.time_edit.setWrapping(True)
        self.time_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        add_row.addWidget(self.time_edit, stretch=1)

        btn_add = QPushButton("添加")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._add_alarm)
        add_row.addWidget(btn_add)

        layout.addLayout(add_row)

        self.status_hint = QLabel(
            "操作：在下方输入时间点【添加】，或选中列表项后点【更新选中】"
        )
        self.status_hint.setObjectName("hint")
        self.status_hint.setWordWrap(True)
        layout.addWidget(self.status_hint)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _refresh_list(self):
        self.list_widget.clear()
        for t in sorted(self.alarms):
            item = QListWidgetItem(t)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_widget.addItem(item)

    def _load_to_edit(self, item):
        t = item.text()
        h, m, s = t.split(":")
        self.time_edit.setTime(QTime(int(h), int(m), int(s)))
        self.status_hint.setText(f"已载入 {t}，修改时间后点【更新选中】")

    def _add_alarm(self):
        t = self.time_edit.time().toString("HH:mm:ss")
        if t in self.alarms:
            QMessageBox.information(self, "提示", f"{t} 已经存在了")
            return
        self.alarms.append(t)
        self._refresh_list()
        self.status_hint.setText(f"已添加 {t}")

    def _edit_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先在列表里选一项")
            return
        old = item.text()
        new = self.time_edit.time().toString("HH:mm:ss")
        if new == old:
            self.status_hint.setText("时间没有变化，无需更新")
            return
        if new in self.alarms:
            QMessageBox.information(self, "提示", f"{new} 已经存在了")
            return
        idx = self.alarms.index(old)
        self.alarms[idx] = new
        self._refresh_list()
        self.status_hint.setText(f"已把 {old} 更新为 {new}")

    def _delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先在列表里选一项")
            return
        old = item.text()
        if old in self.alarms:
            self.alarms.remove(old)
        self._refresh_list()
        self.status_hint.setText(f"已删除 {old}")

    def get_alarms(self):
        return sorted(self.alarms)


# ==================== 主窗口 ====================
class FloatingTimer(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = self._load_config()
        self.interval = self.cfg.get("interval_min", DEFAULT_INTERVAL_MIN) * 60
        self.remaining = self.interval
        self.running = True
        self.overdue = 0
        self.muted = self.cfg.get("muted", False)
        self.sound_path = self.cfg.get("sound_path", "")
        self.fixed_alarms = self.cfg.get("fixed_alarms", [])
        self._last_fixed_fired = None

        self._drag_pos = None
        self._edge_side = None
        self._edge_hidden = False
        self._tray = None
        self._card = None
        self._pulse_anim = None
        self._menu_open = False

        self._init_audio()
        self._init_window()
        self._init_tray()
        self._restore_position()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        self._edge_timer = QTimer(self)
        self._edge_timer.timeout.connect(self._edge_poll)
        self._edge_timer.start(EDGE_POLL_MS)

    # ---------- 配置 ----------
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        self.cfg.update({
            "interval_min": self.interval // 60,
            "pos": [self.x(), self.y()],
            "muted": self.muted,
            "sound_path": self.sound_path,
            "fixed_alarms": self.fixed_alarms,
        })
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("保存配置失败:", e)

    def _restore_position(self):
        pos = self.cfg.get("pos")
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])
        else:
            self.move(60, 60)

    # ---------- 音频（统一走 QMediaPlayer） ----------
    def _init_audio(self):
        self._player = QMediaPlayer(self)
        self._audio_out = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_out)
        self._audio_out.setVolume(0.6)
        self._player.errorOccurred.connect(
            lambda err, msg: print(f"[MediaPlayer error] {err}: {msg}")
        )

    def _stop_all_audio(self):
        try:
            self._player.stop()
            self._player.setSource(QUrl())
        except Exception:
            pass

    def _is_playing(self) -> bool:
        try:
            return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        except Exception:
            return False

    def _play_sound(self):
        if self.muted:
            return
        self._stop_all_audio()
        if not (self.sound_path and os.path.exists(self.sound_path)):
            self._beep()
            return
        try:
            self._player.setSource(QUrl.fromLocalFile(self.sound_path))
            self._player.play()
            # 2 秒后检查是否真的在播，没播就退回 beep
            QTimer.singleShot(2000, self._check_player_playing)
        except Exception as e:
            print("播放失败:", e)
            self._beep()

    def _check_player_playing(self):
        """2 秒后检查；如果没在播，退回默认提示音"""
        if self.muted:
            return
        if not self._is_playing():
            print("[player] 未在播放，退回默认音")
            self._beep()

    def _beep(self):
        try:
            QApplication.beep()
        except Exception:
            pass

    # ---- 供卡片调用：音乐控制 ----
    def is_music_playing(self) -> bool:
        return self._is_playing()

    def toggle_music(self):
        if self._is_playing():
            self._player.pause()
        else:
            if self._player.source().isEmpty():
                self._play_sound()
            else:
                self._player.play()

    # ---------- 窗口 ----------
    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowTitle("Focus Timer")
        self.resize(200, 76)
        self.setStyleSheet(f"""
            QWidget#root {{
                background: {BG_NORMAL};
                border-radius: 12px;
            }}
            QLabel#time {{
                color: {FG_NORMAL};
                font-family: Consolas, "Microsoft YaHei";
                font-size: 26px;
                font-weight: bold;
            }}
            QLabel#status {{
                color: #888888;
                font-family: "Microsoft YaHei";
                font-size: 9px;
            }}
            QPushButton#ctrl {{
                background: #3a3a3a;
                color: #dddddd;
                border: none;
                border-radius: 5px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
                padding: 2px 6px;
                min-width: 26px;
            }}
            QPushButton#ctrl:hover {{
                background: #555555;
                color: #ffffff;
            }}
            QPushButton#ctrl::menu-indicator {{
                image: none;
                width: 0px;
            }}
        """)

        self.root_frame = QFrame(self)
        self.root_frame.setObjectName("root")
        self.root_frame.setGeometry(0, 0, self.width(), self.height())

        layout = QVBoxLayout(self.root_frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        self.time_label = QLabel("20:00")
        self.time_label.setObjectName("time")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label, stretch=1)

        self.status_label = QLabel("工作中 · 右键设置")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.btn_row = QWidget(self.root_frame)
        btn_layout = QHBoxLayout(self.btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)
        btn_layout.addStretch()

        b_pause = QPushButton("⏸")
        b_pause.setObjectName("ctrl")
        b_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        b_pause.clicked.connect(self.toggle)
        btn_layout.addWidget(b_pause)

        b_reset = QPushButton("⟳")
        b_reset.setObjectName("ctrl")
        b_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        b_reset.clicked.connect(self.reset)
        btn_layout.addWidget(b_reset)

        b_add = QPushButton("+N")
        b_add.setObjectName("ctrl")
        b_add.setCursor(Qt.CursorShape.PointingHandCursor)
        add_menu = QMenu(b_add)
        add_menu.setStyleSheet(MENU_QSS)
        for mins in (1, 5, 10, 15, 30):
            act = QAction(f"+{mins} 分钟", self)
            act.triggered.connect(lambda checked=False, m=mins: self.snooze(m))
            add_menu.addAction(act)
        add_menu.aboutToShow.connect(lambda: setattr(self, "_menu_open", True))
        add_menu.aboutToHide.connect(lambda: setattr(self, "_menu_open", False))
        b_add.setMenu(add_menu)
        btn_layout.addWidget(b_add)

        b_min = QPushButton("－")
        b_min.setObjectName("ctrl")
        b_min.setCursor(Qt.CursorShape.PointingHandCursor)
        b_min.clicked.connect(self.minimize_to_tray)
        btn_layout.addWidget(b_min)

        btn_layout.addStretch()

        self.btn_row.setVisible(False)
        layout.addWidget(self.btn_row)

    # ---------- 托盘 ----------
    def _init_tray(self):
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._make_tray_icon())
        self._tray.setToolTip("Focus Timer")

        menu = QMenu()
        menu.setStyleSheet(MENU_QSS)
        act_show = QAction("显示", self)
        act_show.triggered.connect(self._show_from_tray)
        menu.addAction(act_show)
        menu.addSeparator()
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)

    def _make_tray_icon(self):
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#c0392b"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(8, 8, 48, 48)
        p.setPen(QColor("#ffffff"))
        f = QFont("Consolas", 22, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "T")
        p.end()
        return QIcon(pm)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def minimize_to_tray(self):
        self._save_config()
        self.hide()
        self._tray.show()

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        if self._drag_pos is not None:
            self._drag_pos = None
            self._save_config()
            self._check_edge_snap()

    def enterEvent(self, e):
        self.btn_row.setVisible(True)
        self.status_label.setVisible(False)
        if self._edge_hidden:
            self._edge_show()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._menu_open:
            self.btn_row.setVisible(False)
            self.status_label.setVisible(True)
        super().leaveEvent(e)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_QSS)

        act_int = QAction("设置间隔…", self)
        act_int.triggered.connect(self._ask_interval)
        menu.addAction(act_int)

        act_fixed = QAction("定点闹钟…", self)
        act_fixed.triggered.connect(self._open_fixed_alarm_dialog)
        menu.addAction(act_fixed)

        menu.addSeparator()

        act_mute = QAction("🔇 已静音" if self.muted else "🔊 提示音开", self)
        act_mute.triggered.connect(self._toggle_mute)
        menu.addAction(act_mute)

        current_name = os.path.basename(self.sound_path) if self.sound_path else "默认提示音"
        act_pick = QAction(f"选择提示音乐…（{current_name}）", self)
        act_pick.triggered.connect(self._pick_sound)
        menu.addAction(act_pick)

        act_default = QAction("使用默认提示音", self)
        act_default.triggered.connect(self._use_default_sound)
        menu.addAction(act_default)

        if self._is_playing():
            act_prev = QAction("⏹ 停止试听", self)
            act_prev.triggered.connect(self._stop_all_audio)
        else:
            act_prev = QAction("🔊 试听", self)
            act_prev.triggered.connect(self._play_sound)
        menu.addAction(act_prev)

        menu.addSeparator()

        act_tray = QAction("最小化到托盘", self)
        act_tray.triggered.connect(self.minimize_to_tray)
        menu.addAction(act_tray)

        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        menu.exec(e.globalPos())

    # ---------- 贴边隐藏 ----------
    def _check_edge_snap(self):
        scr = self.screen().availableGeometry()
        g = self.frameGeometry()

        side = None
        if g.left() <= scr.left() + 2:
            side = "left"
        elif g.right() >= scr.right() - 2:
            side = "right"
        elif g.top() <= scr.top() + 2:
            side = "top"
        elif g.bottom() >= scr.bottom() - 2:
            side = "bottom"

        self._edge_side = side
        if side:
            self._edge_hidden = True
            self._edge_hide()

    def _edge_hide(self):
        if not self._edge_side:
            return
        scr = self.screen().availableGeometry()
        g = self.frameGeometry()
        target = QPoint(g.left(), g.top())

        if self._edge_side == "left":
            target.setX(scr.left() - g.width() + HIDE_WIDTH)
        elif self._edge_side == "right":
            target.setX(scr.right() - HIDE_WIDTH + 1)
        elif self._edge_side == "top":
            target.setY(scr.top() - g.height() + HIDE_WIDTH)
        elif self._edge_side == "bottom":
            target.setY(scr.bottom() - HIDE_WIDTH + 1)

        self._animate_move(target)

    def _edge_show(self):
        if not self._edge_side:
            return
        scr = self.screen().availableGeometry()
        g = self.frameGeometry()
        target = QPoint(g.left(), g.top())

        if self._edge_side == "left":
            target.setX(scr.left())
        elif self._edge_side == "right":
            target.setX(scr.right() - g.width() + 1)
        elif self._edge_side == "top":
            target.setY(scr.top())
        elif self._edge_side == "bottom":
            target.setY(scr.bottom() - g.height() + 1)

        self._edge_hidden = False
        self._animate_move(target)

    def _animate_move(self, target: QPoint):
        self._move_anim = QPropertyAnimation(self, b"pos")
        self._move_anim.setDuration(180)
        self._move_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._move_anim.setStartValue(self.pos())
        self._move_anim.setEndValue(target)
        self._move_anim.start()

    def _edge_poll(self):
        if not self._edge_side:
            return
        scr = self.screen().availableGeometry()
        g = self.frameGeometry()
        m = QCursor.pos()

        if self._edge_side == "left":
            trigger = (scr.left() <= m.x() <= scr.left() + EDGE_TRIGGER
                       and g.top() <= m.y() <= g.bottom())
        elif self._edge_side == "right":
            trigger = (scr.right() - EDGE_TRIGGER <= m.x() <= scr.right()
                       and g.top() <= m.y() <= g.bottom())
        elif self._edge_side == "top":
            trigger = (scr.top() <= m.y() <= scr.top() + EDGE_TRIGGER
                       and g.left() <= m.x() <= g.right())
        else:
            trigger = (scr.bottom() - EDGE_TRIGGER <= m.y() <= scr.bottom()
                       and g.left() <= m.x() <= g.right())

        inside = g.contains(m)

        if trigger and self._edge_hidden:
            self._edge_show()
        elif not inside and not trigger and not self._edge_hidden:
            self._edge_hidden = True
            self._edge_hide()

    # ---------- 控制 ----------
    def toggle(self):
        self.running = not self.running
        self.status_label.setText("已暂停" if not self.running else "工作中 · 右键设置")

    def reset(self):
        self.remaining = self.interval
        self.overdue = 0
        self.running = True
        self._stop_pulse()
        self._set_bg(BG_NORMAL)
        self.time_label.setStyleSheet(f"color: {FG_NORMAL};")
        self.status_label.setText("工作中 · 右键设置")
        self._close_card()

    def snooze(self, minutes: int = 5):
        self.remaining += minutes * 60
        self.overdue = 0
        self.running = True
        self._stop_pulse()
        self._set_bg(BG_NORMAL)
        self.time_label.setStyleSheet(f"color: {FG_NORMAL};")
        self.status_label.setText(f"已加 {minutes} 分钟")
        self._close_card()
        QTimer.singleShot(1500, lambda: self.status_label.setText("工作中 · 右键设置"))

    def _ask_interval(self):
        v, ok = QInputDialog.getInt(
            self, "设置间隔", "每隔多少分钟提醒一次？",
            self.interval // 60, 1, 180
        )
        if ok:
            self.interval = v * 60
            self.reset()

    def _open_fixed_alarm_dialog(self):
        dlg = FixedAlarmDialog(self.fixed_alarms, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.fixed_alarms = dlg.get_alarms()
            self._save_config()

    def _toggle_mute(self):
        self.muted = not self.muted
        self._stop_all_audio()
        self._save_config()

    def _pick_sound(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "选择提示音乐", "",
            "音频 (*.mp3 *.wav *.ogg *.flac);;所有文件 (*.*)"
        )
        if p:
            self.sound_path = p
            self._save_config()
            name = os.path.basename(p)
            self.status_label.setText(f"已选择：{name}")
            QTimer.singleShot(2500, lambda: self.status_label.setText("工作中 · 右键设置"))

    def _use_default_sound(self):
        """清空 sound_path，恢复为系统默认提示音"""
        self.sound_path = ""
        self._save_config()
        self.status_label.setText("已切换为默认提示音")
        QTimer.singleShot(2500, lambda: self.status_label.setText("工作中 · 右键设置"))
        self._play_sound()

    def quit_app(self):
        self._save_config()
        self._stop_all_audio()
        if self._tray:
            self._tray.hide()
        QApplication.quit()

    # ---------- 主循环 ----------
    def _tick(self):
        if self.running:
            if self.remaining > 0:
                self.remaining -= 1
                self._render_countdown()
            else:
                self.overdue += 1
                self._render_overdue()

        self._check_fixed_alarms()

    def _check_fixed_alarms(self):
        if self.muted:
            return
        now = datetime.now()
        cur = now.strftime("%H:%M:%S")
        if cur in self.fixed_alarms and self._last_fixed_fired != cur:
            self._last_fixed_fired = cur
            self._trigger_alarm(reason=f"定点闹钟 {cur[:5]}")

    def _render_countdown(self):
        m, s = divmod(self.remaining, 60)
        self.time_label.setText(f"{m:02d}:{s:02d}")
        self._set_bg(BG_NORMAL)
        self.time_label.setStyleSheet(f"color: {FG_NORMAL};")

    def _render_overdue(self):
        m, s = divmod(self.overdue, 60)
        self.time_label.setText(f"+{m:02d}:{s:02d}")
        if self.overdue == 1:
            self._trigger_alarm(reason="该起来活动啦～")
        self.status_label.setText("该起来活动啦～")

    def _trigger_alarm(self, reason: str = ""):
        self._play_sound()
        self._show_card(reason=reason)
        self._start_pulse()
        if reason:
            self.status_label.setText(reason)

    # ---------- 视觉脉冲 ----------
    def _start_pulse(self):
        self._set_bg(BG_WARN)
        self.time_label.setStyleSheet(f"color: {FG_WARN};")
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._pulse_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._pulse_anim.setDuration(700)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setKeyValueAt(0.5, 0.45)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.start()

    def _stop_pulse(self):
        if self._pulse_anim is not None:
            self._pulse_anim.stop()
            self._pulse_anim = None
        self.setGraphicsEffect(None)

    def _set_bg(self, color: str):
        self.root_frame.setStyleSheet(f"""
            QWidget#root {{
                background: {color};
                border-radius: 12px;
            }}
            QLabel#time {{
                font-family: Consolas, "Microsoft YaHei";
                font-size: 26px;
                font-weight: bold;
            }}
            QLabel#status {{
                color: #dddddd;
                font-family: "Microsoft YaHei";
                font-size: 9px;
            }}
            QPushButton#ctrl {{
                background: rgba(255,255,255,0.12);
                color: #ffffff;
                border: none;
                border-radius: 5px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
                padding: 2px 6px;
                min-width: 26px;
            }}
            QPushButton#ctrl:hover {{
                background: rgba(255,255,255,0.28);
            }}
            QPushButton#ctrl::menu-indicator {{
                image: none;
                width: 0px;
            }}
        """)

    # ---------- 提示卡片 ----------
    def _show_card(self, reason: str = "该起来活动一下了"):
        if self._card is not None and self._card.isVisible():
            return

        card = QWidget(None, Qt.WindowType.FramelessWindowHint
                       | Qt.WindowType.WindowStaysOnTopHint
                       | Qt.WindowType.Tool)
        card.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        card.setStyleSheet(f"""
            QWidget#cardRoot {{
                background: {BG_WARN};
                border-radius: 14px;
            }}
            QLabel#title {{
                color: #ffffff;
                font-family: "Microsoft YaHei";
                font-size: 16px;
                font-weight: bold;
            }}
            QLabel#desc {{
                color: #ffe0e0;
                font-family: "Microsoft YaHei";
                font-size: 11px;
            }}
            QPushButton#cardBtn {{
                background: #ffffff;
                color: {BG_WARN};
                border: none;
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                padding: 6px 14px;
            }}
            QPushButton#cardBtn:hover {{
                background: #ffe0e0;
            }}
            QPushButton#musicBtn {{
                background: rgba(255,255,255,0.18);
                color: #ffffff;
                border: 1px solid rgba(255,255,255,0.35);
                border-radius: 6px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                padding: 6px 14px;
            }}
            QPushButton#musicBtn:hover {{
                background: rgba(255,255,255,0.30);
            }}
        """)

        root = QFrame(card)
        root.setObjectName("cardRoot")
        root.setGeometry(0, 0, 340, 180)

        lay = QVBoxLayout(root)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(8)

        title = QLabel(f"⏰ {reason}")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        desc = QLabel("你已经连续工作很久了，站起来走两步吧～")
        desc.setObjectName("desc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(desc)

        lay.addSpacing(4)

        # ---- 第一行：音乐控制 ----
        music_row = QHBoxLayout()
        music_row.addStretch()

        music_btn = QPushButton()
        music_btn.setObjectName("musicBtn")
        music_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        music_btn.setMinimumWidth(150)

        def refresh_music_btn():
            if self.is_music_playing():
                music_btn.setText("⏸ 暂停音乐")
            else:
                music_btn.setText("▶ 继续播放")

        def on_music_click():
            self.toggle_music()
            QTimer.singleShot(80, refresh_music_btn)

        refresh_music_btn()
        music_btn.clicked.connect(on_music_click)
        music_row.addWidget(music_btn)
        music_row.addStretch()
        lay.addLayout(music_row)

        # ---- 第二行：原有按钮 ----
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        b1 = QPushButton("我休息了")
        b1.setObjectName("cardBtn")
        b1.setCursor(Qt.CursorShape.PointingHandCursor)
        b1.clicked.connect(lambda: (self._close_card(), self.reset()))
        btn_row.addWidget(b1)

        b2 = QPushButton("再等 5 分钟")
        b2.setObjectName("cardBtn")
        b2.setCursor(Qt.CursorShape.PointingHandCursor)
        b2.clicked.connect(lambda: (self._close_card(), self.snooze(5)))
        btn_row.addWidget(b2)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        scr = self.screen().availableGeometry()
        w, h = 340, 180
        target_x = scr.right() - w - 24
        target_y = scr.bottom() - h - 60

        card.setGeometry(scr.right() + 10, target_y, w, h)
        card.show()

        anim = QPropertyAnimation(card, b"pos")
        anim.setDuration(260)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(QPoint(scr.right() + 10, target_y))
        anim.setEndValue(QPoint(target_x, target_y))
        anim.start()
        card._anim = anim

        self._card = card

    def _close_card(self):
        if self._card is not None:
            try:
                self._card.close()
                self._card.deleteLater()
            except Exception:
                pass
            self._card = None
        self._stop_all_audio()

    # ---------- 关闭 ----------
    def closeEvent(self, e):
        self._save_config()
        self._stop_all_audio()
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = FloatingTimer()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
