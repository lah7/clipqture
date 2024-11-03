# Maintainer: Luke Horwell <code (at) horwell (dot) me>

pkgname=clipqture
pkgver=1.0.0
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
sha256sums=('dc18f15edf09fe03fc1a70e8d90639451cc1074f362d0d0aec93daa3ed53d00d')

package() {
  cd "$pkgname-$pkgver"
  mkdir -p "$pkgdir/etc/xdg/autostart"
  mkdir -p "$pkgdir/usr/bin"
  mkdir -p "$pkgdir/usr/share/applications"
  cp -v clipqture.py "$pkgdir/usr/bin/clipqture"
  cp -v clipqture.desktop "$pkgdir/etc/xdg/autostart/"
  cp -v clipqture.desktop "$pkgdir/usr/share/applications/"
}
