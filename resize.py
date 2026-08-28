from __future__ import annotations

import os
import argparse
import uuid

Image = None
ImageColor = None
ImageOps = None
ImageEnhance = None
ImageStat = None
register_heif_opener = None


def _require_pillow():
    """Import Pillow lazily so `python resize.py -h` works without dependencies."""
    global Image, ImageColor, ImageOps, ImageEnhance, ImageStat, register_heif_opener

    if Image is None:
        try:
            from PIL import Image as _Image, ImageColor as _ImageColor, ImageOps as _ImageOps, ImageEnhance as _ImageEnhance, ImageStat as _ImageStat
        except ModuleNotFoundError as e:
            raise SystemExit(
                "Missing dependency: Pillow. Install with: pip install pillow\n"
                "If you want AVIF/HEIC support, also install: pillow-avif-plugin pillow-heif"
            ) from e
        Image, ImageColor, ImageOps, ImageEnhance, ImageStat = _Image, _ImageColor, _ImageOps, _ImageEnhance, _ImageStat
        Image.MAX_IMAGE_PIXELS = None

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


def _get_meta_forge_parameters(img):
    """Return the source PNG parameters text when present."""
    parameters = img.info.get("parameters")
    return parameters if isinstance(parameters, str) and parameters else None


def _get_meta_forge_exif(parameters):
    """Store parameters in EXIF UserComment for formats without text chunks."""
    exif = Image.Exif()
    exif[37510] = b"ASCII\x00\x00\x00" + parameters.encode("utf-8")
    return exif.tobytes()


def _save_image(img, output_path, target_ext, parameters=None):
    save_kwargs = {}
    if parameters:
        if target_ext == ".png":
            from PIL.PngImagePlugin import PngInfo

            pnginfo = PngInfo()
            pnginfo.add_text("parameters", parameters)
            save_kwargs["pnginfo"] = pnginfo
        elif target_ext == ".jpg":
            save_kwargs["comment"] = parameters.encode("utf-8")
        elif target_ext in {".webp", ".avif", ".heic"}:
            save_kwargs["exif"] = _get_meta_forge_exif(parameters)

    if target_ext == ".jpg":
        img = img.convert("RGB")
        img.save(output_path, "JPEG", **save_kwargs)
    elif target_ext == ".png":
        img.save(output_path, "PNG", **save_kwargs)
    elif target_ext == ".webp":
        img.save(output_path, "WEBP", **save_kwargs)
    elif target_ext == ".avif":
        img.save(output_path, "AVIF", **save_kwargs)
    elif target_ext == ".heic":
        img.save(output_path, "HEIF", **save_kwargs)

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

  5) Conservatively correct a global color cast and brightness
      python resize.py "C:\\images" --auto_normalize --target_ext .jpg

  6) Preserve Stable Diffusion parameters metadata while converting
      python resize.py "C:\\images" --meta-forge --preserve-size --target_ext .avif
"""


VERBOSE_NOTES = """\
Notes

  --box overrides --min_dimension/--max_dimension.
        By default, source dimensions are preserved. Use --fit-range to apply the
        legacy 1600-2048 dimension range, or provide custom min/max values.
    --auto_normalize uses a bounded gray-world white balance and luminance-only
    exposure adjustment. It skips nearly monochrome images and cannot determine
    artistic intent, so review output before replacing originals.
  --box_mode meanings:
     - clip: no scaling; crops/pads to reach the box size
     - cover: scales up/down to fully fill the box, then crops
     - contain: scales up/down to fit inside the box, then pads
    --preserve-size (or --no-resize) skips min/max dimension processing and
        keeps each source image's dimensions. It cannot be combined with --box.
    --recursive includes nested directories. Without --alongside, their relative
        folders are mirrored below --output_dir.
    --alongside writes beside each source file. Existing destination files are
        skipped and listed after processing; no files are overwritten.
    --meta-forge preserves a source image's raw 'parameters' metadata. PNG uses
        a parameters text field, JPEG uses a comment, and WebP/AVIF/HEIC use EXIF
        UserComment. AVI is a video format; use .avif for AV1 still images.

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


