from cryptography.fernet import Fernet
import os
import sys
import subprocess
import argparse
import random
import string
from collections import defaultdict
from tqdm import tqdm
import shutil

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

def overwrite_file(file_path, passes=1):
    try:
        with open(file_path, 'r+b') as file:
            length = os.path.getsize(file_path)
            for _ in range(passes):
                file.seek(0)
                file.write(os.urandom(length))
                file.flush()
                os.fsync(file.fileno())
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

def check_sdelete():
    if shutil.which('sdelete') is None:
        print("sdelete is not installed or not found in the system's PATH.")
        print("Please download and install sdelete from https://docs.microsoft.com/en-us/sysinternals/downloads/sdelete")
        sys.exit(1)

def secure_delete_file(file_path, verbose=False):
    try:
        # Obfuscate the file name
        obfuscated_file_path = obfuscate_file_name(file_path)
        
        # Encrypt the file
        encrypt_file(obfuscated_file_path)
        
        # Overwrite the file with random data
        overwrite_file(obfuscated_file_path)
        
        # Securely delete the file using sdelete
        subprocess.run(['sdelete', '-s', '-q', obfuscated_file_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if verbose:
            print('File securely deleted:', obfuscated_file_path)
    except Exception as e:
        error_files.append((file_path, str(e)))
        if verbose:
            print(f"Error securely deleting file {file_path}: {e}")

def secure_delete_directory(directory_path, verbose=False):
    try:
        # Check if the directory is empty
        if not os.listdir(directory_path):
            # Obfuscate the directory name
            obfuscated_dir_path = obfuscate_directory_name(directory_path)
            
            # Securely delete the directory using sdelete
            subprocess.run(['sdelete', '-s', '-q', obfuscated_dir_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deleted_dirs_count[directory_path] += 1
            if verbose:
                print('Empty directory securely deleted:', obfuscated_dir_path)
        else:
            # Use recursive_delete_directory if the directory is not empty
            recursive_delete_directory(directory_path, verbose)
    except Exception as e:
        error_files.append((directory_path, str(e)))
        if verbose:
            print(f"Error securely deleting directory {directory_path}: {e}")

def recursive_delete_directory(directory_path, verbose=False):
    total_items = sum([len(files) + len(dirs) for _, dirs, files in os.walk(directory_path, followlinks=False)])
    progress_bar = tqdm(total=total_items, desc=f"Processing {directory_path}", unit="item")

    for root, dirs, files in os.walk(directory_path, topdown=False, followlinks=False):
        for file in files:
            file_path = os.path.join(root, file)
            secure_delete_file(file_path, verbose)
            progress_bar.update(1)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            secure_delete_directory(dir_path, verbose)
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
        subprocess.run(['sdelete', '-s', '-q', directory_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            secure_delete_file(ps_history_path, verbose=True)
            print("PowerShell history cleared.")
        else:
            print("PowerShell history file not found.")
    except Exception as e:
        print(f"Error clearing PowerShell history: {e}")

def clear_chrome_temp_files(verbose=False):
    chrome_temp_dirs = [
        os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
        os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Media Cache'),
        os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Code Cache'),
        os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'GPUCache'),
        os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Service Worker', 'CacheStorage'),
        os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Service Worker', 'ScriptCache'),
    ]
    for temp_dir in chrome_temp_dirs:
        if os.path.exists(temp_dir):
            recursive_delete_directory(temp_dir, verbose)
        else:
            if verbose:
                print(f"Chrome temp directory not found: {temp_dir}")

def clear_steam_temp_files(verbose=False):
    steam_temp_dirs = [
        os.path.join(os.getenv('PROGRAMFILES(X86)'), 'Steam', 'appcache'),
        os.path.join(os.getenv('PROGRAMFILES(X86)'), 'Steam', 'logs'),
        os.path.join(os.getenv('PROGRAMFILES(X86)'), 'Steam', 'config', 'htmlcache'),
        os.path.join(os.getenv('PROGRAMFILES(X86)'), 'Steam', 'userdata', '<user_id>', 'config', 'browserdata'),
    ]
    for temp_dir in steam_temp_dirs:
        if os.path.exists(temp_dir):
            recursive_delete_directory(temp_dir, verbose)
        else:
            if verbose:
                print(f"Steam temp directory not found: {temp_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Securely delete files and directories.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('directory', nargs='?', default=None, help='Directory to delete')
    parser.add_argument('--flatten', action='store_true', help='Flatten and obfuscate files instead of secure deletion')
    parser.add_argument('--output', default='flattened_files', help='Output directory for flattened files')
    parser.add_argument('--chrome', action='store_true', help='Securely delete Chrome temporary files')
    parser.add_argument('--steam', action='store_true', help='Securely delete Steam temporary files')
    args = parser.parse_args()

    # Check if sdelete is installed
    check_sdelete()

    if args.chrome:
        clear_chrome_temp_files(args.verbose)
    elif args.steam:
        clear_steam_temp_files(args.verbose)
    elif args.flatten:
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
                recursive_delete_directory(directory_path, args.verbose)
        else:
            recursive_delete_directory(args.directory, args.verbose)

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