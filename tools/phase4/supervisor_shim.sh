#!/bin/sh

set -eu
umask 077

fail() {
    exit 1
}

for value in \
    "${OPEN_BRAIN_TEST_EXECUTABLE:-}" \
    "${OPEN_BRAIN_TEST_ROOT:-}" \
    "${OPEN_BRAIN_TEST_PID_FILE:-}" \
    "${OPEN_BRAIN_TEST_LOADED_FILE:-}" \
    "${OPEN_BRAIN_TEST_CORRUPTION_MARKER:-}" \
    "${OPEN_BRAIN_TEST_CORRUPTION_TARGET:-}"
do
    case "$value" in
        /*) : ;;
        *) fail ;;
    esac
done

pid_file=$OPEN_BRAIN_TEST_PID_FILE
loaded_file=$OPEN_BRAIN_TEST_LOADED_FILE
executable=$OPEN_BRAIN_TEST_EXECUTABLE
brain_root=$OPEN_BRAIN_TEST_ROOT
corruption_marker=$OPEN_BRAIN_TEST_CORRUPTION_MARKER
corruption_target=$OPEN_BRAIN_TEST_CORRUPTION_TARGET

stop_daemon() {
    if [ -f "$pid_file" ]; then
        pid=$(/bin/cat "$pid_file")
        case "$pid" in
            *[!0-9]*|"") fail ;;
        esac
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            count=0
            while kill -0 "$pid" 2>/dev/null && [ "$count" -lt 200 ]; do
                /bin/sleep 0.05
                count=$((count + 1))
            done
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
        /bin/rm -f "$pid_file"
    fi
    if [ -f "$corruption_marker" ]; then
        /bin/rm -f "$corruption_marker"
        printf '\n' >> "$corruption_target"
    fi
}

start_daemon() {
    "$executable" __appliance-daemon --root "$brain_root" >/dev/null 2>&1 &
    printf '%s\n' "$!" > "$pid_file"
}

status_daemon() {
    if [ -f "$pid_file" ]; then
        pid=$(/bin/cat "$pid_file")
        case "$pid" in
            *[!0-9]*|"") fail ;;
        esac
        if kill -0 "$pid" 2>/dev/null; then
            printf 'active\n'
            exit 0
        fi
    fi
    exit 1
}

case " $* " in
    *" bootstrap "*|*" enable "*) : > "$loaded_file" ;;
    *" kickstart "*)
        [ -f "$loaded_file" ] || fail
        stop_daemon
        start_daemon
        ;;
    *" restart "*)
        stop_daemon
        start_daemon
        ;;
    *" start "*) start_daemon ;;
    *" kill "*)
        stop_daemon
        [ ! -f "$loaded_file" ] || start_daemon
        ;;
    *" stop "*) stop_daemon ;;
    *" bootout "*|*" disable "*)
        /bin/rm -f "$loaded_file"
        stop_daemon
        ;;
    *" print "*|*" status "*) status_daemon ;;
    *) exit 0 ;;
esac
