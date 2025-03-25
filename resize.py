from PIL import Image
import os
import argparse

def resize_images(dir_path, output_dir, min_dimension, target_ext):
    # Check if the directory exists
    if not os.path.isdir(dir_path):
        print(f"Error: The directory '{dir_path}' does not exist.")
        return

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Validate the target extension
    if target_ext not in ['.jpg', '.png', '.webp', '.avif']:
        print(f"Error: Unsupported file extension '{target_ext}'. Only .jpg, .png, .webp, and .avif are supported.")
        return

    unsuccessful_conversions = []

    # Iterate over each file in the directory
    for filename in os.listdir(dir_path):
        filename = filename.lower()
        if filename.endswith((".jpg", ".png", ".jpeg", ".webp", ".avif")):
            try:
                # Open the image file
                img_path = os.path.join(dir_path, filename)
                img = Image.open(img_path)

                # Calculate the new width and height based on the dimensions
                width, height = img.size
                if width < min_dimension and height < min_dimension:
                    if width > height:
                        ratio = min_dimension / width
                    else:
                        ratio = min_dimension / height

                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                else:
                    new_width, new_height = width, height

                # Resize the image while maintaining aspect ratio
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)

                # Create the new filename with the target extension
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

                print(f"Resized and converted {filename} to {resized_img_path}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                unsuccessful_conversions.append(filename)

    # Log unsuccessful conversions
    if unsuccessful_conversions:
        print("\nThe following files were not successfully converted:")
        for file in unsuccessful_conversions:
            print(file)

def flip_images(dir_path, output_dir, flip_horizontal=False, flip_vertical=False):
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
    parser.add_argument("dir_path", type=str, help="The path to the directory containing images to resize.")
    parser.add_argument("output_dir", type=str, help="The path to the directory to save resized images.")
    parser.add_argument("--min_dimension", type=int, help="The minimum dimension for the resized images.", default=None)
    parser.add_argument("--flip_horizontal", action="store_true", help="Flip images horizontally.")
    parser.add_argument("--flip_vertical", action="store_true", help="Flip images vertically.")
    parser.add_argument("target_ext", type=str, help="The target file extension for the resized images (e.g., .jpg, .png, .webp, or .avif).")
    
    args = parser.parse_args()
    
    if args.flip_horizontal or args.flip_vertical:
        flip_images(args.dir_path, args.output_dir, args.flip_horizontal, args.flip_vertical)
    elif args.target_ext:
        resize_images(args.dir_path, args.output_dir, args.min_dimension, args.target_ext)
    else:
        print("Error: No valid operation specified. Use --flip_horizontal, --flip_vertical, or provide a target extension for resizing.")
        resize_images(args.dir_path, args.output_dir, args.min_dimension, args.target_ext)