
#!/bin/bash
set -u
set -o pipefail
umask 077

usage() {
	printf '%s\n' \
		"Usage: $0 [--dry-run] [-y|--yes] [--] [PATH]" \
		'' \
		'Without PATH: selected non-browser recent-item lists and your Trash.' \
		'With PATH: only that path; no additional application/system cleanup.' \
		'SSD/APFS/unknown storage: unlink files; macOS manages supported TRIM.' \
		'Confirmed non-Fusion HFS+ HDD: overwrite once, then unlink.' \
		'For a directory, process its contents but keep the target directory.' \
		'--dry-run      Preview without changing the target.' \
		'--yes         Skip the final confirmation.' \
		'' \
		'APFS copy-on-write, clones, snapshots, SSD wear leveling, backups, and' \
		'file metadata/resource forks can retain data that this cannot overwrite.' \
		'Additional overwrite passes do not solve these limitations.' \
		'Close applications using the target; do not run on a changing/untrusted tree.' \
		'Symlinks, hard-linked files, special files, and other filesystems are skipped.'
}

fail() {
	printf 'Error: %s\n' "$*" >&2
	exit 1
}

dry_run=false
skip_confirm=false
while [ "$#" -gt 0 ]; do
	case "$1" in
		--dry-run) dry_run=true ;;
		-y|--yes) skip_confirm=true ;;
		-h|--help) usage; exit 0 ;;
		--) shift; break ;;
		-*) usage >&2; fail "Unknown option: $1" ;;
		*) break ;;
	esac
	shift
done
[ "$#" -le 1 ] || { usage >&2; exit 1; }
[ "$(/usr/bin/uname -s)" = Darwin ] || fail 'This script requires macOS.'

clean_path() (
target=$1
while [ "$target" != / ] && [ "${target%/}" != "$target" ]; do
	target=${target%/}
done
[ ! -L "$target" ] || fail 'The target must not be a symbolic link.'
if [ -d "$target" ]; then
	target=$(cd -P -- "$target" && printf '%s.' "$PWD") || fail 'Cannot resolve target directory.'
	target=${target%.}
elif [ -f "$target" ]; then
	case "$target" in /*) ;; *) target="$PWD/$target" ;; esac
	parent=$(cd -P -- "${target%/*}/" && printf '%s.' "$PWD") || fail 'Cannot resolve parent directory.'
	target="${parent%.}/${target##*/}"
else
	fail 'Target must be an existing regular file or directory.'
fi

case "$target" in
	/|/Users|/Volumes|/System|/Library|/Applications|/usr|/bin|/sbin|/dev|/private|/private/etc|/private/var|/Network|/cores|/opt)
		fail 'Refusing a system or top-level directory.' ;;
esac
home_path=$(cd -- "$HOME" && pwd -P) || fail 'Cannot resolve home directory.'
[ ! "$target" -ef "$HOME" ] || fail 'Refusing your home directory.'
case "$home_path/" in
	"$target/"*) fail 'Refusing your home directory or one of its ancestors.' ;;
esac
target_device=$(/usr/bin/stat -f '%d' "$target") || fail 'Cannot inspect target.'
parent_device=$(/usr/bin/stat -f '%d' "$target/.." 2>/dev/null) || parent_device=$target_device
[ "$target_device" = "$parent_device" ] || fail 'Refusing a volume root.'

plist_value() {
	printf '%s' "$1" | /usr/bin/plutil -extract "$2" raw -o - - 2>/dev/null
}

volume_device=$(/bin/df -P "$target" | /usr/bin/awk 'NR == 2 {print $1}') || volume_device=''
volume_info=$(/usr/sbin/diskutil info -plist "$volume_device" 2>/dev/null) || volume_info=''
filesystem=$(plist_value "$volume_info" FilesystemType) || filesystem=unknown
solid_state=$(plist_value "$volume_info" SolidState) || solid_state=unknown
fusion=$(plist_value "$volume_info" Fusion) || fusion=unknown
encrypted=$(plist_value "$volume_info" FileVault) || encrypted=unknown

physical_disks=''
store_index=0
while physical_store=$(plist_value "$volume_info" "APFSPhysicalStores.$store_index.APFSPhysicalStore"); do
	store_info=$(/usr/sbin/diskutil info -plist "$physical_store" 2>/dev/null) || store_info=''
	if whole_disk=$(plist_value "$store_info" ParentWholeDisk); then
		physical_disks="${physical_disks}${whole_disk},"
	fi
	store_index=$((store_index + 1))
