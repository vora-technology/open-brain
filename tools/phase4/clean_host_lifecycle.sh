#!/bin/sh

set -eu
umask 077

stage='preflight'

fail() {
    printf '{"failure_stage":"%s","status":"failed"}\n' "$stage" >&2
    exit 1
}

[ "$#" -eq 8 ] || fail

package=$1
checksum_file=$2
fixture=$3
evidence=$4
source_sha=$5
host=$6
architecture=$7
exact_signed_candidate=$8

case "$package:$checksum_file:$fixture:$evidence" in
    /*:/*:/*:/*) : ;;
    *) fail ;;
esac
case "$source_sha" in
    *[!0-9a-f]*|"") fail ;;
esac
[ "${#source_sha}" -eq 40 ] || fail
case "$host" in
    ubuntu-24.04|ubuntu-26.04|debian-13|macos-14|macos-15|macos-26) : ;;
    *) fail ;;
esac
case "$architecture" in
    arm64|x86_64) : ;;
    *) fail ;;
esac
case "$exact_signed_candidate" in
    true|false) : ;;
    *) fail ;;
esac

script_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P) || fail
package_root=$(CDPATH='' cd -- "$(dirname -- "$package")" && pwd -P) || fail
fixture_root=$(CDPATH='' cd -- "$fixture" && pwd -P) || fail
package=$package_root/$(basename -- "$package")
checksum_file=$package_root/$(basename -- "$checksum_file")
[ -f "$package" ] && [ ! -L "$package" ] || fail
[ -f "$checksum_file" ] && [ ! -L "$checksum_file" ] || fail
[ -d "$fixture_root/runtime-root" ] || fail
[ -f "$fixture_root/controller.json" ] || fail

temporary_parent=/tmp
if [ ! -d "$temporary_parent" ] || [ ! -w "$temporary_parent" ]; then
    temporary_parent=${TMPDIR:-}
fi
case "$temporary_parent" in
    /*) : ;;
    *) fail ;;
esac
sandbox=$(mktemp -d "$temporary_parent/ob-p4w6.XXXXXX") || fail
sandbox=$(CDPATH='' cd -- "$sandbox" && pwd -P) || fail
mounted=false
mount_point=$sandbox/mount
pid_file=$sandbox/daemon.pid

cleanup() {
    if [ -f "$pid_file" ]; then
        pid=$(/bin/cat "$pid_file" 2>/dev/null || true)
        case "$pid" in
            *[!0-9]*|"") : ;;
            *) kill "$pid" 2>/dev/null || true ;;
        esac
    fi
    if [ "$mounted" = true ]; then
        hdiutil detach "$mount_point" >/dev/null 2>&1 || true
    fi
    rm -rf "$sandbox"
}
trap cleanup EXIT HUP INT TERM

artifact_sha256() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        fail
    fi
}

copy_tree() {
    if command -v ditto >/dev/null 2>&1; then
        ditto "$1" "$2"
    else
        cp -RPp "$1" "$2"
    fi
}

wait_file() {
    count=0
    while [ "$count" -lt 400 ]; do
        [ -f "$1" ] && return 0
        sleep 0.05
        count=$((count + 1))
    done
    fail
}

expected_digest=$(awk 'NR == 1 {print $1}' "$checksum_file")
expected_name=$(awk 'NR == 1 {print $2}' "$checksum_file")
actual_digest=$(artifact_sha256 "$package")
[ "$expected_digest" = "$actual_digest" ] || fail
[ "$expected_name" = "$(basename -- "$package")" ] || fail

stage='media-unpack'
media=$sandbox/media
mkdir "$media"
case "$package" in
    *.tar.gz)
        tar -xzpf "$package" -C "$media" >/dev/null 2>&1 || fail
        payload_count=$(find "$media" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
        [ "$payload_count" = 1 ] || fail
        payload=$(find "$media" -mindepth 1 -maxdepth 1 -type d)
        ;;
    *.dmg)
        mkdir "$mount_point"
        hdiutil attach -readonly -nobrowse -mountpoint "$mount_point" "$package" \
            >/dev/null 2>&1 || fail
        mounted=true
        payload=$mount_point
        ;;
    *) fail ;;
esac
[ -x "$payload/install.sh" ] || fail

stage='artifact-install'
brain=$sandbox/brain
copy_tree "$fixture_root/runtime-root" "$brain"
controller=$sandbox/controller.json
cp -p "$fixture_root/controller.json" "$controller"
chmod 600 "$controller"
install_root=$sandbox/install
home=$sandbox/home
temporary=$sandbox/tmp
host_tools=$sandbox/host-tools
mkdir "$home" "$temporary" "$host_tools"

setup_started=$(date +%s)
OPEN_BRAIN_INSTALL_ROOT=$install_root "$payload/install.sh" > "$sandbox/install.json" || fail
jq -e '.status == "installed"' "$sandbox/install.json" >/dev/null || fail
executable=$install_root/current/open-brain
[ -x "$executable" ] || fail

copy_candidate() {
    identifier=$1
    destination=$install_root/candidates/$identifier
    copy_tree "$install_root/current" "$destination"
    jq -S --arg identifier "$identifier" '.candidate_id = $identifier' \
        "$destination/open-brain-native.json" > "$destination/.manifest.next"
    mv "$destination/.manifest.next" "$destination/open-brain-native.json"
    chmod 644 "$destination/open-brain-native.json"
}

good_candidate=candidate_native-p4w6-next
failed_candidate=candidate_native-p4w6-failed
copy_candidate "$good_candidate"
copy_candidate "$failed_candidate"

cp "$script_root/supervisor_shim.sh" "$host_tools/supervisor-shim"
chmod 755 "$host_tools/supervisor-shim"
ln -s supervisor-shim "$host_tools/launchctl"
ln -s supervisor-shim "$host_tools/systemctl"
cp "$script_root/unix_request.pl" "$sandbox/unix-request"
chmod 755 "$sandbox/unix-request"

corruption_marker=$sandbox/corrupt-next-stop
corruption_target=$install_root/candidates/$failed_candidate/_internal/open_brain/resources/supervisors/launchd.json
loaded_file=$sandbox/supervisor-loaded

run_product() {
    env \
        HOME="$home" \
        OPEN_BRAIN_ROOT="$brain" \
        OPEN_BRAIN_TEST_CORRUPTION_MARKER="$corruption_marker" \
        OPEN_BRAIN_TEST_CORRUPTION_TARGET="$corruption_target" \
        OPEN_BRAIN_TEST_EXECUTABLE="$executable" \
        OPEN_BRAIN_TEST_LOADED_FILE="$loaded_file" \
        OPEN_BRAIN_TEST_PID_FILE="$pid_file" \
        OPEN_BRAIN_TEST_ROOT="$brain" \
        OPEN_BRAIN_UI_PORT=18788 \
        PATH="$host_tools" \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONNOUSERSITE=1 \
        PYTHONPATH="$sandbox/source-checkout-must-not-be-used" \
        TMPDIR="$temporary" \
        "$executable" "$@"
}

stage='prior-schema-upgrade'
state_database=$brain/.open-brain/state/phase1.sqlite3
sqlite3 "$state_database" 'PRAGMA user_version=0;' >/dev/null || fail
[ "$(sqlite3 "$state_database" 'PRAGMA user_version;')" = 0 ] || fail
run_product --json init > "$sandbox/init.json" || fail
jq -e '.state_schema_version == 1' "$sandbox/init.json" >/dev/null || fail
[ "$(sqlite3 "$state_database" 'PRAGMA user_version;')" = 1 ] || fail
jq -r '.fixture_seed' "$controller" \
    > "$brain/.open-brain/state/appliance-owner-credential"
chmod 600 "$brain/.open-brain/state/appliance-owner-credential"

stage='supervisor-start'
run_product --json supervisor install > "$sandbox/supervisor-install.json" || fail
jq -e '.status == "ok"' "$sandbox/supervisor-install.json" >/dev/null || fail
run_product --json supervisor start > "$sandbox/supervisor-start.json" || fail
jq -e '.status == "ok"' "$sandbox/supervisor-start.json" >/dev/null || fail

wait_status() {
    count=0
    while [ "$count" -lt 400 ]; do
        if run_product --json status > "$sandbox/status.json" 2>/dev/null; then
            jq -e '.status == "ok"' "$sandbox/status.json" >/dev/null && return 0
        fi
        sleep 0.05
        count=$((count + 1))
    done
    fail
}
wait_status

stage='setup-recovery'
request_recovery() {
    operation=$1
    request_id=$2
    destination=$3
    source=${4:-}
    output=$5
    if [ -n "$source" ]; then
        jq -ncS \
            --arg destination "$destination" \
            --arg operation "$operation" \
            --arg request_id "$request_id" \
            --arg source "$source" \
            '{action:"recovery.request",destination:$destination,operation:$operation,request_id:$request_id,schema_version:1,source:$source}'
    else
        jq -ncS \
            --arg destination "$destination" \
            --arg operation "$operation" \
            --arg request_id "$request_id" \
            '{action:"recovery.request",destination:$destination,operation:$operation,request_id:$request_id,schema_version:1,source:null}'
    fi | "$sandbox/unix-request" "$brain/.open-brain/run/control.sock" > "$output" || fail
    jq -e --arg operation "$operation" \
        '.operation == $operation and (.status == "scheduled" or .status == "completed")' \
        "$output" >/dev/null || fail
}

setup_backup=$sandbox/setup-backup
setup_export=$sandbox/setup-export
request_recovery \
    backup-create \
    backup_123e4567-e89b-42d3-a456-426614174601 \
    "$setup_backup" \
    '' \
    "$sandbox/setup-backup-request.json"
wait_file "$setup_backup/backup-manifest.json"
request_recovery \
    portable-export \
    export_123e4567-e89b-42d3-a456-426614174602 \
    "$setup_export" \
    '' \
    "$sandbox/setup-export-request.json"
wait_file "$setup_export/portable-manifest.json"
wait_status
jq -e '.doctor.state == "healthy"' "$sandbox/status.json" >/dev/null || fail
setup_finished=$(date +%s)
setup_seconds=$((setup_finished - setup_started))
[ "$setup_seconds" -le 900 ] || fail

stage='browser-auth'
origin=http://127.0.0.1:18788
jq -r '.browser_bootstrap' "$controller" \
    | jq -Rs '{credential:rtrimstr("\n")}' > "$sandbox/login-request.json"
chmod 600 "$sandbox/login-request.json"
curl --fail-with-body --silent --show-error \
    --cookie-jar "$sandbox/cookies" \
    --header "Origin: $origin" \
    --header 'Content-Type: application/json' \
    --output "$sandbox/login-response.json" \
    --data-binary "@$sandbox/login-request.json" \
    "$origin/auth/login" || fail
jq -e '.status == "authenticated" and (.csrf_token | type == "string")' \
    "$sandbox/login-response.json" >/dev/null || fail
csrf=$(jq -r '.csrf_token' "$sandbox/login-response.json")
curl_config=$sandbox/curl-auth.conf
{
    printf '%s\n' 'fail-with-body' 'silent' 'show-error'
    printf 'cookie = "%s"\n' "$sandbox/cookies"
    printf 'header = "Origin: %s"\n' "$origin"
    printf 'header = "X-CSRF-Token: %s"\n' "$csrf"
    printf '%s\n' 'header = "Content-Type: application/json"'
} > "$curl_config"
chmod 600 "$curl_config"

ui_post() {
    endpoint=$1
    body=$2
    output=$3
    curl --config "$curl_config" \
        --request POST \
        --data-binary "@$body" \
        --output "$output" \
        "$origin$endpoint" || fail
}

ui_get() {
    endpoint=$1
    output=$2
    curl --config "$curl_config" --output "$output" "$origin$endpoint" || fail
}

stage='v0-gate-07'
p0=$(jq -r '.proposal_ids[0]' "$controller")
p1=$(jq -r '.proposal_ids[1]' "$controller")
p2=$(jq -r '.proposal_ids[2]' "$controller")
p3=$(jq -r '.proposal_ids[3]' "$controller")
p4=$(jq -r '.proposal_ids[4]' "$controller")
p5=$(jq -r '.proposal_ids[5]' "$controller")

run_product --json review approve "$p0" --delivery=p4w6.clean.cli.approve \
    > "$sandbox/cli-approve.json" || fail
run_product --json review reject "$p1" --delivery=p4w6.clean.cli.reject \
    > "$sandbox/cli-reject.json" || fail
run_product --json review edit "$p2" 'CLI safely edited P4W6 meaning' \
    --delivery=p4w6.clean.cli.edit > "$sandbox/cli-edit.json" || fail
jq -e '.state == "approved"' "$sandbox/cli-approve.json" >/dev/null || fail
jq -e '.state == "rejected"' "$sandbox/cli-reject.json" >/dev/null || fail
jq -e '.state == "edited"' "$sandbox/cli-edit.json" >/dev/null || fail

jq -ncS --arg delivery_id p4w6.clean.ui.approve \
    '{delivery_id:$delivery_id,outcome:"approved"}' > "$sandbox/ui-approve-request.json"
ui_post "/api/proposals/$p3/decision" \
    "$sandbox/ui-approve-request.json" "$sandbox/ui-approve.json"
jq -ncS --arg delivery_id p4w6.clean.ui.reject \
    '{delivery_id:$delivery_id,outcome:"rejected"}' > "$sandbox/ui-reject-request.json"
ui_post "/api/proposals/$p4/decision" \
    "$sandbox/ui-reject-request.json" "$sandbox/ui-reject.json"
jq -ncS --arg delivery_id p4w6.clean.ui.edit \
    --arg edited_markdown 'UI safely edited P4W6 meaning' \
    '{delivery_id:$delivery_id,edited_markdown:$edited_markdown,outcome:"edited"}' \
    > "$sandbox/ui-edit-request.json"
ui_post "/api/proposals/$p5/decision" \
    "$sandbox/ui-edit-request.json" "$sandbox/ui-edit.json"
jq -e '.state == "approved"' "$sandbox/ui-approve.json" >/dev/null || fail
jq -e '.state == "rejected"' "$sandbox/ui-reject.json" >/dev/null || fail
jq -e '.state == "edited"' "$sandbox/ui-edit.json" >/dev/null || fail

run_product --json proposals list > "$sandbox/proposals-final.json" || fail
jq -e '[.proposals[].state] | sort == ["approved","approved","edited","edited","rejected","rejected"]' \
    "$sandbox/proposals-final.json" >/dev/null || fail
[ "$(find "$brain/history/decisions" -type f -name '*.json' | wc -l | tr -d ' ')" = 6 ] \
    || fail
run_product --json query 'safely edited P4W6 meaning' > "$sandbox/gate07-query.json" || fail
jq -e '.results | length == 2' "$sandbox/gate07-query.json" >/dev/null || fail

stage='v0-gate-13-space-create'
run_product --json spaces create 'First P4W6 space' \
    --delivery=p4w6.clean.space.first > "$sandbox/space-first.json" || fail
first_space=$(jq -r '.space_id' "$sandbox/space-first.json")
stage='v0-gate-13-ui-space-create'
jq -ncS --arg delivery_id p4w6.clean.space.second \
    --arg name 'Second P4W6 space' \
    '{delivery_id:$delivery_id,name:$name}' > "$sandbox/space-second-request.json"
ui_post /api/spaces "$sandbox/space-second-request.json" "$sandbox/space-second.json"
second_space=$(jq -r '.space_id' "$sandbox/space-second.json")
stage='v0-gate-13-rename'
jq -ncS --arg delivery_id p4w6.clean.space.rename \
    --arg name 'Renamed P4W6 space' \
    '{delivery_id:$delivery_id,name:$name}' > "$sandbox/space-rename-request.json"
ui_post "/api/spaces/$first_space/rename" \
    "$sandbox/space-rename-request.json" "$sandbox/space-rename.json"
jq -e --arg id "$first_space" '.status == "renamed" and .space_id == $id' \
    "$sandbox/space-rename.json" >/dev/null || fail

stage='v0-gate-13-unassigned-capture'
jq -ncS --arg delivery_id p4w6.clean.capture.unassigned \
    --arg text 'p4w6gate13 first routed token' \
    '{delivery_id:$delivery_id,text:$text}' > "$sandbox/capture-quick-request.json"
ui_post /api/captures/quick \
    "$sandbox/capture-quick-request.json" "$sandbox/capture-quick.json"
quick_capture=$(jq -r '.capture_id' "$sandbox/capture-quick.json")
stage='v0-gate-13-later-route'
run_product --json spaces route "$quick_capture" "$first_space" \
    --delivery=p4w6.clean.route.later > "$sandbox/route.json" || fail
jq -e --arg capture "$quick_capture" --arg space "$first_space" \
    '.status == "routed" and .capture_id == $capture and .space_id == $space' \
    "$sandbox/route.json" >/dev/null || fail

stage='v0-gate-13-second-capture'
jq -ncS --arg delivery_id p4w6.clean.capture.second \
    --arg space_id "$second_space" \
    --arg text 'p4w6gate13 second canonical token' \
    '{delivery_id:$delivery_id,space_id:$space_id,text:$text}' \
    > "$sandbox/capture-canonical-request.json"
ui_post /api/captures/canonical \
    "$sandbox/capture-canonical-request.json" "$sandbox/capture-canonical.json"
canonical_capture=$(jq -r '.capture_id' "$sandbox/capture-canonical.json")

stage='v0-gate-13-cli-scoped-query'
run_product --json query p4w6gate13 --space="$first_space" \
    > "$sandbox/query-scoped.json" || fail
stage='v0-gate-13-cli-all-query'
run_product --json query p4w6gate13 > "$sandbox/query-all.json" || fail
stage='v0-gate-13-ui-scoped-query'
ui_get "/api/search?q=p4w6gate13&space=$first_space" "$sandbox/ui-query-scoped.json"
stage='v0-gate-13-ui-all-query'
ui_get '/api/search?q=p4w6gate13' "$sandbox/ui-query-all.json"
stage='v0-gate-13-cli-scoped-assertion'
jq -e --arg capture "$quick_capture" --arg space "$first_space" \
    '.results | length == 1 and .[0].capture_id == $capture and .[0].space_id == $space' \
    "$sandbox/query-scoped.json" >/dev/null || fail
stage='v0-gate-13-cli-all-assertion'
jq -e --arg first "$quick_capture" --arg second "$canonical_capture" \
    '[.results[].capture_id] | unique == ([$first,$second] | sort)' \
    "$sandbox/query-all.json" >/dev/null || fail
stage='v0-gate-13-ui-scoped-assertion'
jq -e --arg capture "$quick_capture" --arg space "$first_space" \
    '.results | length == 1 and .[0].capture_id == $capture and .[0].space_id == $space' \
    "$sandbox/ui-query-scoped.json" >/dev/null || fail
stage='v0-gate-13-ui-all-assertion'
jq -e --arg first "$quick_capture" --arg second "$canonical_capture" \
    '[.results[].capture_id] | unique == ([$first,$second] | sort)' \
    "$sandbox/ui-query-all.json" >/dev/null || fail
stage='v0-gate-13-identity-assertion'
source_record=$(find "$brain/sources/captures" -type f -name "$quick_capture.json")
jq -e --arg capture "$quick_capture" \
    '.capture_id == $capture and .space_id == null' "$source_record" >/dev/null || fail

stage='portable-round-trip'
portable_export=$sandbox/portable-export
portable_import=$sandbox/portable-import
request_recovery \
    portable-export \
    export_123e4567-e89b-42d3-a456-426614174603 \
    "$portable_export" \
    '' \
    "$sandbox/portable-export-request.json"
wait_file "$portable_export/portable-manifest.json"
request_recovery \
    portable-import \
    import_123e4567-e89b-42d3-a456-426614174604 \
    "$portable_import" \
    "$portable_export" \
    "$sandbox/portable-import-request.json"
wait_file "$portable_import/.open-brain/state/appliance-owner-credential"
cmp "$portable_export/portable-manifest.json" \
    "$portable_import/portable-manifest.json" >/dev/null || fail
jq -r '.files[].path' "$portable_export/portable-manifest.json" | while IFS= read -r relative; do
    case "$relative" in
        ""|/*|..|../*|*/..|*/../*) fail ;;
    esac
    cmp "$portable_export/$relative" "$portable_import/$relative" >/dev/null || fail
done
[ ! -e "$portable_export/.open-brain" ] || fail
if cmp -s \
    "$brain/.open-brain/state/appliance-owner-credential" \
    "$portable_import/.open-brain/state/appliance-owner-credential"
then
    fail
fi

stage='rollback'
: > "$corruption_marker"
mkdir "$sandbox/failed-disposable"
stage='rollback-request'
set +e
run_product upgrade \
    --candidate-id="$failed_candidate" \
    --version=0.1.0 \
    --artifact-kind=native-onedir \
    --backup-destination="$sandbox/failed-upgrade-backup" \
    --disposable-root="$sandbox/failed-disposable" \
    --request-id=upgrade_123e4567-e89b-42d3-a456-426614174605 \
    --requested-at=2026-09-02T12:00:00Z \
    --confirm-owner \
    --json > "$sandbox/failed-upgrade.json"
failed_exit=$?
set -e
stage='rollback-exit'
[ "$failed_exit" -ne 0 ] || fail
stage='rollback-receipt'
if ! jq -e '.failure_stage == "activate" and .rollback_state == "rolled_back" and .daemon_restore_state == "restored"' \
    "$sandbox/failed-upgrade.json" >/dev/null
then
    jq -c '{daemon_restore_state,failure_stage,rollback_state,status}' \
        "$sandbox/failed-upgrade.json" >&2 || true
    fail
fi
stage='rollback-daemon-restore'
wait_status

stage='upgrade-request'
mkdir "$sandbox/good-disposable"
set +e
run_product upgrade \
    --candidate-id="$good_candidate" \
    --version=0.1.0 \
    --artifact-kind=native-onedir \
    --backup-destination="$sandbox/good-upgrade-backup" \
    --disposable-root="$sandbox/good-disposable" \
    --request-id=upgrade_123e4567-e89b-42d3-a456-426614174606 \
    --requested-at=2026-09-02T12:01:00Z \
    --confirm-owner \
    --json > "$sandbox/good-upgrade.json"
good_exit=$?
set -e
if [ "$good_exit" -ne 0 ]; then
    jq -c '{daemon_restore_state,failure_stage,rollback_state,status}' \
        "$sandbox/good-upgrade.json" >&2 || true
    fail
fi
stage='upgrade-receipt'
jq -e '.status == "upgraded"' "$sandbox/good-upgrade.json" >/dev/null || fail
stage='upgrade-activation-link'
[ "$(readlink "$install_root/current")" = "candidates/$good_candidate" ] || fail
stage='upgrade-restore-bytes'
good_backup_manifest=$sandbox/good-upgrade-backup/backup-manifest.json
[ -f "$good_backup_manifest" ] || fail
manifest_file_count=$(jq '[.files[] | select(.path | startswith("portable/"))] | length' \
    "$good_backup_manifest")
live_file_count=$(find \
    "$brain/brain.toml" \
    "$brain/content" \
    "$brain/history" \
    "$brain/sources" \
    -type f | wc -l | tr -d ' ')
[ "$manifest_file_count" = "$live_file_count" ] || fail
jq -r '.files[] | select(.path | startswith("portable/")) | .path' \
    "$good_backup_manifest" | while IFS= read -r backup_relative; do
    portable_relative=${backup_relative#portable/}
    case "$portable_relative" in
        ""|/*|..|../*|*/..|*/../*) fail ;;
    esac
    cmp "$sandbox/good-upgrade-backup/$backup_relative" \
        "$brain/$portable_relative" >/dev/null || fail
    cmp "$sandbox/good-upgrade-backup/$backup_relative" \
        "$sandbox/good-disposable/$portable_relative" >/dev/null || fail
done
stage='upgrade-doctor'
wait_status
jq -e '.doctor.state == "healthy"' "$sandbox/status.json" >/dev/null || fail

stage='uninstall'
run_product uninstall \
    --request-id=uninstall_123e4567-e89b-42d3-a456-426614174607 \
    --requested-at=2026-09-02T12:02:00Z \
    --confirm-owner \
    --json > "$sandbox/uninstall.json" || fail
jq -e '.status == "uninstalled"' "$sandbox/uninstall.json" >/dev/null || fail
[ ! -e "$install_root/current" ] && [ ! -L "$install_root/current" ] || fail
[ -d "$install_root/candidates" ] || fail
[ "$(find "$install_root/candidates" -mindepth 1 | wc -l | tr -d ' ')" = 0 ] || fail
[ "$(find "$install_root" \( -type f -o -type l \) | wc -l | tr -d ' ')" = 0 ] || fail
[ -f "$brain/brain.toml" ] || fail

stage='evidence'
mkdir -p "$(dirname -- "$evidence")"
evidence_next=$evidence.next.$$
jq -nS \
    --arg architecture "$architecture" \
    --arg artifact_sha256 "$actual_digest" \
    --arg host "$host" \
    --arg source_sha "$source_sha" \
    --argjson exact_signed_candidate "$exact_signed_candidate" \
    --argjson setup_seconds "$setup_seconds" \
    '{architecture:$architecture,artifact_sha256:$artifact_sha256,blocker_code:null,checks:{artifact_install:"passed",backup_disposable_restore_exact_bytes:"passed",doctor:"passed",portable_round_trip:"passed",prior_schema_upgrade:"passed",residue:"passed",rollback:"passed",source_checkout_required:false,system_python_required:false,uninstall:"passed",v0_gate_07:"passed",v0_gate_13:"passed"},exact_signed_candidate:$exact_signed_candidate,host:$host,setup_seconds:$setup_seconds,source_sha:$source_sha,status:"passed"}' \
    > "$evidence_next"
mv "$evidence_next" "$evidence"
chmod 644 "$evidence"

trap - EXIT HUP INT TERM
cleanup
printf '%s\n' '{"status":"passed"}'
