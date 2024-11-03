# Maintainer: Luke Horwell <code (at) horwell (dot) me>

pkgname=clipqture
pkgver=1.1.0
pkgrel=1
pkgdesc="Minimal clipboard monitor"
arch=(any)
url="https://github.com/lah7/clipqture"
license=(LGPL-2.1-or-later)
depends=(
  python-pillow
  python-pyqt6
  python-setproctitle
  python-xlib
)
makedepends=()
source=("https://github.com/lah7/clipqture/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('2ba4e535b70f10f09ebe75efb5bf2eb0d00755426ba7a1abf42cc9cd440e572d')

package() {
  cd "$pkgname-$pkgver"
  mkdir -p "$pkgdir/etc/xdg/autostart"
  mkdir -p "$pkgdir/usr/bin"
  mkdir -p "$pkgdir/usr/share/applications"
  cp -v clipqture.py "$pkgdir/usr/bin/clipqture"
  cp -v clipqture.desktop "$pkgdir/etc/xdg/autostart/"
  cp -v clipqture.desktop "$pkgdir/usr/share/applications/"
}
