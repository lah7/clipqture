# ClipQture

_Minimal **Clip**board cap**ture** program for **Qt** desktops._


## What's this?

A minimal clipboard manager written in PyQt6. It listens to the clipboard
and _captures_ recently copied text. By using global shortcut configured
in your desktop environment (such as **Meta+V**), a context menu with
your clipboard entries appears under your cursor.

It is designed for **text only** and under X11.


## Installation

1. Make sure you have PyQt6 installed.

2. Copy files:

    * `clipqture.py` to `~/.local/bin/` (you may need to update your PATH)
    * `clipqture.desktop` to `~/.local/share/applications`

    Adjust the path of the `Exec=` line if necessary.


### Configuration

Use your desktop environment to:

* Set up a global shortcut that executes this file.
    * For example, in KDE, use **Menu Editor**.
* Add this script to run at startup.
    * For example, in KDE, use **System Settings** > **Autostart**.

This works by using a Unix socket to communicate to the first instance.
The socket will be placed at `/run/user/1000/` (where `1000` is your user ID).

To adjust any of the settings, please edit the script directly.


## License

[GNU General Public License v3.0](LICENSE)