def _adjust_rgb_channels(img, red=1.0, green=1.0, blue=1.0):
    """Adjust individual RGB channels by multiplying each channel.
    
    red, green, blue: multipliers for each channel (1.0 = no change, >1.0 = brighter, <1.0 = darker)
    """
    _require_pillow()
    
    # Skip if no adjustment needed
    if red == 1.0 and green == 1.0 and blue == 1.0:
        return img
    
    # Convert to RGB if necessary (JPEG, RGBA, etc.)
    if img.mode == 'RGBA':
        r, g, b, a = img.split()
    elif img.mode == 'RGB':
        r, g, b = img.split()
        a = None
    else:
        # For other modes, convert to RGB first
        img = img.convert('RGB')
        r, g, b = img.split()
        a = None
    
    # Apply multipliers to each channel
    if red != 1.0:
        r = r.point(lambda p: min(255, int(p * red)))
    if green != 1.0:
        g = g.point(lambda p: min(255, int(p * green)))
    if blue != 1.0:
        b = b.point(lambda p: min(255, int(p * blue)))
    
    # Merge channels back
    if a is not None:
        return Image.merge('RGBA', (r, g, b, a))
    else:
        return Image.merge('RGB', (r, g, b))


def _auto_normalize(img, strength=0.5):
    """Conservatively reduce global RGB casts and correct overall exposure.

    Uses the gray-world assumption: across a natural image, average red, green,
    and blue should be similar. Corrections are intentionally capped because a
    blue ocean or red sunset may be a valid subject, not a color cast.
    """
    _require_pillow()
    strength = max(0.0, min(1.0, strength))
    if strength == 0.0:
        return img, None

    has_alpha = "A" in img.getbands()
    alpha = img.getchannel("A") if has_alpha else None
    rgb = img.convert("RGB")
    sample = rgb.copy()
    sample.thumbnail((256, 256), Image.Resampling.BOX)
    means = ImageStat.Stat(sample).mean
    mean_level = sum(means) / 3
    channel_spread = (max(means) - min(means)) / max(mean_level, 1.0)
    factors = [1.0, 1.0, 1.0]
    color_details = "skipped color balance"
    normalized = rgb

    if mean_level > 1.0 and channel_spread >= 0.035:
        # Blend toward neutral means. The bounds retain some protection for
        # scenes whose dominant colors are intentional, while allowing a
        # visible fix for genuinely severe casts at strength 1.0.
        raw_factors = [mean_level / channel_mean for channel_mean in means]
        factors = [max(0.65, min(1.55, 1.0 + (factor - 1.0) * strength)) for factor in raw_factors]
        channels = rgb.split()
        corrected = [
            channel.point(lambda value, factor=factor: min(255, round(value * factor)))
            for channel, factor in zip(channels, factors)
        ]
        normalized = Image.merge("RGB", corrected)
        color_details = "RGB x {:.3f}/{:.3f}/{:.3f}".format(*factors)

    # Stretch luminance with one lookup shared by RGB, preserving the white
    # balance above. This fixes underexposed images much more effectively than
    # a small brightness multiplier while only sacrificing extreme highlights.
    histogram = sample.convert("L").histogram()
    total_pixels = sum(histogram)

    def percentile(percent):
        threshold = total_pixels * percent / 100
        cumulative = 0
        for value, count in enumerate(histogram):
            cumulative += count
            if cumulative >= threshold:
                return value
        return 255

    shadow_point = percentile(1)
    highlight_point = percentile(99)
    if highlight_point - shadow_point >= 12:
        scale = 245 / (highlight_point - shadow_point)
        lookup = [
            round(value * (1 - strength) + max(0, min(245, (value - shadow_point) * scale)) * strength)
            for value in range(256)
        ]
        normalized = normalized.point(lookup * 3)
        exposure_details = f"levels {shadow_point}-{highlight_point}"
    else:
        exposure_details = "skipped narrow tonal range"

    if alpha is not None:
        normalized.putalpha(alpha)
    details = f"{color_details}, {exposure_details}"
    return normalized, details


