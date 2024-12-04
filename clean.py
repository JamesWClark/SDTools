from cryptography.fernet import Fernet
import os
import sys
import subprocess
import argparse
import random
import string
from collections import defaultdict
from tqdm import tqdm

# Generate a key and create a cipher suite
key = Fernet.generate_key()
cipher_suite = Fernet(key)

error_files = []
deleted_files_count = defaultdict(int)
deleted_dirs_count = defaultdict(int)

def encrypt_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            plaintext = file.read()
        ciphertext = cipher_suite.encrypt(plaintext)
        with open(file_path, 'wb') as file:
            file.write(ciphertext)
    except Exception as e:
        error_files.append((file_path, str(e)))

def overwrite_file(file_path, passes=3):
    try:
        with open(file_path, 'r+b') as file:
            length = os.path.getsize(file_path)
            for _ in range(passes):
                file.seek(0)
                file.write(os.urandom(length))
    except Exception as e:
        error_files.append((file_path, str(e)))

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def obfuscate_file_name(file_path):
    try:
        directory, original_name = os.path.split(file_path)
        new_name = generate_random_string()  # No extension
        new_path = os.path.join(directory, new_name)
        os.rename(file_path, new_path)
        return new_path
    except Exception as e:
        error_files.append((file_path, str(e)))
        return file_path

def obfuscate_directory_name(directory_path):
    try:
        parent_dir, original_name = os.path.split(directory_path)
        new_name = generate_random_string()
        new_path = os.path.join(parent_dir, new_name)
        os.rename(directory_path, new_path)
        return new_path
    except Exception as e:
        error_files.append((directory_path, str(e)))
        return directory_path

def secure_delete_directory(directory_path, verbose=False):
    total_items = sum([len(files) + len(dirs) for _, dirs, files in os.walk(directory_path)])
    progress_bar = tqdm(total=total_items, desc=f"Processing {directory_path}", unit="item")

    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            obfuscated_file_path = obfuscate_file_name(file_path)
            encrypt_file(obfuscated_file_path)
            overwrite_file(obfuscated_file_path)
            try:
                os.remove(obfuscated_file_path)
                deleted_files_count[directory_path] += 1
                if verbose:
                    print('File deleted:', obfuscated_file_path)
            except Exception as e:
                error_files.append((obfuscated_file_path, str(e)))
                if verbose:
                    print(f"Error deleting file {obfuscated_file_path}: {e}")
            progress_bar.update(1)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            obfuscated_dir_path = obfuscate_directory_name(dir_path)
            if obfuscated_dir_path != directory_path:
                try:
                    os.rmdir(obfuscated_dir_path)
                    deleted_dirs_count[directory_path] += 1
                    if verbose:
                        print('Directory deleted:', obfuscated_dir_path)
                except Exception as e:
                    error_files.append((obfuscated_dir_path, str(e)))
                    if verbose:
                        print(f"Error deleting directory {obfuscated_dir_path}: {e}")
                progress_bar.update(1)
    progress_bar.close()

def flatten_and_obfuscate_directory(directory_path, output_directory, verbose=False):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    total_items = sum([len(files) for _, _, files in os.walk(directory_path)])
    progress_bar = tqdm(total=total_items, desc=f"Processing {directory_path}", unit="item")

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            new_name = generate_random_string()  # No extension
            new_path = os.path.join(output_directory, new_name)
            try:
                os.rename(file_path, new_path)
                if verbose:
                    print('File moved and obfuscated:', new_path)
            except Exception as e:
                error_files.append((file_path, str(e)))
                if verbose:
                    print(f"Error moving and obfuscating file {file_path}: {e}")
            progress_bar.update(1)
    progress_bar.close()

    # Use sdelete to securely delete the original directory
    try:
        subprocess.run(['sdelete', '-s', '-q', directory_path], check=True)
        if verbose:
            print(f"Securely deleted original directory: {directory_path}")
    except Exception as e:
        print(f"Error securely deleting original directory {directory_path}: {e}")

