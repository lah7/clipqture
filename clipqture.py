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
# Copyright (C) 2024 Luke Horwell <code@horwell.me>
#
"""
Minimal clipboard monitor written in PyQt6 for switching between text copied
to the clipboard via a context menu.

To use:
  - Run it at start-up, to monitor the clipboard.
  - Configure a hotkey using your desktop environment to execute this script,
    which will use a socket to communicate to the first instance.
"""
import os
import re
import signal
import socket
import sys
from typing import List

import setproctitle
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QClipboard, QCursor, QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu

# Options
MAX_ITEMS = 10
MAX_ITEM_LINE_LENGTH = 150
OLD_KLIPPER_BEHAVIOUR = True

DEBUG = False
SOCKET_PATH = f"/run/user/{os.getuid()}/clipqture.sock"


class UnixSocketServer(QThread):
    """
    Create a Unix socket server to listen for messages from another instance
    of this program. This can be used to open the context menu.
    """
    signal_received = pyqtSignal()

    def run(self):
        """
        Forever listen for messages from another instance of this program.
        When a message is received, emit the signal to open the context menu.
        """
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server_socket.bind(SOCKET_PATH)
        except OSError:
            pass

        server_socket.listen(1)

        while True:
            conn, addr = server_socket.accept() # pylint: disable=unused-variable

            while True:
                data = conn.recv(8)
                if data:
                    self.signal_received.emit()
                else:
                    break


class ClipboardItem(object):
    """Describes an item on the clipboard"""
    text: str
    icon: str


class ClipQture(QMainWindow):
    """Minimial [Clip]board Capt[ure] for [Qt] desktop environments"""
    def __init__(self):
        super().__init__()

        self.clipboard: QClipboard = QApplication.clipboard() # type: ignore
        self.clipboard.dataChanged.connect(self.clipboard_changed)
        self.history: List[ClipboardItem] = []
        self.max_items = MAX_ITEMS
        self.setWindowTitle("ClipQture")
        if DEBUG:
            print("Listening to clipboard...")

    def clipboard_changed(self):
        """User copied data to the clipboard"""
        if DEBUG:
            print("Clipboard data changed")

        item = ClipboardItem()
        item.text = self.clipboard.text()

        mimetypes = self.clipboard.mimeData().formats() # type: ignore
        if "text/uri-list" in mimetypes:
            item.icon = "edit-copy"
        else:
            item.icon = ""

        filelist = item.text.split("\n")
        if len(filelist) > 1 and filelist[0].startswith("file://"):
            filelist = []
            for line in item.text.split("\n"):
                if line == "\n":
                    continue
                filelist.append(line.replace("file://", "").strip())
            item.text = f"({len(filelist) - 1} paths): " + "\n".join(filelist)

        for _item in self.history:
            if _item.text == item.text:
                self.history.remove(_item)

        self.history.insert(0, item)
        self.history = self.history[:self.max_items]

    def show_context_menu(self):
        """
        Provide the user a summarised list of the clipboard history.
        The user can change the active clipboard selection.
        """
        if DEBUG:
            print("Got signal to open context menu")

        menu = QMenu()

        if self.history:
            for item in self.history:
                # Provide a summary
                label_text = item.text.strip()

                # Apply older Klipper (<= 6.1.0) behaviour
                if OLD_KLIPPER_BEHAVIOUR:
                    # Don't show '\n' characters, keep everything on one line
                    label_text = label_text.replace("\n", " ")

                    # Reduce multiple spaces to one
                    label_text = re.sub(r"\s+", " ", label_text)

                # Truncate long text
                if len(item.text) > MAX_ITEM_LINE_LENGTH:
                    label_text = label_text[:MAX_ITEM_LINE_LENGTH].strip() + "..."

                action = QAction(label_text, self)
                action.triggered.connect(lambda _, text=item.text: self.clipboard.setText(text))
                if item.icon:
                    action.setIcon(QIcon.fromTheme(item.icon))
                menu.addAction(action)
        else:
            empty = QAction("Empty clipboard history", menu)
            empty.setIcon(QIcon.fromTheme("edit-paste-symbolic"))
            empty.setEnabled(False)
            menu.addAction(empty)

        cursor_position = QCursor.pos()
        menu.exec(cursor_position)


if __name__ == "__main__":
    setproctitle.setproctitle("clipqture")

    # Allow CTRL+C to exit program
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # When a second instance is opened, talk to the first instance.
    if os.path.exists(SOCKET_PATH):
        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.connect(SOCKET_PATH)
            client_socket.send(b"1")
            sys.exit(0)
        except ConnectionRefusedError:
            # The process listening to it had died.
            os.remove(SOCKET_PATH)

    # This is the first instance, manage the clipboard and wait for the signal.
    app = QApplication(sys.argv)
    window = ClipQture()
    server = UnixSocketServer()
    server.signal_received.connect(window.show_context_menu)
    server.start()
    app.exec()
