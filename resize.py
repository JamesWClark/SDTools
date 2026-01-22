from __future__ import annotations

import os
import argparse
import uuid

Image = None
ImageColor = None
ImageOps = None
register_heif_opener = None


def _require_pillow():
    """Import Pillow lazily so `python resize.py -h` works without dependencies."""
    global Image, ImageColor, ImageOps, register_heif_opener

    if Image is None:
        try:
            from PIL import Image as _Image, ImageColor as _ImageColor, ImageOps as _ImageOps
        except ModuleNotFoundError as e:
            raise SystemExit(
                "Missing dependency: Pillow. Install with: pip install pillow\n"
                "If you want AVIF/HEIC support, also install: pillow-avif-plugin pillow-heif"
            ) from e
        Image, ImageColor, ImageOps = _Image, _ImageColor, _ImageOps

    # Optional format plugins
    try:
        import pillow_avif  # noqa: F401
    except Exception:
        pass

    try:
        from pillow_heif import register_heif_opener as _register_heif_opener

        register_heif_opener = _register_heif_opener
        register_heif_opener()
    except Exception:
        pass

    return Image, ImageColor, ImageOps

EXAMPLES_TEXT = """\
Examples

  1) Classic resize by min/max dimension (keeps aspect ratio)
      - Upscales only if BOTH sides are under --min_dimension
      - Downscales if EITHER side exceeds --max_dimension

      python resize.py "C:\\images" --min_dimension 1600 --max_dimension 2048 --target_ext .jpg

  2) Fit output into a fixed box (exact size)

      a) clip: no scaling; center-crop overflow, pad if too small
          python resize.py "C:\\images" --box 512 512 --box_mode clip --target_ext .png

      b) cover: scale to fill then center-crop (lossy)
          python resize.py "C:\\images" --box 512 512 --box_mode cover --target_ext .jpg

      c) contain: scale to fit then pad (lossy)
          python resize.py "C:\\images" --box 512 512 --box_mode contain --pad_color "#202020" --target_ext .png

  3) Make square thumbnails with transparent padding (best with .png/.webp)
      python resize.py "C:\\images" --box 512 512 --box_mode contain --pad_color transparent --target_ext .png

  4) Flip only
      python resize.py "C:\\images" --flip_horizontal
"""


VERBOSE_NOTES = """\
Notes

  --box overrides --min_dimension/--max_dimension.
  --box_mode meanings:
     - clip: no scaling; crops/pads to reach the box size
     - cover: scales up/down to fully fill the box, then crops
     - contain: scales up/down to fit inside the box, then pads

Dependencies

  Core: Pillow
     pip install pillow
  Optional (enables more formats):
     pip install pillow-avif-plugin pillow-heif
"""

def generate_unique_guid(output_dir, target_ext):
    """Generate a unique GUID filename that doesn't exist in the output directory."""
    while True:
        guid_filename = str(uuid.uuid4()) + target_ext
        guid_path = os.path.join(output_dir, guid_filename)
        if not os.path.exists(guid_path):
            return guid_filename

def batch_rename_files(output_dir, target_ext):
    """Rename all files in the output directory to use the folder name as prefix with numbered suffixes."""
    # Get the folder name
    folder_name = os.path.basename(output_dir)
    
    # Get all files with the target extension
    files = [f for f in os.listdir(output_dir) if f.lower().endswith(target_ext.lower())]
    files.sort()  # Sort for consistent ordering
    
    # Rename files with (1), (2), (3) format
    for idx, filename in enumerate(files, start=1):
        old_path = os.path.join(output_dir, filename)
        new_filename = f"{folder_name} ({idx}){target_ext}"
        new_path = os.path.join(output_dir, new_filename)
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {new_filename}")


def _make_canvas_for_padding(reference_img, size: tuple[int, int], pad_color: str):
    _require_pillow()
    pad_color = pad_color.strip()
    if pad_color.lower() in {"transparent", "none"}:
        return Image.new("RGBA", size, (0, 0, 0, 0))

    rgb = ImageColor.getrgb(pad_color)
    rgb = rgb[:3] if isinstance(rgb, tuple) else (0, 0, 0)

    if reference_img.mode in {"RGBA", "LA"} or (reference_img.mode == "P" and "transparency" in reference_img.info):
        return Image.new("RGBA", size, (*rgb, 255))
    return Image.new("RGB", size, rgb)


