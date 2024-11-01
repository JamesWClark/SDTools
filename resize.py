from PIL import Image
import os
import argparse

def resize_images(dir_path, output_dir, min_dimension, max_dimension, target_ext):
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

    # Initialize counter for renaming images
    counter = 1
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
                if max_dimension:
                    if width > height:
                        ratio = max_dimension / width
                    else:
                        ratio = max_dimension / height

                    new_width = min(int(width * ratio), max_dimension)
                    new_height = min(int(height * ratio), max_dimension)
                else:
                    new_width, new_height = width, height

                if min_dimension:
                    if new_width < min_dimension and new_height < min_dimension:
                        if width > height:
                            ratio = min_dimension / width
                        else:
                            ratio = min_dimension / height

                        new_width = max(int(width * ratio), min_dimension)
                        new_height = max(int(height * ratio), min_dimension)

                # Resize the image
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)

                # Create the new filename with the target extension
                resized_img_path = os.path.join(output_dir, f"out{counter}{target_ext}")

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
                counter += 1
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                unsuccessful_conversions.append(filename)

    # Log unsuccessful conversions
    if unsuccessful_conversions:
        print("\nThe following files were not successfully converted:")
        for file in unsuccessful_conversions:
            print(file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resize images in a directory to specified dimensions and convert to a specified format.")
    parser.add_argument("dir_path", type=str, help="The path to the directory containing images to resize.")
    parser.add_argument("output_dir", type=str, help="The path to the directory to save resized images.")
    parser.add_argument("--min_dimension", type=int, help="The minimum dimension for the resized images.", default=None)
    parser.add_argument("--max_dimension", type=int, help="The maximum dimension for the resized images.", default=None)
    parser.add_argument("target_ext", type=str, help="The target file extension for the resized images (e.g., .jpg, .png, .webp, or .avif).")
    
    args = parser.parse_args()
    
    if not args.dir_path or not args.output_dir or not args.target_ext:
        print("Error: Directory path, output directory, or target extension not provided.")
        print("Usage: python resize.py <dir_path> <output_dir> [--min_dimension MIN] [--max_dimension MAX] <target_ext>")
    else:
        resize_images(args.dir_path, args.output_dir, args.min_dimension, args.max_dimension, args.target_ext)