from PIL import Image
import os

# Define the maximum height for the resized images
max_height = 512

# Define the directory containing the images to resize
dir_path = "/path/to/images"

# Iterate over each file in the directory
for filename in os.listdir(dir_path):
    if filename.endswith(".jpg") or filename.endswith(".png"):
        # Open the image file
        img_path = os.path.join(dir_path, filename)
        img = Image.open(img_path)

        # Calculate the new width and height based on the maximum height
        width, height = img.size
        ratio = max_height / height
        new_width = int(width * ratio)
        new_height = int(height * ratio)

        # Resize the image and save it to a new file
        resized_img = img.resize((new_width, new_height))
        resized_img_path = os.path.join(dir_path, "resized_" + filename)
        resized_img.save(resized_img_path)

        print(f"Resized {filename} to {new_width}x{new_height}")