import os
import sys
import subprocess

def secure_delete_directory(directory_path):
    # recursively delete all files and directories
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            result = subprocess.run(['sdelete', '-p', '3', '-s', '-q', file_path], capture_output=True)
            if result.returncode == 0:
                print('File deleted:', file_path)
            else:
                print('Error deleting file:', file_path)
                print(result.stderr.decode())
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if dir_path != directory_path:
                result = subprocess.run(['sdelete', '-p', '3', '-s', '-q', dir_path], capture_output=True)
                if result.returncode == 0:
                    print('Directory deleted:', dir_path)
                else:
                    print('Error deleting directory:', dir_path)
                    print(result.stderr.decode())

if __name__ == '__main__':
    if len(sys.argv) != 2:
        directory_path = 'C:/Users/JWC/git/stable-diffusion-webui/outputs'
    else:
        directory_path = sys.argv[1]

secure_delete_directory(directory_path)
sys.exit(1)