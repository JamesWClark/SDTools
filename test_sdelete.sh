#!/bin/bash
set -eu
set -o pipefail

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
script="$script_dir/sdelete.sh"
fixture=$(/usr/bin/mktemp -d -t sdelete-tests)
trap '/bin/rm -rf -- "$fixture"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

run_script() (
	function /usr/bin/pgrep() {
		[ "${TEST_APP_RUNNING:-false}" = true ]
	}
	function /usr/bin/defaults() {
		case "$1" in
			read) [ -f "$2.$3" ] ;;
			delete) /bin/rm -- "$2.$3" ;;
			*) return 1 ;;
		esac
	}
	function /usr/bin/killall() {
		return 0
	}
	function /usr/bin/find() {
		if [ "$2" = /Volumes ]; then
			if [ -n "${TEST_VOLUME:-}" ]; then
				printf '%s\0' "$TEST_VOLUME"
			fi
		elif [ "${TEST_TRASH_DENIED:-false}" = true ] && [ "$3" = "$HOME/.Trash" ]; then
			return 1
		else
			command /usr/bin/find "$@"
		fi
	}
	function /usr/sbin/diskutil() {
		[ "${TEST_UNKNOWN:-false}" != true ] || return 1
		if [ "$1" = apfs ]; then
			printf '%s\n' '<plist version="1.0"><dict><key>Snapshots</key><array><dict/></array></dict></plist>'
		else
			printf '%s\n' "<plist version=\"1.0\"><dict>
<key>FilesystemType</key><string>${TEST_FILESYSTEM:-apfs}</string>
<key>SolidState</key><${TEST_SSD:-true}/>
<key>Fusion</key><${TEST_FUSION:-false}/>
<key>FileVault</key><true/>
<key>ParentWholeDisk</key><string>disk0</string>
</dict></plist>"
		fi
	}
	function /usr/sbin/system_profiler() {
		printf '%s\n' '{"SPNVMeDataType":[{"_items":[{"bsd_name":"disk0","spnvme_trim_support":"Yes"},{"bsd_name":"disk99","spnvme_trim_support":"No"}]}]}'
	}
	function /bin/dd() {
		[ "${TEST_WRITE_FAILURE:-false}" != true ] || return 1
		command /bin/dd "$@"
	}
	function /bin/sync() {
		[ "${TEST_SYNC_FAILURE:-false}" != true ]
	}
	set -- "$@"
	source "$script"
)

expect_failure() {
	if "$@" > "$fixture/output" 2>&1; then
		printf 'Expected failure: %s\n' "$*" >&2
		exit 1
	fi
}

mkdir "$fixture/target" "$fixture/target/nested"
printf payload > "$fixture/target/nested/file"
run_script --dry-run "$fixture/target" > "$fixture/output"
test "$(cat "$fixture/target/nested/file")" = payload
grep -q 'disk0: Yes' "$fixture/output"
! grep -q 'disk99' "$fixture/output"
grep -q 'APFS snapshots on target volume: 1' "$fixture/output"
expect_failure run_script "$fixture/target" < /dev/null
test -f "$fixture/target/nested/file"
printf 'DELETE\n' | run_script "$fixture/target" > "$fixture/output"
test -d "$fixture/target"
test ! -e "$fixture/target/nested"
printf 'PASS: dry-run, target-backed diagnostics, confirmation, and root preservation\n'

for target_name in 'spaces and * glob' $'line\nbreak' $'trailing\n' '-leading'; do
	printf original > "$fixture/$target_name"
	exec 8< "$fixture/$target_name"
	run_script --yes -- "$fixture/$target_name" > "$fixture/output"
	test ! -e "$fixture/$target_name"
	test "$(cat <&8)" = original
	exec 8<&-
done
mkdir "$fixture/target"$'\n'
printf data > "$fixture/target"$'\n/file'
run_script --yes "$fixture/target"$'\n' > "$fixture/output"
test -d "$fixture/target"$'\n'
test ! -e "$fixture/target"$'\n/file'
printf 'PASS: unusual target names and SSD deletion without overwriting\n'

