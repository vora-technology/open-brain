#!/bin/sh

set -eu
umask 077

candidate_id="candidate_native-p4w6"

fail() {
    printf '%s\n' '{"status":"failed"}' >&2
    exit 1
}

case "${OPEN_BRAIN_INSTALL_ROOT:-}" in
    /*) install_root=$OPEN_BRAIN_INSTALL_ROOT ;;
    "")
        case "${HOME:-}" in
            /*) install_root=$HOME/.local/share/open-brain ;;
            *) fail ;;
        esac
        ;;
    *) fail ;;
esac

media_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P) || fail
source_candidate=$media_root/$candidate_id
candidates=$install_root/candidates
destination=$candidates/$candidate_id
temporary=$candidates/.$candidate_id.$$
next_link=$install_root/.current.$$

[ -d "$source_candidate" ] || fail
[ ! -L "$source_candidate" ] || fail
[ -x "$source_candidate/open-brain" ] || fail
[ -f "$source_candidate/open-brain-native.json" ] || fail
[ ! -L "$install_root" ] || fail
[ ! -e "$destination" ] && [ ! -L "$destination" ] || fail
[ ! -e "$install_root/current" ] && [ ! -L "$install_root/current" ] || fail
[ ! -e "$temporary" ] && [ ! -L "$temporary" ] || fail
[ ! -e "$next_link" ] && [ ! -L "$next_link" ] || fail

cleanup() {
    rm -rf "$temporary"
    rm -f "$next_link"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$candidates"
chmod 700 "$install_root" "$candidates"
mkdir "$temporary"
if command -v ditto >/dev/null 2>&1; then
    ditto "$source_candidate" "$temporary"
else
    cp -RPp "$source_candidate/." "$temporary/"
fi

"$temporary/open-brain" __native-self-check >/dev/null 2>&1 || fail
mv "$temporary" "$destination"
ln -s "candidates/$candidate_id" "$next_link"
mv "$next_link" "$install_root/current"
trap - EXIT HUP INT TERM

printf '%s\n' '{"status":"installed"}'
