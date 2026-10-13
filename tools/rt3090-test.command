#!/bin/bash
# Manual temporary testing only. Never edits EFI, SIP or Extensions/cache.
set -euo pipefail
PATH=/usr/bin:/bin:/usr/sbin:/sbin
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ACTION=${1:-check}
BUNDLE_ID=org.rt3090.network
SOURCE="$ROOT/RT3090Network.kext"
STAGE=""
cleanup() { if [[ -n "$STAGE" && -d "$STAGE" ]]; then /bin/rm -rf -- "$STAGE"; fi; }
trap cleanup EXIT
need_root() { if [[ $(/usr/bin/id -u) != 0 ]]; then echo "Run explicitly with sudo; no settings changed." >&2; exit 1; fi; }
case "$ACTION" in
 status) exec /usr/bin/python "$ROOT/rt3090ctl.py" status ;;
 log) exec /usr/bin/log stream --style syslog --predicate 'process == "kernel" AND eventMessage CONTAINS[c] "RT3090"' ;;
 check|load)
  need_root
  [[ -f "$SOURCE/Contents/Info.plist" && -f "$SOURCE/Contents/MacOS/RT3090Network" ]] || { echo "Main RT3090Network.kext is missing beside this script." >&2; exit 1; }
  IDENTIFIER=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$SOURCE/Contents/Info.plist")
  VERSION=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$SOURCE/Contents/Info.plist")
  [[ "$IDENTIFIER" == "$BUNDLE_ID" && "$VERSION" == 0.3.4 ]] || { echo "Expected RT3090Network 0.3.4; refusing other bundle/version." >&2; exit 1; }
  /usr/bin/plutil -lint "$SOURCE/Contents/Info.plist"
  if [[ "$ACTION" == load ]]; then
   LISTING=$(/usr/sbin/kextstat -b "$BUNDLE_ID")
   if printf '%s\n' "$LISTING" | /usr/bin/awk -v id="$BUNDLE_ID" '$6==id {found=1} END {exit !found}'; then
    echo "$LISTING"; echo "A version is already loaded. No automatic unload/replacement performed." >&2; exit 1
   fi
  fi
  STAGE=$(/usr/bin/mktemp -d /private/tmp/rt3090-test.XXXXXX)
  /usr/bin/ditto "$SOURCE" "$STAGE/RT3090Network.kext"
  /usr/sbin/chown -R root:wheel "$STAGE"
  /bin/chmod -R u+rwX,go+rX,go-w "$STAGE"
  /usr/sbin/kextutil -n -t "$STAGE/RT3090Network.kext"
  if [[ "$ACTION" == load ]]; then
   /usr/sbin/kextutil -v 6 "$STAGE/RT3090Network.kext"
   /usr/sbin/kextstat -b "$BUNDLE_ID"
   echo "Temporary load requested. This is not PCI/WPA2/Internet success. Run status next."
  else
   echo "Validation command succeeded; no kext loaded. Native hardware remains unverified."
  fi
  ;;
 unload)
  need_root
  /usr/sbin/kextunload -b "$BUNDLE_ID"
  /usr/sbin/kextstat -b "$BUNDLE_ID"
  echo "Unload requested; previously installed EFI/Extensions copies were not removed."
  ;;
 *) echo "Usage: $0 [check|load|unload|status|log] (default: check)" >&2; exit 2 ;;
esac
