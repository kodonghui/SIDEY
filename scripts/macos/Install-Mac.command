#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && /bin/pwd -P)
PAYLOAD="$ROOT/macOS/corthex-sidey-macOS-arm64.zip"
fail() { printf '\n%s\n' "$1"; printf 'Press Return to close: '; read -r answer; exit 1; }
test "$(uname -s)" = Darwin || fail 'This installer is for macOS.'
test "$(sysctl -n hw.optional.arm64 2>/dev/null || true)" = 1 || fail 'Apple Silicon (M1 or later) is required.'
MAJOR=$(sw_vers -productVersion | cut -d. -f1)
test "$MAJOR" -ge 26 || fail 'macOS 26 or later is required. Update macOS before installing.'
test -f "$PAYLOAD" || fail 'The macOS app archive is missing. Extract the entire ZIP before installation.'
if pgrep -x SIDEY >/dev/null 2>&1; then
  fail 'Quit the running SIDEY app from its menu bar icon, then run this installer again.'
fi

STAGE=$(mktemp -d "${TMPDIR:-/tmp}/corthex-sidey-install.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM
ditto -x -k "$PAYLOAD" "$STAGE"
SOURCE="$STAGE/SIDEY.app"
test -x "$SOURCE/Contents/MacOS/SIDEY" || fail 'The app archive is incomplete.'
codesign --verify --deep --strict "$SOURCE" || fail 'App signature verification failed. Download the complete package again.'
DEST="$HOME/Applications/corthex-sidey.app"
DESKTOP="$HOME/Desktop/corthex-sidey.app"
STAMP=$(date +%Y%m%d-%H%M%S)-$$
mkdir -p "$HOME/Applications" "$HOME/Desktop"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then mv "$DEST" "$DEST.backup-$STAMP"; fi
if ! ditto "$SOURCE" "$DEST"; then
  if [ -e "$DEST" ] || [ -L "$DEST" ]; then mv "$DEST" "$STAGE/failed-app"; fi
  if [ -e "$DEST.backup-$STAMP" ]; then mv "$DEST.backup-$STAMP" "$DEST"; fi
  fail 'App installation failed.'
fi
if [ -e "$DESKTOP" ] || [ -L "$DESKTOP" ]; then mv "$DESKTOP" "$DESKTOP.backup-$STAMP"; fi
ln -s "$DEST" "$DESKTOP"
printf '\nInstalled: %s\nDesktop shortcut: %s\n' "$DEST" "$DESKTOP"
printf '\nOpen corthex-sidey on your Desktop. Keep the original SIDEY app closed.\n'
printf 'This personal build is ad-hoc signed, not notarized. macOS may require approval in System Settings > Privacy & Security.\n'
printf 'Your account data and the original SIDEY installation were not removed.\n'
printf '\nPress Return to close: '
read -r answer