printf outside > "$fixture/outside"
ln -s "$fixture/outside" "$fixture/target/symlink"
ln "$fixture/outside" "$fixture/target/hardlink"
mkfifo "$fixture/target/pipe"
expect_failure run_script --yes "$fixture/target"
test "$(cat "$fixture/outside")" = outside
test -L "$fixture/target/symlink"
test -f "$fixture/target/hardlink"
test -p "$fixture/target/pipe"
expect_failure run_script --yes "$fixture/target/symlink"
expect_failure run_script --yes /
expect_failure run_script --yes "$HOME"
expect_failure run_script --yes /Volumes
printf 'PASS: symlink, hard-link, special-file, and dangerous-target safeguards\n'

printf '%0131079d' 0 > "$fixture/hdd"
cp "$fixture/hdd" "$fixture/expected"
exec 8< "$fixture/hdd"
TEST_FILESYSTEM=hfs TEST_SSD=false run_script --yes "$fixture/hdd" > "$fixture/output"
test ! -e "$fixture/hdd"
test "$(/usr/bin/stat -f '%z' <&8)" -eq 131079
if /usr/bin/cmp -s "$fixture/expected" - <&8; then
	printf 'HDD contents were not overwritten\n' >&2
	exit 1
fi
exec 8<&-
grep -q 'overwritten: 1' "$fixture/output"
printf '' > "$fixture/empty"
TEST_FILESYSTEM=hfs TEST_SSD=false run_script --yes "$fixture/empty" > "$fixture/output"
test ! -e "$fixture/empty"
printf 'PASS: real HDD-mode writes, exact byte length, and empty files\n'

printf preserved > "$fixture/write-failure"
TEST_FILESYSTEM=hfs TEST_SSD=false TEST_WRITE_FAILURE=true expect_failure run_script --yes "$fixture/write-failure"
test "$(cat "$fixture/write-failure")" = preserved
printf preserved > "$fixture/sync-failure"
TEST_FILESYSTEM=hfs TEST_SSD=false TEST_SYNC_FAILURE=true expect_failure run_script --yes "$fixture/sync-failure"
test -f "$fixture/sync-failure"
printf 'PASS: overwrite and flush failures retain files\n'

for storage in apfs fusion unknown; do
	printf original > "$fixture/$storage"
	exec 8< "$fixture/$storage"
	case "$storage" in
		apfs) TEST_SSD=false run_script --yes "$fixture/$storage" > "$fixture/output" ;;
		fusion) TEST_FILESYSTEM=hfs TEST_SSD=false TEST_FUSION=true run_script --yes "$fixture/$storage" > "$fixture/output" ;;
		unknown) TEST_UNKNOWN=true run_script --yes "$fixture/$storage" > "$fixture/output" ;;
	esac
	test ! -e "$fixture/$storage"
	test "$(cat <&8)" = original
	exec 8<&-
done
printf 'PASS: APFS HDD, Fusion, and unknown media avoid overwrites\n'

fake_home="$fixture/home"
recent="$fake_home/Library/Application Support/com.apple.sharedfilelist"
app_recent="$recent/com.apple.LSSharedFileList.ApplicationRecentDocuments"
preferences="$fake_home/Library/Preferences"
volume="$fixture/volume"
volume_trash="$volume/.Trashes/$(/usr/bin/id -u)"
mkdir -p "$app_recent" "$preferences" "$fake_home/.Trash/nested" "$volume_trash"
for app in quicktimeplayerx preview textedit safari chrome firefox; do
	printf recent > "$app_recent/com.apple.$app.sfl3"
