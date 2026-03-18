# cursor-ide-bin

Arch Linux package for [Cursor](https://www.cursor.com) — the AI code editor. Packages the official `.deb` release with its bundled Electron runtime.

Available on the [AUR](https://aur.archlinux.org/packages/cursor-ide-bin).

## Features

- Tracks the official **stable** release channel (not pre-release/latest)
- Uses Cursor's bundled Electron (no system electron dependency)
- Icon trimmed and resized to fit desktop environment conventions

## Install

```bash
# With an AUR helper
paru -S cursor-ide-bin

# Or manually
git clone https://aur.archlinux.org/cursor-ide-bin.git
cd cursor-ide-bin
makepkg -si
```

## Update Script

A TypeScript update helper is included to check for and apply new upstream releases:

```bash
# Check for updates
npx tsx update.ts --check

# Update PKGBUILD and .SRCINFO
npx tsx update.ts --update
```
