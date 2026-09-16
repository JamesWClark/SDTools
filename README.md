# Image Resize & Processing Script

A Python utility for batch resizing, formatting, and adjusting images with various options for brightness, saturation, and output modes.

## Installation

### Dependencies

```bash
pip install pillow
```

### Optional (for additional format support)

```bash
pip install pillow-avif-plugin pillow-heif
```

## Quick Start

```bash
python resize.py "C:\images" `
  --recursive `
  --alongside `
  --clean `
  --preserve-size `
  --meta-forge `
  --target_ext .webp
```

## Basic Usage

### Simple Resize

Resize images to fit between min and max dimensions while maintaining aspect ratio:

```bash
python resize.py "C:\images" --min_dimension 1600 --max_dimension 2048 --target_ext .jpg
```

The default now preserves source dimensions. Use `--fit-range` to opt into the legacy 1600-to-2048 dimension bounds:

```bash
python resize.py "C:\images" --fit-range --target_ext .webp
```

Use `--min_dimension` and/or `--max_dimension` for custom bounds.

### Recursive Sibling Conversion

To create the converted copy beside each source image, use `--alongside`. Add `--recursive` to include nested folders. Existing destination files are skipped and listed at the end; no source or output file is overwritten.

```bash
python resize.py "C:\images" --recursive --alongside --preserve-size --meta-forge --target_ext .webp
```

Add `--clean` to securely delete each original only after its converted alongside file is saved. This requires `sdelete` to be installed and available in `PATH`:

```bash
python resize.py "C:\images" --recursive --alongside --clean --preserve-size --meta-forge --target_ext .webp
```

If conversion fails, an output already exists, or secure deletion fails, the source is kept.

Without `--alongside`, `--recursive` mirrors the input folder structure below `--output_dir`:

```bash
python resize.py "C:\images" --recursive --output_dir "C:\converted" --target_ext .webp
```

### Change Output Format

Specify the output format as a positional argument or use `--target_ext`:

```bash
# Positional format argument
python resize.py "C:\images" .png
python resize.py "C:\images" --brightness 1.3 .webp

# Using --target_ext flag
python resize.py "C:\images" --target_ext .png
```

Supported formats: `.jpg`, `.png`, `.webp`, `.avif`, `.heic`

### Preserve Generation Metadata

Use `--meta-forge` to copy a source image's raw `parameters` metadata to the converted file:

```bash
python resize.py "C:\images" --meta-forge --preserve-size --target_ext .avif
```

`--preserve-size` skips the default min/max dimension processing and keeps each source image's dimensions. `--no-resize` is an alias. The flag cannot be combined with `--box`. The text is preserved without reformatting. PNG stores it in the `parameters` text field, JPEG stores it as a comment, and WebP, AVIF, and HEIC store it in EXIF `UserComment`. `.avi` is a video format; use `.avif` for AV1 still-image conversion.

### Adjust Brightness

Lighten or darken images:

```bash
# Moderately lighter (recommended for dark/dusk-tinted images)
python resize.py "C:\images" --brightness 1.3 .png

# Various brightness levels
python resize.py "C:\images" --brightness 1.5 .jpg    # Noticeably lighter
python resize.py "C:\images" --brightness 1.8 .webp   # Significantly lighter
python resize.py "C:\images" --brightness 0.7 .png    # Darker
```

**Brightness values:**

- `1.0` = original (no change)
- `>1.0` = lighter
- `<1.0` = darker
- Suggested starting point for dark images: `1.3`

### Adjust RGB Color Channels

Reduce or amplify individual color channels to correct color casts:

```bash
# Reduce red (useful for removing reddish/warm tint)
python resize.py "C:\images" --red 0.8 .png

# Reduce blue (useful for removing blueish/cool tint like your dusk-tinted images)
python resize.py "C:\images" --blue 0.7 .png

# Boost green
python resize.py "C:\images" --green 1.2 .jpg

# Combine adjustments: brighten AND reduce blue cast
python resize.py "C:\images" --brightness 1.3 --blue 0.75 .png

# Adjust all three channels
python resize.py "C:\images" --red 0.9 --green 1.1 --blue 0.8 .webp
```

**RGB channel values:**

- `1.0` = original (no change)
- `>1.0` = amplify that color (brighter in that channel)
- `<1.0` = reduce that color (darker in that channel)
- Typical range: `0.5` to `1.5` for most adjustments

