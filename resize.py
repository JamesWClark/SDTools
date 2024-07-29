# To run this script from command line, use:
# `Usage: `python resize.py <dir_path> <max_dimension> <target_ext>`
# `python resize.py /path/to/images 2048 .jpg`

from PIL import Image
import os
import argparse

def resize_images(dir_path, max_dimension, target_ext):
    # Check if the directory exists
    if not os.path.isdir(dir_path):
        print(f"Error: The directory '{dir_path}' does not exist.")
        return

    # Validate the target extension
    if target_ext not in ['.jpg', '.png']:
        print(f"Error: Unsupported file extension '{target_ext}'. Only .jpg and .png are supported.")
        return

    # Iterate over each file in the directory
    for filename in os.listdir(dir_path):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            # Open the image file
            img_path = os.path.join(dir_path, filename)
            img = Image.open(img_path)

            # Calculate the new width and height based on the maximum dimension
            width, height = img.size
            if width > height:
                ratio = max_dimension / width
            else:
                ratio = max_dimension / height

            new_width = min(int(width * ratio), max_dimension)
            new_height = min(int(height * ratio), max_dimension)

            # Resize the image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)

            # Create the new filename with the target extension
            base, _ = os.path.splitext(filename)
            resized_img_path = os.path.join(dir_path, f"{base}{target_ext}")

            # Save the resized image in the target format
            if target_ext == '.jpg':
                resized_img = resized_img.convert("RGB")  # Ensure image is in RGB mode for JPEG
                resized_img.save(resized_img_path, 'JPEG')
            else:
                resized_img.save(resized_img_path, 'PNG')

            print(f"Resized and converted {filename} to {resized_img_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resize images in a directory to a specified maximum dimension and convert to a specified format.")
    parser.add_argument("dir_path", type=str, help="The path to the directory containing images to resize.")
    parser.add_argument("max_dimension", type=int, help="The maximum dimension for the resized images.")
    parser.add_argument("target_ext", type=str, help="The target file extension for the resized images (e.g., .jpg or .png).")
    
    args = parser.parse_args()
    
    if not args.dir_path or not args.max_dimension or not args.target_ext:
        print("Error: Directory path, max dimension, or target extension not provided.")
        print("Usage: python resize.py <dir_path> <max_dimension> <target_ext>")
    else:
        resize_images(args.dir_path, args.max_dimension, args.target_ext)