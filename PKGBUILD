# Maintainer: Luke Horwell <code (at) horwell (dot) me>

pkgname=clipqture
pkgver=1.0.0
pkgrel=1
pkgdesc="Minimal clipboard monitor"
arch=(any)
url="https://github.com/lah7/clipqture"
license=(LGPL-2.1-or-later)
depends=(
  python-pyqt6
  python-setproctitle
)
makedepends=()
source=("git+https://github.com/lah7/clipqture/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('afc91733fad4d5366d83c6767b11a51dd0d183292df2eff733d84f77c017ba16')

package() {
  cd "$pkgname"
  mkdir -p "$pkgdir/etc/xdg/autostart"
  mkdir -p "$pkgdir/usr/bin"
  mkdir -p "$pkgdir/usr/share/applications"
  cp -v clipqture.py "$pkgdir/usr/bin/clipqture"
  cp -v clipqture.desktop "$pkgdir/etc/xdg/autostart/"
  cp -v clipqture.desktop "$pkgdir/usr/share/applications/"
}