**Common use cases:**

- **Blueish/dusk tint** (like your image): Use `--blue 0.7` or `--blue 0.8`
- **Too much red/warm**: Use `--red 0.8` or `--red 0.9`
- **Too much green**: Use `--green 0.8`
- **Too pale**: Use higher multipliers like `--blue 1.3 --red 1.2`

## Advanced Options

### Fixed Box Size (Exact Output Dimensions)

Force output to exact width × height using `--box_mode`:

#### Cover Mode (Scale + Crop)

Scales image to fill the box completely, then center-crops excess. Output is always the exact box size, but image content may be cropped.

```bash
python resize.py "C:\images" --box 512 512 --box_mode cover --target_ext .jpg
```

#### Contain Mode (Scale + Pad)

Scales image to fit inside the box, then pads the remaining space with a color. Output is exact box size with padding.

```bash
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color "#202020" --target_ext .png

# Transparent padding (for .png or .webp)
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color transparent --target_ext .png
```

#### Clip Mode (No Scaling, Crop/Pad Only)

No scaling. Crops oversized images from center, pads undersized images. Output is exact box size.

```bash
python resize.py "C:\images" --box 512 512 --box_mode clip --pad_color black --target_ext .png
```

### Padding Color

Used with `--box_mode contain` or `--box_mode clip`:

```bash
# Named colors
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color black
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color white

# Hex colors
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color "#202020"
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color "#FF00FF"

# Transparent (for alpha-capable formats like .png, .webp, .avif)
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color transparent --target_ext .png
```

### Output Directory

```bash
# Default: creates "<input_dir>/resized-images-resize-py"
python resize.py "C:\images"

# Specify custom output directory
python resize.py "C:\images" --output_dir "C:\output\my_resized_images"
```

### Rename Output Files

Rename output files to folder_name with numbered suffixes:

```bash
python resize.py "C:\images\my_folder" --rename
# Output: my_folder (1).jpg, my_folder (2).jpg, my_folder (3).jpg, etc.

# Combined with other options
python resize.py "C:\images\my_folder" --rename --brightness 1.3 .png
```

### Flip Images

Flip images horizontally or vertically:

```bash
# Horizontal flip
python resize.py "C:\images" --flip_horizontal --target_ext .jpg

# Vertical flip
python resize.py "C:\images" --flip_vertical --target_ext .jpg

# When using flip, output is just the flipped images (no resizing)
```

## Combined Examples

### Example 1: Create Square Thumbnails with Transparent Padding

```bash
python resize.py "C:\images" --box 512 512 --box_mode contain --pad_color transparent --target_ext .png
```

### Example 2: Lighten Dark Images and Convert to WebP

```bash
python resize.py "C:\images" --brightness 1.3 --min_dimension 1600 --max_dimension 2048 .webp
```

### Example 2b: Fix Blueish/Dusk-Tinted Images (Like Your Sample)

```bash
# Reduce blue cast and brighten
python resize.py "E:\Training\Pending\0_GO\LouisianeGouverneur\color" --brightness 1.3 --blue 0.75 .png

# Or for more aggressive correction
python resize.py "E:\Training\Pending\0_GO\LouisianeGouverneur\color" --brightness 1.4 --blue 0.7 --red 1.1 .png
```

### Example 3: Resize, Lighten, and Rename with Custom Output

```bash
python resize.py "C:\images\photos" --brightness 1.4 --rename --output_dir "C:\output\bright_photos" .jpg
```

### Example 4: Fit to Box and Rename

```bash
python resize.py "C:\images\portraits" --box 300 400 --box_mode contain --pad_color black --rename .jpg
```

## Help & Examples

View built-in documentation:

```bash
python resize.py --help              # Standard help
python resize.py --help-verbose      # Detailed help with examples
python resize.py --examples          # Just the examples
```

## Parameter Reference