def _fit_to_box(img, box: tuple[int, int], box_mode: str, pad_color: str):
    """Transform an image into an exact box size.

    box_mode:
      - cover: scale to fill the box, then center-crop (lossy)
      - contain: scale to fit inside the box, then pad (lossy)
      - clip: no scaling; center-crop if too large, pad if too small
    """
    _require_pillow()
    box_width, box_height = box
    if box_width <= 0 or box_height <= 0:
        raise ValueError("Box dimensions must be positive")

    img = ImageOps.exif_transpose(img)
    box_mode = box_mode.lower().strip()

    if box_mode == "cover":
        return ImageOps.fit(img, (box_width, box_height), method=Image.LANCZOS, centering=(0.5, 0.5))

    if box_mode == "contain":
        contained = ImageOps.contain(img, (box_width, box_height), method=Image.LANCZOS)
        canvas = _make_canvas_for_padding(contained, (box_width, box_height), pad_color)
        paste_x = (box_width - contained.size[0]) // 2
        paste_y = (box_height - contained.size[1]) // 2

        if canvas.mode == "RGBA" and contained.mode != "RGBA":
            contained = contained.convert("RGBA")

        if "A" in contained.getbands():
            canvas.paste(contained, (paste_x, paste_y), mask=contained.getchannel("A"))
        else:
            canvas.paste(contained, (paste_x, paste_y))
        return canvas

    if box_mode == "clip":
        width, height = img.size
        crop_w = min(box_width, width)
        crop_h = min(box_height, height)
        left = (width - crop_w) // 2
        top = (height - crop_h) // 2
        cropped = img.crop((left, top, left + crop_w, top + crop_h))

        canvas = _make_canvas_for_padding(cropped, (box_width, box_height), pad_color)
        paste_x = (box_width - cropped.size[0]) // 2
        paste_y = (box_height - cropped.size[1]) // 2

        if canvas.mode == "RGBA" and cropped.mode != "RGBA":
            cropped = cropped.convert("RGBA")

        if "A" in cropped.getbands():
            canvas.paste(cropped, (paste_x, paste_y), mask=cropped.getchannel("A"))
        else:
            canvas.paste(cropped, (paste_x, paste_y))
        return canvas

    raise ValueError(f"Unsupported --box_mode '{box_mode}'. Use: clip, cover, contain")


def resize_images(dir_path, output_dir, min_dimension, max_dimension, target_ext, rename=False, box=None, box_mode="clip", pad_color="black"):
    _require_pillow()
    # Check if the directory exists
    if not os.path.isdir(dir_path):
        print(f"Error: The directory '{dir_path}' does not exist.")
        return

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Validate the target extension
    if target_ext not in ['.jpg', '.png', '.webp', '.avif', '.heic']:
        print(f"Error: Unsupported file extension '{target_ext}'. Only .jpg, .png, .webp, .avif, and .heic are supported.")
        return

    unsuccessful_conversions = []

    # Gather all image files to process
    valid_exts = (".jpg", ".png", ".jpeg", ".webp", ".avif", ".heic")
    all_files = [f for f in os.listdir(dir_path) if f.lower().endswith(valid_exts)]
    total_files = len(all_files)
    print(f"Found {total_files} image files to process.")

    for idx, filename in enumerate(all_files):
        try:
            img_path = os.path.join(dir_path, filename)
            img = Image.open(img_path)

            if box is not None:
                resized_img = _fit_to_box(img, box, box_mode=box_mode, pad_color=pad_color)
            else:
                img = ImageOps.exif_transpose(img)

                width, height = img.size
                # Calculate new size based on min and max dimension
                # First, scale up if both dimensions are less than min_dimension
                if min_dimension is not None and width < min_dimension and height < min_dimension:
                    if width > height:
                        ratio = min_dimension / width
                    else:
                        ratio = min_dimension / height
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                else:
                    new_width, new_height = width, height

                # Then, scale down if any dimension is greater than max_dimension
                if max_dimension is not None and (new_width > max_dimension or new_height > max_dimension):
                    if new_width > new_height:
                        ratio = max_dimension / new_width
                    else:
                        ratio = max_dimension / new_height
                    new_width = int(new_width * ratio)
                    new_height = int(new_height * ratio)

                # Resize the image while maintaining aspect ratio
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)

            # Use GUID filename if renaming is enabled, otherwise preserve original name
            if rename:
                guid_filename = generate_unique_guid(output_dir, target_ext)
                resized_img_path = os.path.join(output_dir, guid_filename)
            else:
                resized_img_path = os.path.join(output_dir, os.path.splitext(filename)[0] + target_ext)

            # Save the resized image in the target format
            if target_ext == '.jpg':
                resized_img = resized_img.convert("RGB")  # Ensure image is in RGB mode for JPEG
                resized_img.save(resized_img_path, 'JPEG')
            elif target_ext == '.png':
                resized_img.save(resized_img_path, 'PNG')
            elif target_ext == '.webp':
                resized_img.save(resized_img_path, 'WEBP')
            elif target_ext == '.avif':
                resized_img.save(resized_img_path, 'AVIF')
            elif target_ext == '.heic':
                resized_img.save(resized_img_path, 'HEIF')

            print(f"{idx+1}/{total_files}: Processed {filename}")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            unsuccessful_conversions.append(filename)

    # Log unsuccessful conversions
    if unsuccessful_conversions:
        print("\nThe following files were not successfully converted:")
        for file in unsuccessful_conversions:
            print(file)
    
    # Batch rename files if --rename flag is enabled
    if rename:
        print(f"\nBatch renaming files...")
        batch_rename_files(output_dir, target_ext)
        print(f"Resizing and renaming complete!")
    else:
        print(f"Resizing complete!")

