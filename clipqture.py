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
# Copyright (C) 2024-2025 Luke Horwell <code@horwell.me>
#
"""
Minimal clipboard monitor written in PyQt6 for switching between text copied
to the clipboard via a context menu.

To use:
  - Run it at start-up, to monitor the clipboard.
  - Configure a hotkey using your desktop environment to execute this script,
    which will use a socket to communicate to the first instance.
"""
import configparser
import os
import re
import signal
import socket
import sys
from typing import List

import setproctitle
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QClipboard, QCursor, QIcon, QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu
from Xlib import X, display
from Xlib.error import XError

DEBUG = False
SOCKET_PATH = f"/run/user/{os.getuid()}/clipqture.sock"


def get_active_window_icon() -> Image.Image|None:
    """
    For X11, capture the icon of the active window.
    This can be used to show which application the data was copied from.
    """
    # Connect to the X server
    d = display.Display()
    root = d.screen().root

    # Get the active window
    wm_icon = d.intern_atom("_NET_WM_ICON")
    active_window = d.intern_atom("_NET_ACTIVE_WINDOW")
    active_window = root.get_full_property(active_window, X.AnyPropertyType).value[0]

    # Get the icon data
    xwindow = d.create_resource_object("window", active_window)
    xproperty = xwindow.get_full_property(wm_icon, X.AnyPropertyType)
    if not xproperty:
        return None

    icon_data = xproperty.value

    # Parse the icon data
    icons = []
    while icon_data:
        width = icon_data[0]
        height = icon_data[1]
        icon = icon_data[2:2 + width * height]
        icons.append((width, height, icon))
        icon_data = icon_data[2 + width * height:]

    # Convert the first icon to an image
    if icons:
        width, height, icon = icons[0]

        # Adjust byte order from BGRA to RGBA
        rgba_icon = []
        for pixel in icon:
            b = (pixel & 0x000000FF)
            g = (pixel & 0x0000FF00) >> 8
            r = (pixel & 0x00FF0000) >> 16
            a = (pixel & 0xFF000000) >> 24
            rgba_icon.append((r, g, b, a))

        # Pack the pixel data into a byte string
        pixel_data = bytes([component for pixel in rgba_icon for component in pixel])

        # Create an image from the byte string
        image = Image.frombytes("RGBA", (width, height), pixel_data)
        return image

    return None


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
    text: str = ""
    icon: str|QPixmap|None = None


class ClipQture(QMainWindow):
    """Minimial [Clip]board Capt[ure] for [Qt] desktop environments"""
    def __init__(self):
        super().__init__()

        self.clipboard: QClipboard = QApplication.clipboard() # type: ignore
        self.clipboard.dataChanged.connect(self.clipboard_changed)
        self.history: List[ClipboardItem] = []
        self.setWindowTitle("ClipQture")

        # Options
        self.max_items = 10
        self.max_item_line_length = 150
        self.old_klipper_behaviour = True
        self.capture_window_icon = True
        self.load_configuration()

        if DEBUG:
            print("Listening to clipboard...")

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
                f.write("# X11 only: Show the application icon in the list?\n")
                f.write(f"capture_window_icon = {self.capture_window_icon}\n\n")
            print(f"Default configuration written to {config_path}")

    def clipboard_changed(self):
        """User copied data to the clipboard"""
        if DEBUG:
            print("Clipboard data changed")

        item = ClipboardItem()
        item.text = self.clipboard.text()

        if not item.text:
            return

        # Show an icon
        if self.capture_window_icon:
            item.icon = QPixmap()
            try:
                image = get_active_window_icon()
            except XError:
                image = None

            if image:
                qimage = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGBA8888)
                item.icon = QPixmap.fromImage(qimage)
        else:
            mimetypes = self.clipboard.mimeData().formats() # type: ignore
            if "text/uri-list" in mimetypes:
                item.icon = "edit-copy"

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
                if self.old_klipper_behaviour:
                    # Don't show '\n' characters, keep everything on one line
                    label_text = label_text.replace("\n", " ")

                    # Reduce multiple spaces to one
                    label_text = re.sub(r"\s+", " ", label_text)

                # Truncate long text
                if len(item.text) > self.max_item_line_length:
                    label_text = label_text[:self.max_item_line_length].strip() + "..."

                action = QAction(label_text, self)
                action.triggered.connect(lambda _, text=item.text: self.clipboard.setText(text))

                if item.icon:
                    if isinstance(item.icon, str):
                        action.setIcon(QIcon.fromTheme(item.icon))
                    else:
                        action.setIcon(QIcon(item.icon))

                menu.addAction(action)

                if not self.old_klipper_behaviour:
                    menu.addSeparator()

            menu.addSeparator()
            clear = QAction("Clear History", self)
            clear.setIcon(QIcon.fromTheme("edit-clear-history"))
            clear.triggered.connect(self.clear_history)
            menu.addAction(clear)

        else:
            empty = QAction("Empty clipboard history", menu)
            empty.setIcon(QIcon.fromTheme("edit-paste-symbolic"))
            empty.setEnabled(False)
            menu.addAction(empty)

        cursor_position = QCursor.pos()
        menu.exec(cursor_position)

    def clear_history(self):
        """Clear the clipboard history"""
        self.history = []


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