| Parameter                 | Type         | Default                                 | Description                                                               |
| ------------------------- | ------------ | --------------------------------------- | ------------------------------------------------------------------------- |
| `dir_path`              | path         | (required)                              | Directory containing images to process                                    |
| `target_ext_positional` | string       | (optional)                              | Output format as positional arg (e.g.,`.png`, `jpg`)                  |
| `--target_ext`          | string       | `.jpg`                                | Output format:`.jpg`, `.png`, `.webp`, `.avif`, `.heic`         |
| `--output_dir`          | path         | `<dir_path>/resized-images-resize-py` | Where to save processed images                                            |
| `--recursive`           | flag         | (false)                                 | Include images in nested directories                                      |
| `--alongside`           | flag         | (false)                                 | Write outputs beside sources; skip and report existing destinations       |
| `--clean`               | flag         | (false)                                 | With `--alongside`, securely delete each source after successful conversion |
| `--min_dimension`       | int          | (none)                                  | Minimum width/height to upscale to when supplied                          |
| `--max_dimension`       | int          | (none)                                  | Maximum width/height to downscale to when supplied                        |
| `--fit-range`           | flag         | (false)                                 | Apply the legacy 1600-to-2048 dimension bounds                            |
| `--brightness`          | float        | `1.0`                                 | Brightness multiplier (1.0=original, >1.0=lighter, <1.0=darker)           |
| `--box`                 | WIDTH HEIGHT | (none)                                  | Force exact output size (overrides min/max resizing)                      |
| `--box_mode`            | choice       | `clip`                                | How to fit into box:`clip`, `cover`, `contain`                      |
| `--pad_color`           | string       | `black`                               | Color for padding when using`--box_mode contain/clip`                   |
| `--brightness`          | float        | `1.0`                                 | Brightness multiplier (1.0=original, >1.0=lighter, <1.0=darker)           |
| `--red`                 | float        | `1.0`                                 | Red channel multiplier (1.0=original, >1.0=more red, <1.0=less red)       |
| `--green`               | float        | `1.0`                                 | Green channel multiplier (1.0=original, >1.0=more green, <1.0=less green) |
| `--blue`                | float        | `1.0`                                 | Blue channel multiplier (1.0=original, >1.0=more blue, <1.0=less blue)    |
| `--meta-forge`          | flag         | (false)                                 | Preserve source`parameters` metadata in the converted output            |
| `--rename`              | flag         | (false)                                 | Rename outputs to`folder_name (1)`, `folder_name (2)`, etc.           |
| `--flip_horizontal`     | flag         | (false)                                 | Flip images left-to-right                                                 |
| `--flip_vertical`       | flag         | (false)                                 | Flip images top-to-bottom                                                 |

## Brightness Adjustment Examples

For the dark/dusk-tinted image in the attachment:

- **Start with `--brightness 1.3`** for moderate lightening
- **Increase to `1.5`** if still too dark
- **Use `1.2`** if too washed out at 1.3

```bash
# Test different brightness levels
python resize.py "E:\Training\Pending\0_GO\LouisianeGouverneur\color" --brightness 1.2 .png
python resize.py "E:\Training\Pending\0_GO\LouisianeGouverneur\color" --brightness 1.3 .png
python resize.py "E:\Training\Pending\0_GO\LouisianeGouverneur\color" --brightness 1.5 .png
```

## RGB Color Correction Examples

For images with strong color casts:

```bash
# Remove blueish tint (dusk/cool lighting)
python resize.py "C:\images" --blue 0.7 .png
python resize.py "C:\images" --blue 0.75 .png  # Less aggressive

# Remove reddish/warm tint
python resize.py "C:\images" --red 0.8 .png

# Combine brightness + color correction
python resize.py "C:\images" --brightness 1.3 --blue 0.75 .png

# Test different blue reduction levels
python resize.py "C:\images" --blue 0.6 .png  # Very strong reduction
python resize.py "C:\images" --blue 0.75 .png  # Moderate
python resize.py "C:\images" --blue 0.9 .png  # Slight
```

## Notes

- `--box` overrides `--min_dimension` and `--max_dimension`
- When using `--flip_horizontal` or `--flip_vertical`, only flipping is performed (no resizing)
- Aspect ratio is maintained during resize unless using `--box_mode cover`
- JPEG files are always converted to RGB mode
- PNG and WebP support alpha transparency (use with `--pad_color transparent`)
- Original image orientation (EXIF) is automatically corrected before processing

# macOS File Cleanup

[sdelete.sh](sdelete.sh) accepts an optional file or directory. With a path, it operates only on that path: no application cleanup or Trash emptying is added. For directories, it deletes descendants but keeps the requested directory. It uses the tools included with current macOS; no Homebrew packages are required.

```bash
bash sdelete.sh --dry-run "/path/to/folder"
bash sdelete.sh "/path/to/folder"
bash sdelete.sh --yes "/path/to/file-or-folder"
```

