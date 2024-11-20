import os
import json
import re
from PIL import Image

def parse_generation_parameters(parameters):
    # Simplified parsing logic
    metadata = {}
    for line in parameters.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip()
    return metadata

def get_image_metadata(image_path):
    with Image.open(image_path) as img:
        info = img.info
        if "parameters" in info:
            metadata = parse_generation_parameters(info["parameters"])
            return metadata
        else:
            return None

def build_index(directory):
    index = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.png'):
                file_path = os.path.join(root, file)
                metadata = get_image_metadata(file_path)
                if metadata:
                    first_key = next(iter(metadata))
                    first_value = metadata[first_key]
                    try:
                        lora, tags = first_value.split('>', 1)
                        words_list = tags.strip().split(', ')
                        index[file_path] = {
                            "lora": lora.strip(),
                            "tags": words_list,
                        }
                    except ValueError:
                        print(f"Skipping file {file_path}: metadata format not as expected.")
    return index

def save_index(index, output_file):
    with open(output_file, 'w') as f:
        json.dump(index, f, indent=4)

def load_index(index_file):
    with open(index_file, 'r') as f:
        return json.load(f)

def search_index(index, tags):
    # Use regular expression to split by comma followed by any number of spaces or newline characters
    tags_set = set(re.split(r',\s*', tags))
    result = [file_path for file_path, words_list in index.items() if tags_set.issubset(words_list)]
    return result

# Build and save the index
directory = "D:\\SteamLibrary\\steamapps\\common\\TMP\\txt2img-images\\txt2img-images"
index = build_index(directory)

# Ensure the output file is in the express folder
express_folder = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(express_folder, "image_index.json")
save_index(index, output_file)

# Load the index and perform a search
index = load_index(output_file)
search_tags = "denim"
results = search_index(index, search_tags)
print(f"Images with tags '{search_tags}':")
for result in results:
    print(result)