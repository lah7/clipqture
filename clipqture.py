#!/usr/bin/python3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2024-2026 Luke Horwell <code@horwell.me>
#
"""
Minimal clipboard monitor written in PyQt6 for switching between text on the
clipboard via a simple context menu.

Brings back the Plasma 6.1 Kilpper experience, with support for Wayland.

This program runs in the background monitoring the clipboard via:
    wl-paste --watch

A KWin script provides functionality that normal applications can't achieve
on Wayland, such as opening the menu from a global shortcut and positioning
it under the cursor, and knowing which program icon originally copied the content.
"""
import base64
import configparser
import os
import re
import shutil
import signal
import subprocess
import sys
from typing import Dict, List

import setproctitle
from PyQt6.QtCore import (QEvent, QObject, QProcess, QStandardPaths, Qt,
                          pyqtClassInfo, pyqtSlot)
from PyQt6.QtDBus import QDBusAbstractAdaptor, QDBusConnection
from PyQt6.QtGui import QAction, QColor, QIcon, QKeyEvent, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu

APP_ID = "clipqture"
DBUS_SERVICE = "me.horwell.clipqture"
DBUS_PATH = "/Clipqture"
DBUS_INTERFACE = "me.horwell.clipqture"

# The KWin script identifies the menu window by this title.
MENU_TITLE = "Clipqture Menu"


def find_icon_name(desktop_file: str, window_class: str) -> str:
    """
    Resolve the icon name of an application from its window properties.
    Returns an empty string if it couldn't be determined.
    """
    candidates = [name for name in (desktop_file, window_class, window_class.lower()) if name]
    candidates = [name[:-len(".desktop")] if name.endswith(".desktop") else name for name in candidates]

    for name in candidates:
        path = QStandardPaths.locate(QStandardPaths.StandardLocation.ApplicationsLocation, f"{name}.desktop")
        if not path:
            continue
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(path, encoding="utf-8")
            icon = parser.get("Desktop Entry", "Icon", fallback="")
        except configparser.Error:
            icon = ""
        if icon:
            return icon

    for name in candidates:
        if QIcon.hasThemeIcon(name):
            return name

    return ""


class ClipboardItem:
    """Describes an item on the clipboard"""
    text: str = ""
    icon: str|QPixmap|None = None