The default run reports the storage type, FileVault status, reported TRIM support for the backing disks, and the target volume's APFS snapshot count where available. It then asks you to type `DELETE`. `--yes` skips confirmation; no other opt-in flag is required. Dry-run changes nothing in the target.

## No-Path Cleanup

```bash
bash sdelete.sh --dry-run
bash sdelete.sh
bash sdelete.sh --yes
```

Without a path, the script previews its selected targets and asks for one confirmation before cleaning:

- QuickTime Player, Preview, and TextEdit application recent-document lists (`sfl`, `sfl2`, and `sfl3`), including known sandbox locations and legacy `NSRecentDocuments` preferences.
- Finder recent-folder lists and the `FXRecentFolders` preference, preserving sidebar favorites and other settings.
- Apple menu Recent Items: recent applications, documents, and servers from the `com.apple.LSSharedFileList.Recent*.sfl*` shared-file lists.
- The contents of your home Trash and your numeric-user-ID Trash on volumes mounted directly under `/Volumes`. Other users' Trash is excluded. Trash uses the same SSD/HDD-aware deletion as explicit paths, not a stronger physical-erasure method.

Browser profiles, history, caches, sessions, and browser recent-document lists are not targeted. General application caches, saved sessions, autosaves, and application containers are not swept. Run no-path cleanup as the logged-in GUI user; running it from `sudo su` targets root's home and cannot clear that user's Apple menu. This is an explicit allowlist, not automatic cleanup of every installed app. Emptying Trash necessarily includes any browser files you previously placed in Trash.

Quit QuickTime Player, Preview, and TextEdit first; an active app blocks destructive default cleanup to reduce recent-list recreation. Target access is checked before any changes. If macOS denies Trash or Library access, grant your terminal application (or VS Code for its integrated terminal) **Full Disk Access** in System Settings > Privacy & Security, then restart it and retry the preview. The script does not request elevation or bypass macOS privacy controls. Permission changes during cleanup can still cause partial completion.

Recent-item services and Finder can cache menus until logout/login. The script does not forcibly restart shared services, Finder, or applications. Preference-key deletion is logical, not secure erasure of old plist extents. Missing known lists are skipped; this does not prove every app/version-specific history store has been cleared. Symlinks, hard links, and special files retain the normal safety policy and can prevent Trash from being completely emptied; they are reported as skips/errors.

## Storage-Aware Defaults

- **SSD, APFS, Fusion, or unknown storage:** logical deletion without overwriting. macOS manages TRIM on supported storage. Overwriting cannot reliably reach old SSD blocks or APFS copy-on-write extents, and creates unnecessary writes.
- **Confirmed non-Fusion HFS+ spinning disk:** one random overwrite pass over the file's exact logical length, flush, then unlink. This is still not a physical-erasure guarantee and does not securely overwrite extended attributes, resource forks, or filesystem metadata.
- **Safety:** refuse system/top-level targets, volume roots, and your home directory. Do not follow symlinks or cross filesystems. Retain and report hard-linked files, special files, and overwrite failures. Remove directories only when empty. Skips or failures produce a nonzero exit status.

Close applications using the target first. Shell pathname checks are not atomic: this script is not safe against concurrent renames, mounts, or a malicious process changing the tree. Files held open elsewhere can remain readable after unlinking. A failed overwrite can leave a partially overwritten file.

## What TRIM Does Not Guarantee

TRIM tells the storage controller that filesystem blocks are no longer needed. Reported support does not prove that TRIM was issued for a particular file, or that the controller has physically erased its flash cells. Snapshots and clones can keep blocks allocated. An unknown report is not evidence that TRIM is disabled; some enclosures and storage stacks do not expose the information.

There is no supported per-file macOS command that this script can use to force and verify flash erasure. `sync` is not such a command. The script does not invoke `trimforce`, erase free space, or delete snapshots or backups. `trimforce` changes system-wide TRIM support for certain third-party AHCI drives, requires a reboot, and carries compatibility risks; it is not a per-file erase operation. Windows SDelete plus enabled NTFS TRIM has the same fundamental SSD wear-leveling limitation.

