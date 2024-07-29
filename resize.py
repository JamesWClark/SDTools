# To run this script from command line, use:
# `python resize.py /path/to/images 2048`

from PIL import Image
import os
import argparse

def resize_images(dir_path, max_dimension):
    # Check if the directory exists
    if not os.path.isdir(dir_path):
        print(f"Error: The directory '{dir_path}' does not exist.")
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

            # Create the new filename with dimensions appended
            base, ext = os.path.splitext(filename)
            base = base.replace(' ', '_')
            resized_img_path = os.path.join(dir_path, f"{base}_{new_width}x{new_height}{ext}")

            # Save the resized image
            resized_img.save(resized_img_path)

            print(f"Resized {filename} to {new_width}x{new_height} and saved as {resized_img_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resize images in a directory to a specified maximum dimension.")
    parser.add_argument("dir_path", type=str, help="The path to the directory containing images to resize.")
    parser.add_argument("max_dimension", type=int, help="The maximum dimension for the resized images.")
    
    args = parser.parse_args()
    
    if not args.dir_path or not args.max_dimension:
        print("Error: Directory path or max dimension not provided.")
        print("Usage: python resize.py <dir_path> <max_dimension>")
    else:
        resize_images(args.dir_path, args.max_dimension)