class HistoryMenu(QMenu):
    """
    The clipboard history menu.

    Applications can't open a popup at an arbitrary position on Wayland, so it
    is a borderless window that the KWin script moves under the cursor.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(MENU_TITLE)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        # Only popups close themselves when an item is chosen.
        self.triggered.connect(self.close)

    def event(self, e: QEvent|None) -> bool:
        if e and e.type() == QEvent.Type.WindowDeactivate:
            self.close()
        return super().event(e)

    def keyPressEvent(self, e: QKeyEvent|None):
        if e and e.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(e)


@pyqtClassInfo("D-Bus Interface", DBUS_INTERFACE)
class ClipqtureAdaptor(QDBusAbstractAdaptor):
    """D-Bus interface used by the KWin script"""
    def __init__(self, parent_daemon: "Clipqture"):
        super().__init__(parent_daemon)
        self.daemon = parent_daemon

    @pyqtSlot()
    def ShowMenu(self): # pylint: disable=invalid-name
        """Open the clipboard history menu"""
        self.daemon.show_menu()

    @pyqtSlot(str, str)
    def ActiveWindowChanged(self, desktop_file: str, window_class: str): # pylint: disable=invalid-name
        """The active window changed (sent by the KWin script)"""
        self.daemon.set_active_window(desktop_file, window_class)


class Clipqture(QObject):
    """Minimial [Clip]board Capt[ure] for [Qt] desktop environments"""
    def __init__(self):
        super().__init__()

        self.history: List[ClipboardItem] = []
        self.active_icon = ""
        self.icon_cache: Dict[tuple, str] = {}
        self.menu: HistoryMenu|None = None
        self.watcher: QProcess|None = None
        self.watch_buffer = b""

        # Options
        self.max_items = 10
        self.max_item_line_length = 150
        self.old_klipper_behaviour = True
        self.capture_window_icon = True
        self.load_configuration()

        if not (shutil.which("wl-paste") and shutil.which("wl-copy")):
            sys.exit("clipqture requires 'wl-clipboard' to be installed.")
        self.start_watcher()

    def load_configuration(self):
        """Load the user's configuration, or create default with comments"""
        config_path = os.path.expanduser("~/.config/clipqture.conf")
        parser = configparser.ConfigParser()
        parser.read(config_path)

        if "clipqture" in parser:
            if "max_items" in parser["clipqture"]:
                self.max_items = int(parser["clipqture"]["max_items"])
            if "max_item_line_length" in parser["clipqture"]:
                self.max_item_line_length = int(parser["clipqture"]["max_item_line_length"])
            if "old_klipper_behaviour" in parser["clipqture"]:
                self.old_klipper_behaviour = parser["clipqture"].getboolean("old_klipper_behaviour")
            if "capture_window_icon" in parser["clipqture"]:
                self.capture_window_icon = parser["clipqture"].getboolean("capture_window_icon")
        else:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("[clipqture]\n\n")
                f.write("# How many items to remember on the clipboard?\n")
                f.write(f"max_items = {self.max_items}\n\n")
                f.write("# How many characters to show in the context menu?\n")
                f.write(f"max_item_line_length = {self.max_item_line_length}\n\n")
                f.write("# Show one line per item, strip whitespace, and hide '\\n' characters?\n")
                f.write(f"old_klipper_behaviour = {self.old_klipper_behaviour}\n\n")
                f.write("# KDE only: Show the application icon in the list? (requires the KWin script)\n")
                f.write(f"capture_window_icon = {self.capture_window_icon}\n\n")
            print(f"Default configuration written to {config_path}")

    def start_watcher(self):
        """
        Wayland doesn't notify unfocused applications of clipboard changes,
        so use wl-paste to listen via the data-control protocol.
        For every change, print the clipboard as one line of base64.
        """
        self.watcher = QProcess(self)
        self.watcher.readyReadStandardOutput.connect(self.watcher_output)
        self.watcher.finished.connect(self.watcher_finished)
        self.watcher.start("wl-paste", ["--type", "text", "--watch", "sh", "-c", "base64 -w0; echo"])

    def watcher_output(self):
        """Received clipboard data from wl-paste"""
        assert self.watcher
        self.watch_buffer += bytes(self.watcher.readAllStandardOutput().data())
        *lines, self.watch_buffer = self.watch_buffer.split(b"\n")
        for line in lines:
            try:
                text = base64.b64decode(line).decode("utf-8")
            except ValueError:
                continue
            self.clipboard_changed(text)

    def watcher_finished(self):
        """wl-paste stopped (e.g. the compositor doesn't support data-control)"""
        assert self.watcher
        print("wl-paste stopped: " + bytes(self.watcher.readAllStandardError().data()).decode("utf-8", "replace"), file=sys.stderr)

    def set_active_window(self, desktop_file: str, window_class: str):
        """The KWin script reports the focused window, which is where copied text originates from"""
        if APP_ID in [desktop_file, window_class]:
            return

        key = (desktop_file, window_class)
        if key not in self.icon_cache:
            self.icon_cache[key] = find_icon_name(desktop_file, window_class)
        self.active_icon = self.icon_cache[key]

    def set_clipboard(self, text: str):
        """Change the active clipboard text"""
        subprocess.run(["wl-copy", "--type", "text/plain"], input=text.encode("utf-8"), check=False)

    def clipboard_changed(self, text: str):
        """User copied data to the clipboard"""
        item = ClipboardItem()
        item.text = text
        item.icon = ""

        if not item.text:
            return

        # Determine icon to show
        hex_colour = item.text.replace(";", "").strip()
        if hex_colour.startswith("#") and (len(hex_colour) == 4 or len(hex_colour) == 7) and hex_colour[1:].isalnum():
            item.icon = QPixmap(16, 16)
            item.icon.fill(QColor(hex_colour))

        elif self.capture_window_icon:
            item.icon = self.active_icon

        # Tweak file:// paths by counting how many paths were copied
        filelist = item.text.split("\n")
        if len(filelist) > 1 and filelist[0].startswith("file://"):
            filelist = []
            for line in item.text.split("\n"):
                if line == "\n":
                    continue
                filelist.append(line.replace("file://", "").strip())
            item.text = f"({len(filelist) - 1} paths): " + "\n".join(filelist)

        # Existing item, move to start
        for index, _item in enumerate(self.history):
            if _item.text == item.text:
                self.history.pop(index)
                self.history.insert(0, _item)
                return

        # New item, add to history
        self.history.insert(0, item)
        self.history = self.history[:self.max_items]

    def show_menu(self):
        """
        Provide the user a summarised list of the clipboard history.
        The user can change the active clipboard selection.
        """
        if self.menu:
            self.menu.close()

        menu = HistoryMenu()
        self.menu = menu

        if self.history:
            for item in self.history:
                # Provide a summary
                label_text = item.text.strip()

                # Apply older Klipper (<= 6.1.0) behaviour
                if self.old_klipper_behaviour:
                    # Don't show '\n' characters, keep everything on one line
                    label_text = label_text.replace("\n", " ")

                    # Reduce multiple spaces to one
                    label_text = re.sub(r"\s+", " ", label_text)

                # Truncate long text
                if len(item.text) > self.max_item_line_length:
                    label_text = label_text[:self.max_item_line_length].strip() + "..."

                action = QAction(label_text, menu)
                action.triggered.connect(lambda _, text=item.text: self.set_clipboard(text))

                if item.icon:
                    if isinstance(item.icon, str):
                        if item.icon.startswith("/"):
                            action.setIcon(QIcon(item.icon))
                        else:
                            action.setIcon(QIcon.fromTheme(item.icon))
                    else:
                        action.setIcon(QIcon(item.icon))

                menu.addAction(action)

                if not self.old_klipper_behaviour:
                    menu.addSeparator()

            menu.addSeparator()
            clear = QAction("Clear History", menu)
            clear.setIcon(QIcon.fromTheme("edit-clear-history"))
            clear.triggered.connect(self.clear_history)
            menu.addAction(clear)

        else:
            empty = QAction("Empty clipboard history", menu)
            empty.setIcon(QIcon.fromTheme("edit-paste-symbolic"))
            empty.setEnabled(False)
            menu.addAction(empty)

        # Position is set by the KWin script
        menu.show()

    def clear_history(self):
        """Clear the clipboard history"""
        self.history = []


if __name__ == "__main__":
    setproctitle.setproctitle("clipqture")

    # Allow CTRL+C to exit program
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)

    # Only one instance may run, as it owns the D-Bus service.
    bus = QDBusConnection.sessionBus()
    if not bus.registerService(DBUS_SERVICE):
        sys.exit("clipqture is already running.")

    # Monitor the clipboard and wait for the KWin script.
    daemon = Clipqture()
    ClipqtureAdaptor(daemon)
    bus.registerObject(DBUS_PATH, daemon, QDBusConnection.RegisterOption.ExportAdaptors)
    app.exec()