**For stronger protection:** enable FileVault before storing sensitive data. FileVault protects locked storage, but ordinary file deletion does not destroy its volume key or make retained copies inaccessible while unlocked. Keep highly sensitive future data in separately encrypted storage with independently managed keys, and account for backups, snapshots, exports, and application caches. For retiring a supported Mac, use Apple's Erase All Content and Settings workflow, which destroys encryption keys for the erased data; this is a whole-device workflow, not selective file deletion. Already-written unencrypted SSD data cannot be reliably sanitized file by file by this script.

Run the disposable-fixture regression tests on macOS:

```bash
bash test_sdelete.sh
```

Tests mock disk reports and failures while performing real writes/deletions only in a fresh temporary directory. They do not certify physical erasure or exercise real HDD firmware or mounted external-volume boundaries.

# Secure Cleaner Script

`clean.py` is a Windows cleanup utility that uses Microsoft Sysinternals SDelete to securely remove existing files. It also checks that NTFS TRIM is enabled before cleanup. If TRIM is disabled, the script can request administrator access to enable it and then verifies the setting again.

## Cleaner Prerequisites

- Windows 10 or later
- [Microsoft Sysinternals SDelete](https://learn.microsoft.com/sysinternals/downloads/sdelete) available on `PATH`
- Administrator approval when Windows displays a UAC prompt for enabling TRIM or clearing protected resources

## Default Cleanup

Run the configured cleanup paths without interactive confirmation:

```powershell
python clean.py -Y
```

The default no-path run includes configured temporary directories, screenshot and ScreenSketch data, clipboard storage, recent-item shortcuts, thumbnail caches, shell histories, Paint state, and other application caches listed in `clean.py`.

`-Y` skips the script's confirmation questions. It does not bypass Windows UAC. If NTFS TRIM is disabled, Windows still displays an administrator approval prompt, and cleanup proceeds only after TRIM is verified as enabled.

Run without `-Y` to confirm destructive operations interactively:

```powershell
python clean.py
```

## Delete a Specific Path

Securely delete one file or the contents of one directory:

```powershell
python clean.py "C:\path\to\file-or-directory"
python clean.py -Y "C:\path\to\file-or-directory"
```

Root-drive targets require stronger confirmation unless `-Y` is supplied. Use explicit root-drive deletion with extreme care.

## Clean Previously Deleted Data

Per-file cleanup cannot sanitize files that were already deleted normally. Use `--clean-free-space` to make a one-pass SDelete sweep of unallocated space after the normal cleanup:

```powershell
python clean.py -Y --clean-free-space C:
```

This operation can take considerable time and temporarily consume most available free space. It is intended for occasional cleanup of previously deleted data, not routine use. One pass is used to limit unnecessary SSD writes.

Multiple volumes can be requested by repeating the option:

```powershell
python clean.py -Y --clean-free-space C: --clean-free-space E:
```

## Application Cleanup Modes

```powershell
# Clear caches for all detected Chrome profiles and shared Chrome caches
python clean.py -Y --chrome

# Clear configured Steam cache locations
python clean.py -Y --steam

# Reset Paint during a targeted/default cleanup flow
python clean.py -Y --reset-paint
```

Close applications before cleanup when possible. Active applications and Windows services can recreate cache files immediately after they are removed; such files are newly created data, not evidence that SDelete failed to remove the previous file.

## Flatten Mode

Move files from a directory tree into one output directory and replace their names with random strings:

```powershell
python clean.py -Y "C:\path\to\source" --flatten --output "C:\path\to\flattened"
```

Flatten mode moves and renames files; it does not securely delete the moved output files.

## Cleaner Option Reference

| Option                       | Description                                                                            |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| `directory`                | Optional file or directory to process; omitting it runs the configured default cleanup |
| `-v`, `--verbose`        | Print additional per-file and diagnostic information                                   |
| `-Y`, `-y`, `--yes`    | Skip script confirmation questions; Windows UAC may still appear                       |
| `--chrome`                 | Securely clear detected Chrome profile and shared caches                               |
| `--steam`                  | Securely clear configured Steam cache locations                                        |
| `--reset-paint`            | Reset Microsoft Paint to its default per-user state                                    |
| `--clean-free-space DRIVE` | Run one SDelete pass over unallocated space, for example`C:`; may be repeated        |
| `--flatten`                | Flatten and randomly rename files instead of securely deleting them                    |
| `--output PATH`            | Set the flatten-mode output directory; default is`flattened_files`                   |

View the current command-line help:

```powershell
python clean.py --help
```
