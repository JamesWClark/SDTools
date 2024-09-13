from cryptography.fernet import Fernet
import os
import sys
import subprocess
import argparse

# Generate a key and create a cipher suite
key = Fernet.generate_key()
cipher_suite = Fernet(key)

error_files = []
deleted_files = []
deleted_dirs = []

def encrypt_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            plaintext = file.read()
        ciphertext = cipher_suite.encrypt(plaintext)
        with open(file_path, 'wb') as file:
            file.write(ciphertext)
    except Exception as e:
        error_files.append((file_path, str(e)))

def secure_delete_directory(directory_path, verbose=False):
    # recursively delete all files and directories
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            encrypt_file(file_path)
            try:
                result = subprocess.run(['sdelete', '-p', '3', '-s', '-q', file_path], capture_output=True)
                if result.returncode == 0:
                    deleted_files.append(file_path)
                    if verbose:
                        print('File deleted:', file_path)
                else:
                    error_message = result.stderr.decode()
                    error_files.append((file_path, error_message))
                    if verbose:
                        print('Error deleting file:', file_path)
                        print(error_message)
            except Exception as e:
                error_files.append((file_path, str(e)))
                if verbose:
                    print(f"Error deleting file {file_path}: {e}")
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if dir_path != directory_path:
                try:
                    result = subprocess.run(['sdelete', '-p', '3', '-s', '-q', dir_path], capture_output=True)
                    if result.returncode == 0:
                        deleted_dirs.append(dir_path)
                        if verbose:
                            print('Directory deleted:', dir_path)
                    else:
                        error_message = result.stderr.decode()
                        error_files.append((dir_path, error_message))
                        if verbose:
                            print('Error deleting directory:', dir_path)
                            print(error_message)
                except Exception as e:
                    error_files.append((dir_path, str(e)))
                    if verbose:
                        print(f"Error deleting directory {dir_path}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Securely delete files and directories.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('directory', nargs='?', default=None, help='Directory to delete')
    args = parser.parse_args()

    if args.directory is None:
        directory_paths = [
            '../outputs',
            'C:\\Windows\\Temp',
            os.path.join(os.getenv('LOCALAPPDATA'), 'Temp'),
            os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
            os.path.join(os.getenv('LOCALAPPDATA'), 'Mozilla', 'Firefox', 'Profiles')
        ]
        for directory_path in directory_paths:
            secure_delete_directory(directory_path, args.verbose)
    else:
        secure_delete_directory(args.directory, args.verbose)

    # Print error files and final report after a blank line
    print("\nFinal Report:")
    if deleted_files:
        print("\nDeleted files:")
        for file_path in deleted_files:
            print(file_path)
    if deleted_dirs:
        print("\nDeleted directories:")
        for dir_path in deleted_dirs:
            print(dir_path)
    if error_files:
        print("\nError files and directories:")
        for file_path, error in error_files:
            print(f"{file_path}: {error}")

sys.exit(1)