done
if [ "$store_index" -eq 0 ]; then
	physical_disks=$(plist_value "$volume_info" ParentWholeDisk) || physical_disks=''
fi
trim_report=unknown
if [ -n "$physical_disks" ]; then
	if storage_json=$(LC_ALL=C /usr/sbin/system_profiler SPNVMeDataType SPSerialATADataType -json 2>/dev/null); then
		trim_report=$(/usr/bin/osascript -l JavaScript -e '
function run(args) {
    var disks = args[1].split(",").filter(Boolean);
    var reports = {};
    function visit(node) {
        if (!node || typeof node !== "object") return;
        if (disks.indexOf(node.bsd_name) !== -1) {
            var trim = node.spnvme_trim_support || node.spsata_trim_support;
            if (trim) reports[node.bsd_name] = String(trim);
        }
        Object.keys(node).forEach(function (key) { visit(node[key]); });
    }
    visit(JSON.parse(args[0]));
    return disks.map(function (disk) {
        return disk + ": " + (reports[disk] || "unknown");
    }).join("; ");
}' "$storage_json" "$physical_disks" 2>/dev/null) || trim_report=unknown
	fi
fi

snapshot_count=unknown
if [ "$filesystem" = apfs ]; then
	snapshot_info=$(/usr/sbin/diskutil apfs listSnapshots -plist "$volume_device" 2>/dev/null) || snapshot_info=''
	if snapshots_json=$(printf '%s' "$snapshot_info" | /usr/bin/plutil -extract Snapshots json -o - - 2>/dev/null); then
		snapshot_count=$(/usr/bin/osascript -l JavaScript -e \
			'function run(args) { return JSON.parse(args[0]).length; }' "$snapshots_json" 2>/dev/null) || snapshot_count=unknown
	fi
fi
overwrite=false
if [ "$filesystem" = hfs ] && [ "$solid_state" = false ] && [ "$fusion" = false ]; then
	overwrite=true
fi

printf 'Target: %q\n' "$target"
printf 'Filesystem: %s; SSD: %s; FileVault: %s\n' "$filesystem" "$solid_state" "$encrypted"
printf 'Reported TRIM support (not erase completion): %s\n' "$trim_report"
if [ "$filesystem" = apfs ]; then
	printf 'APFS snapshots on target volume: %s (left untouched)\n' "$snapshot_count"
fi
if "$overwrite"; then
	printf '%s\n' 'Mode: one random overwrite pass, then unlink (HFS+ HDD).'
else
	printf '%s\n' 'Mode: logical deletion without overwriting (SSD/APFS/unknown storage).'
fi
printf '%s\n' 'WARNING: Physical secure erasure is NOT guaranteed.'
printf '%s\n' 'Snapshots, clones, backups, SSD remnants, and metadata may retain data.'
printf '%s\n' 'TRIM is managed by macOS; this script cannot force or verify per-file flash erasure.'
printf '%s\n' 'FileVault protects locked storage; deleting files does not destroy the volume key.'
if ! "$dry_run" && ! "$skip_confirm"; then
	printf 'Delete the selected contents using the mode above? Type DELETE: '
	IFS= read -r answer || fail 'Confirmation required; nothing changed.'
	[ "$answer" = DELETE ] || fail 'Cancelled; nothing changed.'
fi

manifest=$(/usr/bin/mktemp -t sdelete) || fail 'Cannot create traversal manifest.'
trap '/bin/rm -f -- "$manifest"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
manifest_parent=$(cd -- "$(/usr/bin/dirname -- "$manifest")" && pwd -P) || fail 'Cannot resolve temporary directory.'
case "$manifest_parent/" in
	"$target/"*) fail 'Temporary directory is inside the target; set TMPDIR outside it.' ;;
esac

if [ -d "$target" ]; then
	/usr/bin/find -P -x "$target" -depth -mindepth 1 -print0 > "$manifest" || fail 'Traversal failed; nothing changed.'
else
	printf '%s\0' "$target" > "$manifest" || fail 'Cannot write manifest.'
fi

