import sys
import os

# Check if at least one folder path is supplied as a command-line argument
if len(sys.argv) < 2:
    print('Error: no folder paths supplied')
    sys.exit(1)

# Iterate over each folder path supplied as a command-line argument
for folder_path in sys.argv[1:]:
    # Iterate over each file in the folder
    for filename in os.listdir(folder_path):
        # Check if the file has a .txt extension
        if filename.endswith('.txt'):
            # Construct the full file path
            file_path = os.path.join(folder_path, filename)
            # Read the contents of the file
            with open(file_path, 'r') as f:
                contents = f.read()
            # Replace all newline characters with a space
            contents = contents.replace('\n', ' ')
            # Add a prefix and suffix to the contents
            modified_contents = 'a photo of ' + contents + ' in between two gray walls on each side of the photo'
            # Write the modified contents back to the file
            with open(file_path, 'w') as f:
                f.write(modified_contents)