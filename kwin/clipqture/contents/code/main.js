// Companion to clipqture.py: does what Wayland doesn't allow normal applications to do.
const SERVICE = "me.horwell.clipqture";
const PATH = "/Clipqture";
const INTERFACE = "me.horwell.clipqture";
const MENU_TITLE = "Clipqture Menu";

function isMenu(window) {
    return window.caption === MENU_TITLE;
}

function placeMenu(window) {
    const cursor = workspace.cursorPos;
    const area = workspace.clientArea(KWin.PlacementArea, workspace.screenAt(cursor), workspace.currentDesktop);
    const geometry = window.frameGeometry;

    let x = cursor.x;
    let y = cursor.y;
    if (x + geometry.width > area.x + area.width) {
        x = area.x + area.width - geometry.width;
    }
    if (y + geometry.height > area.y + area.height) {
        y = cursor.y - geometry.height;
    }
    x = Math.max(x, area.x);
    y = Math.max(y, area.y);

    window.noBorder = true;
    window.skipTaskbar = true;
    window.skipPager = true;
    window.skipSwitcher = true;
    window.keepAbove = true;
    window.frameGeometry = { x: x, y: y, width: geometry.width, height: geometry.height };
    workspace.activeWindow = window;
}

workspace.windowAdded.connect(function (window) {
    if (isMenu(window)) {
        placeMenu(window);
    } else {
        // The title may be set after the window is created.
        window.captionChanged.connect(function () {
            if (isMenu(window)) {
                placeMenu(window);
            }
        });
    }
});

workspace.windowActivated.connect(function (window) {
    if (!window || isMenu(window)) {
        return;
    }
    callDBus(SERVICE, PATH, INTERFACE, "ActiveWindowChanged", window.desktopFileName || "", window.resourceClass || "");
});

registerShortcut("Clipqture", "Show Clipqture at Mouse Position", "Meta+V", function () {
    callDBus(SERVICE, PATH, INTERFACE, "ShowMenu");
});