overwrite_file() {
	local file=$1 identity=$2 size=$3 opened current blocks remainder
	exec 3<> "$file" || return 1
	opened=$(/usr/bin/stat -f '%d:%i:%l:%z' <&3) || { exec 3>&-; return 1; }
	if [ "$opened" != "$identity" ] || [ -L "$file" ]; then
		exec 3>&-
		return 1
	fi
	blocks=$((size / 65536))
	remainder=$((size % 65536))
	if ! /bin/dd if=/dev/urandom bs=65536 count="$blocks" >&3 2>/dev/null ||
		! /bin/dd if=/dev/urandom bs=1 count="$remainder" >&3 2>/dev/null ||
		! /bin/sync; then
		exec 3>&-
		return 1
	fi
	current=$(/usr/bin/stat -f '%d:%i:%l:%z' <&3) || { exec 3>&-; return 1; }
	exec 3>&-
	[ "$current" = "$identity" ] && [ ! -L "$file" ] &&
		[ "$(/usr/bin/stat -f '%d:%i:%l:%z' "$file")" = "$identity" ] || return 1
	/bin/rm -- "$file" < /dev/null
}

deleted=0
overwritten=0
removed_dirs=0
planned=0
errors=0
while IFS= read -r -d '' entry; do
	if [ -L "$entry" ]; then
		printf 'Skipped symbolic link: %q\n' "$entry" >&2
		errors=$((errors + 1))
		continue
	fi
	identity=$(/usr/bin/stat -f '%d:%i:%l:%z' "$entry") || { errors=$((errors + 1)); continue; }
	IFS=: read -r device inode links size <<< "$identity"
	if [ "$device" != "$target_device" ]; then
		printf 'Skipped other filesystem: %q\n' "$entry" >&2
		errors=$((errors + 1))
	elif [ -d "$entry" ]; then
		if "$dry_run"; then
			printf 'Would remove directory if empty: %q\n' "$entry"
		elif /bin/rmdir -- "$entry"; then
			removed_dirs=$((removed_dirs + 1))
		else
			errors=$((errors + 1))
		fi
	elif [ ! -f "$entry" ] || [ "$links" -ne 1 ]; then
		printf 'Skipped special or hard-linked file: %q\n' "$entry" >&2
		errors=$((errors + 1))
	elif "$dry_run"; then
		if "$overwrite"; then
			printf 'Would overwrite %s bytes and unlink: %q\n' "$size" "$entry"
		else
			printf 'Would unlink without overwriting: %q\n' "$entry"
		fi
		planned=$((planned + 1))
	elif "$overwrite"; then
		printf 'Overwriting %s bytes: %q\n' "$size" "$entry"
		if overwrite_file "$entry" "$identity" "$size"; then
			deleted=$((deleted + 1))
			overwritten=$((overwritten + 1))
		else
			printf 'Failed; file not intentionally unlinked (may be partially overwritten): %q\n' "$entry" >&2
			errors=$((errors + 1))
		fi
	else
		printf 'Unlinking without overwriting: %q\n' "$entry"
		if [ ! -L "$entry" ] && [ "$(/usr/bin/stat -f '%d:%i:%l:%z' "$entry")" = "$identity" ] &&
			/bin/rm -- "$entry" < /dev/null; then
			deleted=$((deleted + 1))
		else
			errors=$((errors + 1))
		fi
	fi
done < "$manifest"

if ! "$dry_run" && [ "$deleted" -gt 0 ]; then
	/bin/sync || errors=$((errors + 1))
fi
printf 'Unlinked: %s; overwritten: %s; directories removed: %s; preview files: %s; skipped/errors: %s\n' \
	"$deleted" "$overwritten" "$removed_dirs" "$planned" "$errors"
printf '%s\n' 'These counts do not certify physical erasure.'
[ "$errors" -eq 0 ]
)

collect_volume_trash() {
	local volume current_uid volume_manifest
	current_uid=$(/usr/bin/id -u) || return 1
	volume_manifest=$(/usr/bin/mktemp -t sdelete-volumes) || return 1
	if ! /usr/bin/find -P /Volumes -mindepth 1 -maxdepth 1 -type d -print0 > "$volume_manifest"; then
		/bin/rm -f -- "$volume_manifest"
		return 1
	fi
	while IFS= read -r -d '' volume; do
		cleanup_paths+=("$volume/.Trashes/$current_uid")
	done < "$volume_manifest"
	/bin/rm -f -- "$volume_manifest"
}