def flip_images(dir_path, output_dir, flip_horizontal=False, flip_vertical=False):
    _require_pillow()
    # Check if the directory exists
    if not os.path.isdir(dir_path):
        print(f"Error: The directory '{dir_path}' does not exist.")
        return

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Validate that at least one flip option is selected
    if not flip_horizontal and not flip_vertical:
        print("Error: No flip option selected. Use --flip_horizontal or --flip_vertical.")
        return

    unsuccessful_flips = []

    # Iterate over each file in the directory
    for filename in os.listdir(dir_path):
        filename = filename.lower()
        if filename.endswith((".jpg", ".png", ".jpeg", ".webp", ".avif")):
            try:
                # Open the image file
                img_path = os.path.join(dir_path, filename)
                img = Image.open(img_path)

                # Apply the flip operation
                if flip_horizontal:
                    flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)
                elif flip_vertical:
                    flipped_img = img.transpose(Image.FLIP_TOP_BOTTOM)

                # Save the flipped image
                flipped_img_path = os.path.join(output_dir, filename)
                flipped_img.save(flipped_img_path)
                print(f"Flipped {filename} and saved to {flipped_img_path}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                unsuccessful_flips.append(filename)

    # Log unsuccessful flips
    if unsuccessful_flips:
        print("\nThe following files were not successfully flipped:")
        for file in unsuccessful_flips:
            print(file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resize images in a directory to specified dimensions and convert to a specified format.")
    parser.add_argument("dir_path", nargs="?", type=str, help="The path to the directory containing images to resize.")
    parser.add_argument("--examples", action="store_true", help="Print usage examples and exit (no dir_path required).")
    parser.add_argument("--help-verbose", action="store_true", help="Show detailed help + examples and exit (no dir_path required).")
    parser.add_argument("--output_dir", type=str, help="The path to the directory to save resized images. Defaults to '<dir_path>/resized-images-resize-py'.", default=None)
    parser.add_argument("--min_dimension", type=int, help="The minimum dimension for the resized images.", default=1600)
    parser.add_argument("--max_dimension", type=int, help="The maximum dimension for the resized images.", default=2048)
    parser.add_argument("--box", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"), default=None,
                        help="If set, output is forced to exactly WIDTHxHEIGHT using --box_mode (overrides min/max resizing).")
    parser.add_argument("--box_mode", choices=["clip", "cover", "contain"], default="clip",
                        help="How to fit into --box: clip (no scaling, center-crop/pad), cover (scale+crop), contain (scale+pad).")
    parser.add_argument("--pad_color", type=str, default="black",
                        help="Padding color for --box_mode contain/clip when image is smaller. Use 'transparent' for alpha-capable outputs.")
    parser.add_argument("--target_ext", type=str, help="The target file extension for the resized images (e.g., .jpg, .png, .webp, or .avif).", default=".jpg")
    parser.add_argument("--rename", action="store_true", help="Rename output files to folder_name (1), folder_name (2), etc. instead of preserving original names.")
    parser.add_argument("--flip_horizontal", action="store_true", help="Flip images horizontally.")
    parser.add_argument("--flip_vertical", action="store_true", help="Flip images vertically.")

    args = parser.parse_args()

    if args.examples:
        print(EXAMPLES_TEXT)
        raise SystemExit(0)

    if args.help_verbose:
        print(parser.format_help())
        print(VERBOSE_NOTES)
        print(EXAMPLES_TEXT)
        raise SystemExit(0)

    if args.dir_path is None:
        parser.error("dir_path is required unless using --examples or --help-verbose")

    # Auto-generate output directory if not provided
    if args.output_dir is None:
        args.output_dir = os.path.join(args.dir_path, "resized-images-resize-py")

    if args.flip_horizontal or args.flip_vertical:
        flip_images(args.dir_path, args.output_dir, args.flip_horizontal, args.flip_vertical)
    else:
        resize_images(
            args.dir_path,
            args.output_dir,
            args.min_dimension,
            args.max_dimension,
            args.target_ext,
            args.rename,
            box=tuple(args.box) if args.box else None,
            box_mode=args.box_mode,
            pad_color=args.pad_color,
        )