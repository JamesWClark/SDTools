
#!/bin/bash
# Securely overwrite and delete all files and subfolders in a given directory, but not the directory itself
# Usage: ./sdelete.sh /path/to/folder

if [ -z "$1" ]; then
	echo "Usage: $0 /path/to/folder"
	exit 1
fi

TARGET_DIR="$1"

if [ ! -d "$TARGET_DIR" ]; then
	echo "Error: $TARGET_DIR is not a directory."
	exit 1
fi


# Get a list of all files and count them
total=$(find "$TARGET_DIR" -mindepth 1 -type f | wc -l)
count=0

find "$TARGET_DIR" -mindepth 1 -type f | while read -r file; do
	count=$((count+1))
	echo "$count/$total: Overwriting $file"
	dd if=/dev/urandom of="$file" bs=1m count=$(du -m "$file" | cut -f1) conv=notrunc status=none
done

# Delete all contents (files and subfolders), but not the directory itself
find "$TARGET_DIR" -mindepth 1 -delete