default_cleanup() {
	local recent_root app bundle list_bundle extension candidate pref key answer cleanup_errors=0
	local cleanup_paths=() preference_paths=() preference_keys=()
	local app_names=('QuickTime Player' 'Preview' 'TextEdit')
	local bundles=('com.apple.QuickTimePlayerX' 'com.apple.Preview' 'com.apple.TextEdit')
	local app_index
	recent_root="$HOME/Library/Application Support/com.apple.sharedfilelist"
	printf '%s\n' 'Default cleanup: QuickTime/Preview/TextEdit recent files, Finder recent folders, and your Trash.'
	printf '%s\n' 'Browser profiles, history, caches, sessions, and global recent-app/document lists are excluded.'
	printf '%s\n' 'Trash includes anything you placed there, including any previously trashed browser files.'
	printf '%s\n' 'Physical erasure is not guaranteed on SSD/APFS; the storage-aware path mode applies.'
	for app_index in 0 1 2; do
		app=${app_names[$app_index]}
		bundle=${bundles[$app_index]}
		list_bundle=$(printf '%s' "$bundle" | /usr/bin/tr '[:upper:]' '[:lower:]')
		if /usr/bin/pgrep -u "$(/usr/bin/id -u)" -x "$app" > /dev/null; then
			printf 'Close %s before cleanup; recent items can otherwise be recreated.\n' "$app" >&2
			if ! "$dry_run"; then
				return 1
			fi
		fi
		for extension in sfl sfl2 sfl3; do
			cleanup_paths+=("$recent_root/com.apple.LSSharedFileList.ApplicationRecentDocuments/$list_bundle.$extension")
			cleanup_paths+=("$HOME/Library/Containers/$bundle/Data/Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments/$list_bundle.$extension")
		done
		for pref in "$HOME/Library/Preferences/$bundle" "$HOME/Library/Containers/$bundle/Data/Library/Preferences/$bundle"; do
			if /usr/bin/defaults read "$pref" NSRecentDocuments > /dev/null 2>&1; then
				preference_paths+=("$pref")
				preference_keys+=(NSRecentDocuments)
			fi
		done
	done
	pref="$HOME/Library/Preferences/com.apple.finder"
	if /usr/bin/defaults read "$pref" FXRecentFolders > /dev/null 2>&1; then
		preference_paths+=("$pref")
		preference_keys+=(FXRecentFolders)
	fi
	for extension in sfl sfl2 sfl3; do
		cleanup_paths+=("$recent_root/com.apple.LSSharedFileList.RecentFolders.$extension")
	done
	cleanup_paths+=("$HOME/.Trash")
	collect_volume_trash || return 1
	for candidate in "${cleanup_paths[@]}"; do
		if [ -e "$candidate" ] || [ -L "$candidate" ]; then
			printf 'Cleanup target: %q\n' "$candidate"
			if [ -L "$candidate" ]; then
				printf 'Refusing linked cleanup target: %q\n' "$candidate" >&2
				cleanup_errors=$((cleanup_errors + 1))
			elif [ -d "$candidate" ]; then
				if ! /usr/bin/find -P -x "$candidate" -mindepth 1 -print > /dev/null; then
					cleanup_errors=$((cleanup_errors + 1))
				fi
			elif [ ! -r "$candidate" ]; then
				printf 'Cannot read cleanup target: %q\n' "$candidate" >&2
				cleanup_errors=$((cleanup_errors + 1))
			fi
		fi
	done
	if [ "$cleanup_errors" -ne 0 ]; then
		printf '%s\n' 'Preflight failed; nothing changed. Check permissions and Full Disk Access for Terminal/VS Code.' >&2
		return 1
	fi
	for ((app_index=0; app_index<${#preference_paths[@]}; app_index++)); do
		printf 'Recent-item preference: %s in %q\n' "${preference_keys[$app_index]}" "${preference_paths[$app_index]}"
	done
	if ! "$dry_run" && ! "$skip_confirm"; then
		printf 'Clear the listed recent items and empty your Trash? Type DELETE: '
		IFS= read -r answer || return 1
		[ "$answer" = DELETE ] || return 1
	fi
	for candidate in "${cleanup_paths[@]}"; do
		if [ -e "$candidate" ] || [ -L "$candidate" ]; then
			if ! (skip_confirm=true; clean_path "$candidate"); then
				cleanup_errors=$((cleanup_errors + 1))
			fi
		fi
	done
	for ((app_index=0; app_index<${#preference_paths[@]}; app_index++)); do
		pref=${preference_paths[$app_index]}
		key=${preference_keys[$app_index]}
		if "$dry_run"; then
			printf 'Would clear preference %s in %q\n' "$key" "$pref"
		elif ! /usr/bin/defaults delete "$pref" "$key"; then
			cleanup_errors=$((cleanup_errors + 1))
		fi
	done
	printf '%s\n' 'Recent-item services may cache lists until logout/login. No browser data or backups were targeted.'
	printf 'Default cleanup failed targets: %s\n' "$cleanup_errors"
	[ "$cleanup_errors" -eq 0 ]
}

if [ "$#" -eq 0 ]; then
	default_cleanup
else
	clean_path "$1"
fi
