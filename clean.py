from cryptography.fernet import Fernet
import os
import sys
import subprocess

# Generate a key and create a cipher suite
key = Fernet.generate_key()
cipher_suite = Fernet(key)

def encrypt_file(file_path):
    with open(file_path, 'rb') as file:
        plaintext = file.read()
    ciphertext = cipher_suite.encrypt(plaintext)
    with open(file_path, 'wb') as file:
        file.write(ciphertext)

def secure_delete_directory(directory_path):
    # recursively delete all files and directories
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            encrypt_file(file_path)
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
        directory_paths = ['../outputs', 'C:/Users/JWC/git/Forge/output', 'C:/Users/JWC/git/Fooocus_win64_2-1-831/Fooocus/outputs']
        for directory_path in directory_paths:
            secure_delete_directory(directory_path)
    else:
        directory_path = sys.argv[1]


sys.exit(1)