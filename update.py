#!/usr/bin/env python3
"""
Check for new Cursor releases and update PKGBUILD accordingly.

Cursor doesn't have a proper release API, but their download URLs follow a
predictable pattern. We probe their update endpoint to discover the latest
version and commit hash, then patch the PKGBUILD.

Exit codes:
  0 = updated (or already up-to-date with --check)
  1 = error
  2 = already up-to-date (with --update)
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


# Cursor's update check endpoint (same one the app uses)
UPDATE_URL = "https://api2.cursor.sh/updates/api/update/linux-x64/stable/latest"
# Fallback: direct download page that redirects
DOWNLOAD_URL = "https://www.cursor.com/api/download?platform=linux-x64&releaseTrack=stable"


def get_latest_version() -> dict:
    """Query Cursor's update API for the latest version info."""
    # Try the update API first
    try:
        req = urllib.request.Request(
            UPDATE_URL,
            headers={"User-Agent": "cursor-ide-bin-updater/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            if "version" in data and "name" in data:
                return {
                    "version": data["name"],
                    "commit": data["version"],
                    "url": data.get("url", ""),
                }
    except Exception as e:
        print(f"Update API failed ({e}), trying fallback...", file=sys.stderr)

    # Fallback: follow the download redirect to extract version from URL
    try:
        req = urllib.request.Request(
            DOWNLOAD_URL,
            headers={"User-Agent": "cursor-ide-bin-updater/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            final_url = resp.url
            # URL pattern: .../production/<commit>/linux/x64/deb/amd64/deb/cursor_<ver>_amd64.deb
            m = re.search(
                r"/production/([a-f0-9]+)/linux/x64/deb/amd64/deb/cursor_([0-9.]+)_amd64\.deb",
                final_url,
            )
            if m:
                return {
                    "version": m.group(2),
                    "commit": m.group(1),
                    "url": final_url,
                }
    except Exception as e:
        print(f"Fallback also failed: {e}", file=sys.stderr)

    # Last resort: try the JSON API endpoint that the original updater uses
    try:
        api_url = "https://downloads.cursor.com/production/latest/linux/x64/deb/amd64/deb"
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "cursor-ide-bin-updater/1.0"},
            method="HEAD",
        )
        # Don't follow redirects manually
        opener = urllib.request.build_opener(NoRedirectHandler())
        resp = opener.open(req, timeout=30)
        location = resp.headers.get("Location", "")
        m = re.search(
            r"/production/([a-f0-9]+)/linux/x64/deb/amd64/deb/cursor_([0-9.]+)_amd64\.deb",
            location,
        )
        if m:
            return {
                "version": m.group(2),
                "commit": m.group(1),
                "url": location,
            }
    except Exception:
        pass

    print("ERROR: Could not determine latest Cursor version from any endpoint.", file=sys.stderr)
    sys.exit(1)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    http_error_301 = http_error_303 = http_error_307 = http_error_302


def get_current_version(pkgbuild: Path) -> tuple[str, str]:
    """Extract current pkgver and _commit from PKGBUILD."""
    text = pkgbuild.read_text()
    ver_m = re.search(r"^pkgver=(.+)$", text, re.MULTILINE)
    commit_m = re.search(r"^_commit=(.+)$", text, re.MULTILINE)
    if not ver_m or not commit_m:
        print("ERROR: Could not parse pkgver/_commit from PKGBUILD", file=sys.stderr)
        sys.exit(1)
    return ver_m.group(1).strip(), commit_m.group(1).strip()


def compute_sha256(url: str) -> str:
    """Download file and compute SHA256."""
    print(f"Downloading {url} for checksum...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "cursor-ide-bin-updater/1.0"})
    sha = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=300) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def update_pkgbuild(pkgbuild: Path, new_ver: str, new_commit: str, new_sha256: str):
    """Update PKGBUILD with new version, commit, and checksum."""
    text = pkgbuild.read_text()

    text = re.sub(r"^pkgver=.+$", f"pkgver={new_ver}", text, flags=re.MULTILINE)
    text = re.sub(r"^pkgrel=.+$", "pkgrel=1", text, flags=re.MULTILINE)
    text = re.sub(r"^_commit=.+$", f"_commit={new_commit}", text, flags=re.MULTILINE)

    # Update sha256sums — first entry is the deb
    text = re.sub(
        r"(sha256sums=\(')[^']*(')",
        rf"\g<1>{new_sha256}\2",
        text,
    )

    pkgbuild.write_text(text)


def generate_srcinfo(pkgbuild_dir: Path) -> str:
    """Generate .SRCINFO from PKGBUILD using makepkg."""
    result = subprocess.run(
        ["makepkg", "--printsrcinfo"],
        cwd=pkgbuild_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"makepkg --printsrcinfo failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description="Update cursor-ide-bin PKGBUILD")
    parser.add_argument(
        "--check", action="store_true",
        help="Only check, don't update. Prints JSON with latest version info.",
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Update PKGBUILD if a new version is available.",
    )
    parser.add_argument(
        "--pkgbuild", type=Path, default=Path(__file__).parent / "PKGBUILD",
        help="Path to PKGBUILD (default: ./PKGBUILD)",
    )
    parser.add_argument(
        "--skip-checksum", action="store_true",
        help="Skip SHA256 download (use SKIP). Faster but less secure.",
    )
    args = parser.parse_args()

    if not args.check and not args.update:
        parser.print_help()
        sys.exit(1)

    latest = get_latest_version()
    current_ver, current_commit = get_current_version(args.pkgbuild)

    print(f"Current: {current_ver} ({current_commit[:12]}...)", file=sys.stderr)
    print(f"Latest:  {latest['version']} ({latest['commit'][:12]}...)", file=sys.stderr)

    if args.check:
        is_new = latest["version"] != current_ver or latest["commit"] != current_commit
        out = {
            "current_version": current_ver,
            "latest_version": latest["version"],
            "latest_commit": latest["commit"],
            "update_available": is_new,
        }
        print(json.dumps(out, indent=2))
        return

    if args.update:
        if latest["version"] == current_ver and latest["commit"] == current_commit:
            print("Already up-to-date.", file=sys.stderr)
            sys.exit(2)

        # Compute checksum
        deb_url = (
            f"https://downloads.cursor.com/production/{latest['commit']}"
            f"/linux/x64/deb/amd64/deb/cursor_{latest['version']}_amd64.deb"
        )
        if args.skip_checksum:
            sha256 = "SKIP"
        else:
            sha256 = compute_sha256(deb_url)
            print(f"SHA256: {sha256}", file=sys.stderr)

        update_pkgbuild(args.pkgbuild, latest["version"], latest["commit"], sha256)
        print(f"PKGBUILD updated to {latest['version']}", file=sys.stderr)

        # Regenerate .SRCINFO
        srcinfo_path = args.pkgbuild.parent / ".SRCINFO"
        try:
            srcinfo = generate_srcinfo(args.pkgbuild.parent)
            srcinfo_path.write_text(srcinfo)
            print(".SRCINFO regenerated", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not regenerate .SRCINFO: {e}", file=sys.stderr)
            print("You may need to run 'makepkg --printsrcinfo > .SRCINFO' manually.", file=sys.stderr)


if __name__ == "__main__":
    main()
