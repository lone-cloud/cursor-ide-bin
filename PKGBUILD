# Maintainer: lone-cloud <lonecloud604@pm.me>

pkgname=cursor-ide-bin
pkgver=2.6.19
pkgrel=1
pkgdesc='Cursor - AI-first coding environment (uses bundled Electron)'
arch=('x86_64')
url="https://www.cursor.com"
license=('LicenseRef-Cursor_EULA')
provides=('cursor')
conflicts=('cursor-bin')

depends=(
  'alsa-lib'
  'at-spi2-core'
  'cairo'
  'dbus'
  'expat'
  'gcc-libs'
  'glib2'
  'gtk3'
  'hicolor-icon-theme'
  'libdrm'
  'libsecret'
  'libx11'
  'libxcb'
  'libxcomposite'
  'libxdamage'
  'libxext'
  'libxfixes'
  'libxkbcommon'
  'libxkbfile'
  'libxrandr'
  'mesa'
  'nspr'
  'nss'
  'pango'
  'xdg-utils'
)
optdepends=(
  'libnotify: desktop notifications'
  'org.freedesktop.secrets: credential storage via SecretService'
  'libdbusmenu-glib: KDE global menu support'
)

options=(!strip !debug)

_commit=224838f96445be37e3db643a163a817c15b3606c
source=(
  "cursor_${pkgver}_amd64.deb::https://downloads.cursor.com/production/${_commit}/linux/x64/deb/amd64/deb/cursor_${pkgver}_amd64.deb"
  "cursor.desktop"
  "cursor-launcher.sh"
)
sha256sums=('SKIP'
            'SKIP'
            'SKIP')
noextract=("cursor_${pkgver}_amd64.deb")

package() {
  # Extract full deb — keep bundled Electron intact.
  bsdtar -xOf "cursor_${pkgver}_amd64.deb" data.tar.xz |
    tar -xJf - -C "$pkgdir"

  # Fix zsh completion path for Arch
  if [[ -d "$pkgdir/usr/share/zsh/vendor-completions" ]]; then
    mv "$pkgdir/usr/share/zsh/vendor-completions" \
       "$pkgdir/usr/share/zsh/site-functions"
  fi

  # Install our .desktop file
  install -Dm644 "$srcdir/cursor.desktop" \
    "$pkgdir/usr/share/applications/cursor.desktop"

  # Install icons at proper sizes for KDE/GNOME
  local _res_dir="$pkgdir/usr/share/cursor/resources/app/resources/linux"
  if [[ -f "$_res_dir/code.png" ]]; then
    install -Dm644 "$_res_dir/code.png" \
      "$pkgdir/usr/share/icons/hicolor/512x512/apps/cursor.png"
  fi
  if [[ -f "$_res_dir/code.svg" ]]; then
    install -Dm644 "$_res_dir/code.svg" \
      "$pkgdir/usr/share/icons/hicolor/scalable/apps/cursor.svg"
  fi
  # Fallback from pixmaps
  if [[ -f "$pkgdir/usr/share/pixmaps/cursor.png" ]] &&
     [[ ! -f "$pkgdir/usr/share/icons/hicolor/512x512/apps/cursor.png" ]]; then
    install -Dm644 "$pkgdir/usr/share/pixmaps/cursor.png" \
      "$pkgdir/usr/share/icons/hicolor/512x512/apps/cursor.png"
  fi

  # Install launcher
  install -Dm755 "$srcdir/cursor-launcher.sh" "$pkgdir/usr/bin/cursor"

  # chrome-sandbox suid for non-user-namespace systems
  if [[ -f "$pkgdir/usr/share/cursor/chrome-sandbox" ]]; then
    chmod 4755 "$pkgdir/usr/share/cursor/chrome-sandbox"
  fi
}