done
printf folders > "$recent/com.apple.LSSharedFileList.RecentFolders.sfl3"
printf favorites > "$recent/com.apple.LSSharedFileList.FavoriteItems.sfl3"
printf recentapps > "$recent/com.apple.LSSharedFileList.RecentApplications.sfl3"
printf recentdocs > "$recent/com.apple.LSSharedFileList.RecentDocuments.sfl3"
printf recentservers > "$recent/com.apple.LSSharedFileList.RecentServers.sfl3"
printf oldrecent > "$preferences/com.apple.QuickTimePlayerX.NSRecentDocuments"
printf finderrecent > "$preferences/com.apple.finder.FXRecentFolders"
printf settings > "$preferences/com.apple.QuickTimePlayerX.other"
container_recent="$fake_home/Library/Containers/com.apple.QuickTimePlayerX/Data/Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments"
mkdir -p "$container_recent"
printf sandboxrecent > "$container_recent/com.apple.quicktimeplayerx.sfl2"
printf trash > "$fake_home/.Trash/nested/deleted"
printf external > "$volume_trash/deleted"
printf external > "$volume/.Trashes/another-user"
mkdir -p "$fake_home/Library/Safari" "$fake_home/Library/Caches/com.apple.Safari"
printf history > "$fake_home/Library/Safari/History.db"
printf cache > "$fake_home/Library/Caches/com.apple.Safari/data"

HOME="$fake_home" TEST_VOLUME="$volume" run_script --dry-run > "$fixture/output"
test -f "$fake_home/.Trash/nested/deleted"
test -f "$app_recent/com.apple.quicktimeplayerx.sfl3"
test -f "$recent/com.apple.LSSharedFileList.RecentApplications.sfl3"
test -f "$recent/com.apple.LSSharedFileList.RecentDocuments.sfl3"
test -f "$recent/com.apple.LSSharedFileList.RecentServers.sfl3"
test -f "$preferences/com.apple.QuickTimePlayerX.NSRecentDocuments"
HOME="$fake_home" TEST_VOLUME="$volume" expect_failure run_script < /dev/null
HOME="$fake_home" TEST_VOLUME="$volume" TEST_APP_RUNNING=true expect_failure run_script --yes
HOME="$fake_home" TEST_VOLUME="$volume" TEST_TRASH_DENIED=true expect_failure run_script --yes
test -f "$app_recent/com.apple.quicktimeplayerx.sfl3"
test -f "$volume_trash/deleted"
printf 'PASS: default preview, confirmation, running-app and access preflight\n'

printf targeted > "$fixture/explicit"
HOME="$fake_home" TEST_VOLUME="$volume" run_script --yes "$fixture/explicit" > "$fixture/output"
test ! -e "$fixture/explicit"
test -f "$fake_home/.Trash/nested/deleted"
test -f "$app_recent/com.apple.quicktimeplayerx.sfl3"
test -f "$preferences/com.apple.QuickTimePlayerX.NSRecentDocuments"
printf 'PASS: explicit path never runs default cleanup\n'

HOME="$fake_home" TEST_VOLUME="$volume" run_script --yes > "$fixture/output"
for app in quicktimeplayerx preview textedit; do
	test ! -e "$app_recent/com.apple.$app.sfl3"
done
test ! -e "$recent/com.apple.LSSharedFileList.RecentFolders.sfl3"
test ! -e "$recent/com.apple.LSSharedFileList.RecentApplications.sfl3"
test ! -e "$recent/com.apple.LSSharedFileList.RecentDocuments.sfl3"
test ! -e "$recent/com.apple.LSSharedFileList.RecentServers.sfl3"
test ! -e "$preferences/com.apple.QuickTimePlayerX.NSRecentDocuments"
test ! -e "$preferences/com.apple.finder.FXRecentFolders"
test ! -e "$container_recent/com.apple.quicktimeplayerx.sfl2"
test ! -e "$fake_home/.Trash/nested"
test ! -e "$volume_trash/deleted"
test -d "$fake_home/.Trash"
test -d "$volume_trash"
for app in safari chrome firefox; do
	test "$(cat "$app_recent/com.apple.$app.sfl3")" = recent
done
test "$(cat "$fake_home/Library/Safari/History.db")" = history
test "$(cat "$fake_home/Library/Caches/com.apple.Safari/data")" = cache
test "$(cat "$recent/com.apple.LSSharedFileList.FavoriteItems.sfl3")" = favorites
test "$(cat "$preferences/com.apple.QuickTimePlayerX.other")" = settings
test "$(cat "$volume/.Trashes/another-user")" = external
printf 'PASS: recent items and user Trash cleared; browsers, settings, favorites, and other users preserved\n'