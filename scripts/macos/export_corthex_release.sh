#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && /bin/pwd -P)
EXPORT_DIR=${1:-$REPO_ROOT/build/corthex-macos}
DERIVED_DIR=${SIDEY_DERIVED_DATA:-$REPO_ROOT/build/corthex-derived}
python3 "$REPO_ROOT/scripts/validate_pixel_assets.py" --canonical-only

xcodebuild \
  -project "$REPO_ROOT/macos/SIDEY.xcodeproj" \
  -scheme SIDEY -configuration Release \
  -destination 'platform=macOS,arch=arm64' \
  -derivedDataPath "$DERIVED_DIR" \
  -disableAutomaticPackageResolution \
  ARCHS=arm64 ONLY_ACTIVE_ARCH=YES \
  CODE_SIGN_IDENTITY=- CODE_SIGN_STYLE=Manual DEVELOPMENT_TEAM= \
  ENABLE_HARDENED_RUNTIME=NO \
  SIDEY_DISPLAY_NAME=corthex-sidey \
  SIDEY_RELEASE_CHANNEL=production \
  'SWIFT_ACTIVE_COMPILATION_CONDITIONS=$(inherited) CORTHEX_CUSTOM_BUILD' \
  build

APP="$DERIVED_DIR/Build/Products/Release/SIDEY.app"
PLIST="$APP/Contents/Info.plist"
test -x "$APP/Contents/MacOS/SIDEY"
test "$(lipo -archs "$APP/Contents/MacOS/SIDEY")" = arm64
test "$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "$PLIST")" = 26.0
test "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$PLIST")" = app.sidey.desktop
test "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "$PLIST")" = corthex-sidey
test "$(/usr/libexec/PlistBuddy -c 'Print :SIDEYAuthURLScheme' "$PLIST")" = sidey
test "$(/usr/libexec/PlistBuddy -c 'Print :SIDEYReleaseChannel' "$PLIST")" = production
for character in pepe agumon gabumon tentomon palmon gomamon biyomon patamon gatomon; do
  find "$APP/Contents/Resources" -name "$character.png" -print | grep . >/dev/null
done
codesign --verify --deep --strict "$APP"
mkdir -p "$EXPORT_DIR"
ditto -c -k --norsrc --noextattr --noqtn --noacl --keepParent "$APP" "$EXPORT_DIR/corthex-sidey-macOS-arm64.zip"
(cd "$EXPORT_DIR" && shasum -a 256 corthex-sidey-macOS-arm64.zip > corthex-sidey-macOS-arm64.zip.sha256)
printf '%s\n' 'Built corthex-sidey: Apple Silicon, macOS 26+, ad-hoc signed, not notarized.'
