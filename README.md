# cursor-ide

Arch Linux package for [Cursor](https://www.cursor.com) — the AI code editor. Packages the official `.deb` release with its bundled Electron runtime.

Available on the [AUR](https://aur.archlinux.org/packages/cursor-ide).

## Features

- Tracks the official **stable** release channel (not pre-release/latest)
- Uses Cursor's bundled Electron (no system electron dependency)
- Icon trimmed and resized to fit desktop environment conventions

## cursor-ide vs cursor-bin

| | cursor-ide | cursor-bin |
|---|---|---|
| Electron | Bundled (upstream) | System |
| Native module compatibility | Guaranteed | May break |
| Package size | Larger | Smaller |
| Upstream behaviour | Identical to official builds | Best-effort |

Use `cursor-ide` if you want the exact behaviour of Cursor's official Linux builds. Use `cursor-bin` if you prefer sharing the system Electron and don't mind the occasional breakage with native extensions.

## Install

```bash
# With an AUR helper
paru -S cursor-ide

# Or manually
git clone https://aur.archlinux.org/cursor-ide.git
cd cursor-ide
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