def resize_images(dir_path, output_dir, min_dimension, max_dimension, target_ext, rename=False, box=None, box_mode="clip", pad_color="black", brightness=1.0, red=1.0, green=1.0, blue=1.0, auto_normalize=False, auto_strength=0.5, meta_forge=False, preserve_size=False, recursive=False, alongside=False):
    _require_pillow()
    # Check if the directory exists
    if not os.path.isdir(dir_path):
        print(f"Error: The directory '{dir_path}' does not exist.")
        return

    # Create the output directory if it doesn't exist
    if not alongside and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Validate the target extension
    if target_ext not in ['.jpg', '.png', '.webp', '.avif', '.heic']:
        print(f"Error: Unsupported file extension '{target_ext}'. Only .jpg, .png, .webp, .avif, and .heic are supported.")
        return

    unsuccessful_conversions = []
    collisions = []

    # Gather all image files to process
    valid_exts = (".jpg", ".png", ".jpeg", ".webp", ".avif", ".heic")
    source_root = os.path.normcase(os.path.abspath(dir_path))
    output_root = os.path.normcase(os.path.abspath(output_dir))

    def is_generated_output(path):
        if alongside or output_root == source_root:
            return False
        normalized_path = os.path.normcase(os.path.abspath(path))
        try:
            return os.path.commonpath([normalized_path, output_root]) == output_root
        except ValueError:
            return False

    if recursive:
        all_files = [
            os.path.join(root, filename)
            for root, _, filenames in os.walk(dir_path)
            for filename in filenames
            if filename.lower().endswith(valid_exts)
            and not (alongside and os.path.splitext(filename)[1].lower() == target_ext.lower())
            and not is_generated_output(os.path.join(root, filename))
        ]
    else:
        all_files = [
            os.path.join(dir_path, filename)
            for filename in os.listdir(dir_path)
            if filename.lower().endswith(valid_exts)
            and not (alongside and os.path.splitext(filename)[1].lower() == target_ext.lower())
        ]
    total_files = len(all_files)
    print(f"Found {total_files} image files to process.")

    for idx, img_path in enumerate(all_files):
        filename = os.path.basename(img_path)
        try:
            img = Image.open(img_path)
            meta_forge_parameters = _get_meta_forge_parameters(img) if meta_forge else None
            if meta_forge and meta_forge_parameters is None:
                print(f"  Meta Forge: no 'parameters' metadata found in {filename}")

            if preserve_size:
                resized_img = ImageOps.exif_transpose(img)
            elif box is not None:
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

            # Apply brightness adjustment if specified
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(resized_img)
                resized_img = enhancer.enhance(brightness)

            # Apply RGB channel adjustments if specified
            if red != 1.0 or green != 1.0 or blue != 1.0:
                resized_img = _adjust_rgb_channels(resized_img, red=red, green=green, blue=blue)

            if auto_normalize:
                resized_img, auto_normalize_details = _auto_normalize(resized_img, auto_strength)
                if auto_normalize_details:
                    print(f"  Auto normalize: {auto_normalize_details}")

            # Use GUID filename if renaming is enabled, otherwise preserve original name
            if rename:
                guid_filename = generate_unique_guid(output_dir, target_ext)
                resized_img_path = os.path.join(output_dir, guid_filename)
            else:
                destination_dir = os.path.dirname(img_path) if alongside else output_dir
                if not alongside and recursive:
                    relative_dir = os.path.relpath(os.path.dirname(img_path), dir_path)
                    if relative_dir != ".":
                        destination_dir = os.path.join(output_dir, relative_dir)
                resized_img_path = os.path.join(destination_dir, os.path.splitext(filename)[0] + target_ext)

            if os.path.exists(resized_img_path):
                collisions.append(resized_img_path)
                print(f"Skipped collision: {resized_img_path}")
                continue

            os.makedirs(os.path.dirname(resized_img_path), exist_ok=True)

            _save_image(resized_img, resized_img_path, target_ext, meta_forge_parameters)

            print(f"{idx+1}/{total_files}: Processed {filename}")
        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            unsuccessful_conversions.append(filename)

    # Log unsuccessful conversions
    if unsuccessful_conversions:
        print("\nThe following files were not successfully converted:")
        for file in unsuccessful_conversions:
            print(file)

    if collisions:
        print("\nSkipped existing output files (no data was overwritten):")
        for collision in collisions:
            print(collision)
    
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
    parser.add_argument("target_ext_positional", nargs="?", type=str, help="(Optional) Target format as positional arg, e.g., .png .jpg .webp")
    parser.add_argument("--examples", action="store_true", help="Print usage examples and exit (no dir_path required).")
    parser.add_argument("--help-verbose", action="store_true", help="Show detailed help + examples and exit (no dir_path required).")
    parser.add_argument("--output_dir", type=str, help="The path to the directory to save resized images. Defaults to '<dir_path>/resized-images-resize-py'.", default=None)
    parser.add_argument("--recursive", action="store_true",
                        help="Process images in the target directory and all nested directories.")
    parser.add_argument("--alongside", "--sibling-output", dest="alongside", action="store_true",
                        help="Write each converted image beside its source; existing files are skipped and reported.")
    parser.add_argument("--min_dimension", type=int, help="The minimum dimension for the resized images.", default=None)
    parser.add_argument("--max_dimension", type=int, help="The maximum dimension for the resized images.", default=None)
    parser.add_argument("--fit-range", action="store_true",
                        help="Use the legacy 1600-2048 dimension range instead of preserving source dimensions by default.")
    parser.add_argument("--box", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"), default=None,
                        help="If set, output is forced to exactly WIDTHxHEIGHT using --box_mode (overrides min/max resizing).")
    parser.add_argument("--box_mode", choices=["clip", "cover", "contain"], default="clip",
                        help="How to fit into --box: clip (no scaling, center-crop/pad), cover (scale+crop), contain (scale+pad).")
    parser.add_argument("--preserve-size", "--no-resize", dest="preserve_size", action="store_true",
                        help="Preserve each source image's dimensions; ignore --min_dimension and --max_dimension.")
    parser.add_argument("--pad_color", type=str, default="black",
                        help="Padding color for --box_mode contain/clip when image is smaller. Use 'transparent' for alpha-capable outputs.")
    parser.add_argument("--brightness", type=float, default=1.0,
                        help="Brightness multiplier (1.0 = original, >1.0 = lighter, <1.0 = darker). Try 1.3 for moderately lighter output.")
    parser.add_argument("--red", type=float, default=1.0,
                        help="Red channel multiplier (1.0 = original, >1.0 = more red, <1.0 = less red).")
    parser.add_argument("--green", type=float, default=1.0,
                        help="Green channel multiplier (1.0 = original, >1.0 = more green, <1.0 = less green).")
    parser.add_argument("--blue", type=float, default=1.0,
                        help="Blue channel multiplier (1.0 = original, >1.0 = more blue, <1.0 = less blue).")
    parser.add_argument("--auto_normalize", action="store_true",
                        help="Conservatively reduce global RGB casts and correct overall brightness; skips nearly monochrome images.")
    parser.add_argument("--auto_strength", type=float, default=0.5,
                        help="Auto-normalize strength from 0.0 to 1.0 (default: 0.5; channel/exposure changes remain capped).")
    parser.add_argument("--meta-forge", action="store_true",
                        help="Preserve source 'parameters' metadata in the converted output when the format supports it.")
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

    if args.preserve_size and args.box:
        parser.error("--preserve-size/--no-resize cannot be combined with --box")

    if args.fit_range and args.box:
        parser.error("--fit-range cannot be combined with --box")

    if args.preserve_size and args.fit_range:
        parser.error("--preserve-size/--no-resize cannot be combined with --fit-range")

    if args.alongside and args.rename:
        parser.error("--alongside/--sibling-output cannot be combined with --rename")

    if args.fit_range:
        args.min_dimension = 1600 if args.min_dimension is None else args.min_dimension
        args.max_dimension = 2048 if args.max_dimension is None else args.max_dimension

    # Auto-generate output directory if not provided
    if args.output_dir is None:
        args.output_dir = os.path.join(args.dir_path, "resized-images-resize-py")

    # If target format provided as positional arg, use it (overrides --target_ext)
    if args.target_ext_positional:
        if not args.target_ext_positional.startswith('.'):
            args.target_ext_positional = '.' + args.target_ext_positional
        args.target_ext = args.target_ext_positional

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
            brightness=args.brightness,
            red=args.red,
            green=args.green,
            blue=args.blue,
            auto_normalize=args.auto_normalize,
            auto_strength=args.auto_strength,
            meta_forge=args.meta_forge,
            preserve_size=args.preserve_size,
            recursive=args.recursive,
            alongside=args.alongside,
        )