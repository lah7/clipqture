# ClipQture

A minimal clipboard assistant written in PyQt6. It brings back the previous
Plasma 6.1 (Kilpper) experience for the Clipboard's "Show at Mouse Position" shortcut.

ClipQture = _**Clip**board for **Qt**/KDE desktops cap**ture** program._

![Comparison of clipqture and Klipper in Plasma 6.1 and 6.2](.readme/comparison.webp)

It is designed to co-exist with the Plasma widget, although the clipboard state isn't
synchronised between the two programs. It is designed for **selecting text**
and **X11 only**.

Otherwise, this is how it works:

* Listen to the clipboard and _capture_ recently copied text.
* A global shortcut configured in your desktop environment (like **Meta+V**) executes
the program, which tells the first instance to open a context menu.
* Use the context menu to quickly change the active clipboard text.

It extends original functionality by showing the window icon where the text was copied from!


## Features

* Show window icon where text was copied from **(X11 only)**
* Show previews of colour hex values (e.g. #RRGGBB).
* Configurable preferences file.


## Installation

### Arch / KDE

Grab a copy from [Releases]. Or, build a package using the supplied PKGBUILD:

    git clone https://github.com/lah7/clipqture.git
    makepkg -i

_(If this software is useful for many people_ ⭐, _I'll consider submitting it to the AUR.)_

[Releases]: https://github.com/lah7/clipqture

Next, use **KDE Menu Editor** to configure a shortcut key to launch this program.
This is required to open the context menu at your cursor position.

![Showing KDE Menu Editor with Advanced tab](.readme/menuedit.webp)

The program will be automatically started when you log in (`/etc/xdg/autostart`)


### Other Distributions & Environments

1. Make sure you have the [Python dependencies] installed.

2. Copy the files:

    * `clipqture.py` to `~/.local/bin/` (you may need to update your PATH)
    * `clipqture.desktop` to `~/.local/share/applications/`

    Edit the `.desktop` files to adjust the path of the `Exec=` line to point
    to the full path where you placed `clipqture.py`.

[Python dependencies]: PKGBUILD#10

Then, use your desktop environment to:

* Set up a global shortcut that executes this file.
* Add this script to run at startup.
    * For example, in KDE, use **System Settings** > **Autostart**. In MATE, use **Start-up Applications**.


## Configuration

There are some basic settings to change with `~/.config/clipqture.conf`.
It will be created with default settings on the first run. Restart the program
to apply changes.


### Wayland

Support under Wayland is poor, due to the security model of Wayland. Items may not
appear on the clipboard, and the menu doesn't open under the cursor.

To hide the window title bar that appears for the menu that is opened, you'll
need to use the settings for your window manager.

In KDE/Breeze, you can set this up in **System Settings**:

1. Go to Colours & Themes → **Window Decorations**
2. Edit the "Breeze" theme.
3. Go to "Window-Specific Overrides" tab.
5. Add an exception for:
  * Window Title: clipqture.py
  * Check "Hide window title bar"
6. Apply and save changes.

This step is not necessary under X11.


## Why does it exist?

Starting in Plasma 6.2.0, KDE's Klipper (Clipboard applet) went in a different
direction. The shortcut for _"Show Clipboard Items at Mouse Position"_ opens
the full widget at the cursor. I used it often enough that it felt like a
regression for this use case.

From a UI perspective, the widget has more buttons, more padding per item,
and buttons getting in the way. Context menus had a border, but the Plasma widget
does not (there's a shadow, but it's shallow, making it look flat).
Not to mention the widget takes up lots of vertical space that it may need
to scroll, and it has images and other data types I didn't need.

I was pretty happy and productive with the old menu, with one item per line.
This project brings back that simplicity. Other clipboard managers seemed too much.
Being written in Python, it's easy to modify and extend, and nobody can take
that away!


## Tip: Don't make your clipboard forget!

**It is recommended to keep Klipper enabled,** but disable the "show at cursor" shortcut.
This makes sure that the clipboard doesn't vanish if you copy text from a program
and then close that same program.


## License

[GNU General Public License v3.0](LICENSE)
