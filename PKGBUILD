# Maintainer: Luke Horwell <code (at) horwell (dot) me>

pkgname=clipqture
pkgver=2.0.0
pkgrel=1
pkgdesc="Minimal clipboard monitor for KDE Plasma"
arch=(any)
url="https://github.com/lah7/clipqture"
license=(LGPL-3.0-or-later)
depends=(
  python-pyqt6
  python-setproctitle
  wl-clipboard
)
makedepends=()
source=("https://github.com/lah7/clipqture/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('f8fe5eada8c1d143a5a642e72a83da9fb0738089c24ca53fe03cb39f5e5b97f0')

package() {
  cd "$pkgname-$pkgver"
  mkdir -p "$pkgdir/etc/xdg/autostart"
  mkdir -p "$pkgdir/usr/bin"
  mkdir -p "$pkgdir/usr/share/applications"
  mkdir -p "$pkgdir/usr/share/kwin/scripts"
  cp -rv kwin/clipqture "$pkgdir/usr/share/kwin/scripts/"
  cp -v clipqture.py "$pkgdir/usr/bin/clipqture"
  cp -v clipqture.desktop "$pkgdir/etc/xdg/autostart/"
  cp -v clipqture.desktop "$pkgdir/usr/share/applications/"
}