def check_trim_status():
    try:
        result = subprocess.run(['fsutil', 'behavior', 'query', 'disabledeletenotify'], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            if "DisableDeleteNotify = 0" in output:
                print("TRIM is enabled.")
            else:
                print("\033[91mTRIM is not enabled. Please run 'fsutil behavior set disabledeletenotify 0' as an administrator to enable TRIM.\033[0m")
        else:
            print("Failed to check TRIM status.")
            print(result.stderr)
    except Exception as e:
        print(f"Error checking TRIM status: {e}")

def clear_dns_cache():
    try:
        subprocess.run(['ipconfig', '/flushdns'], check=True)
        print("DNS cache cleared.")
    except Exception as e:
        print(f"Error clearing DNS cache: {e}")

def clear_event_logs():
    logs = ['Application', 'Security', 'System']
    for log in logs:
        try:
            # Overwrite the log file with random data
            log_path = f'C:\\Windows\\System32\\winevt\\Logs\\{log}.evtx'
            if os.path.exists(log_path):
                with open(log_path, 'r+b') as file:
                    length = os.path.getsize(log_path)
                    file.write(os.urandom(length))
            
            # Clear the log
            subprocess.run(['wevtutil', 'cl', log], check=True)
            print(f"{log} log cleared.")
        except Exception as e:
            print(f"Error clearing {log} log: {e}")

def clear_temp_files():
    temp_dirs = [os.getenv('TEMP'), os.getenv('TMP'), 'C:\\Windows\\Temp']
    for temp_dir in temp_dirs:
        try:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
            print(f"Temporary files in {temp_dir} cleared.")
        except Exception as e:
            print(f"Error clearing temporary files in {temp_dir}: {e}")

def clear_icon_and_thumbnail_cache():
    try:
        # Clear IconCache.db
        icon_cache_path = os.path.join(os.getenv('LOCALAPPDATA'), 'IconCache.db')
        if os.path.exists(icon_cache_path):
            os.remove(icon_cache_path)
            print("Icon cache cleared. Please restart your computer to rebuild the icon cache.")
        else:
            print("Icon cache file not found.")

        # Clear thumbnail cache
        thumbnail_cache_path = os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Windows', 'Explorer')
        for file in os.listdir(thumbnail_cache_path):
            if file.startswith('thumbcache'):
                file_path = os.path.join(thumbnail_cache_path, file)
                os.remove(file_path)
        print("Thumbnail cache cleared. Please restart your computer to rebuild the thumbnail cache.")
    except Exception as e:
        print(f"Error clearing icon or thumbnail cache: {e}")

def clear_cmd_history():
    try:
        subprocess.run(['doskey', '/reinstall'], check=True)
        print("CMD history cleared.")
    except Exception as e:
        print(f"Error clearing CMD history: {e}")

def clear_powershell_history():
    try:
        ps_history_path = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'PowerShell', 'PSReadline', 'ConsoleHost_history.txt')
        if os.path.exists(ps_history_path):
            encrypt_file(ps_history_path)
            overwrite_file(ps_history_path)
            print("PowerShell history cleared.")
        else:
            print("PowerShell history file not found.")
    except Exception as e:
        print(f"Error clearing PowerShell history: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Securely delete files and directories.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('directory', nargs='?', default=None, help='Directory to delete')
    parser.add_argument('--flatten', action='store_true', help='Flatten and obfuscate files instead of secure deletion')
    parser.add_argument('--output', default='flattened_files', help='Output directory for flattened files')
    args = parser.parse_args()

    if args.flatten:
        if args.directory:
            flatten_and_obfuscate_directory(args.directory, args.output, args.verbose)
        else:
            print("Please specify a directory to flatten and obfuscate.")
    else:
        if args.directory is None:
            directory_paths = [
                '../outputs',
                'C:\\Windows\\Temp',
                os.path.join(os.getenv('LOCALAPPDATA'), 'Temp'),
                os.path.join(os.getenv('USERPROFILE'), '.cache', 'lm-studio', 'user-files'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Packages', 'Microsoft.ScreenSketch_8wekyb3d8bbwe', 'TempState', 'Snips'),
            ]
            for directory_path in directory_paths:
                secure_delete_directory(directory_path, args.verbose)
        else:
            secure_delete_directory(args.directory, args.verbose)

        # Additional cleanup tasks
        clear_dns_cache()
        clear_event_logs()
        clear_temp_files()
        clear_icon_and_thumbnail_cache()
        clear_cmd_history()
        clear_powershell_history()

        # Check TRIM status at the end
        check_trim_status()

        print("\nFinal Report:")
        if deleted_files_count:
            print("\nDeleted files summary:")
            for dir_path, count in deleted_files_count.items():
                print(f"{dir_path}: {count} files")
        if deleted_dirs_count:
            print("\nDeleted directories summary:")
            for dir_path, count in deleted_dirs_count.items():
                print(f"{dir_path}: {count} directories")
        if error_files:
            print("\nError files and directories:")
            for file_path, error in error_files:
                print(f"{file_path}: {error}")

    sys.exit(1)