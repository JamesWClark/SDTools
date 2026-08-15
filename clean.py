import os
import sys
import subprocess
import argparse
import random
import string
from collections import defaultdict
import shutil
import threading
import queue
import multiprocessing
import winreg

error_files = []
deleted_files_count = defaultdict(int)
deleted_dirs_count = defaultdict(int)

class ProgressBar:
    def __init__(self, total, desc, unit):
        self.total = total
        self.desc = desc
        self.unit = unit
        self.current = 0
        self.last_percent = -1
        self.lock = threading.Lock()

    def update(self, amount=1):
        with self.lock:
            self.current += amount
            percent = 100 if self.total == 0 else int(self.current * 100 / self.total)
            if percent == 100 or percent >= self.last_percent + 5:
                self.last_percent = percent
                print(f"\r{self.desc}: {self.current}/{self.total} {self.unit} ({percent}%)", end='')

    def close(self):
        if self.total == 0:
            print(f"{self.desc}: no {self.unit}s found")
        else:
            print()

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
        subprocess.run(
            ['sdelete', '-p', '1', '-r', '-q', file_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deleted_files_count[os.path.dirname(file_path) or '.'] += 1
        if verbose:
            print('File securely deleted:', file_path)
        return True
    except Exception as e:
        error_files.append((file_path, str(e)))
        if verbose:
            print(f"Error securely deleting file {file_path}: {e}")
        return False

def secure_delete_directory(directory_path, verbose=False):
    try:
        # Check if the directory is empty
        if not os.listdir(directory_path):
            # Obfuscate the directory name
            obfuscated_dir_path = obfuscate_directory_name(directory_path)
            
            # Securely delete the directory using sdelete
            subprocess.run(
                ['sdelete', '-p', '1', '-r', '-s', '-q', obfuscated_dir_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
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
    progress_bar = ProgressBar(total=total_items, desc=f"Processing {directory_path}", unit="item")

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
    progress_bar = ProgressBar(total=total_items, desc=f"Processing {directory_path}", unit="item")

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
        subprocess.run(
            ['sdelete', '-p', '1', '-r', '-s', '-q', directory_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if verbose:
            print(f"Securely deleted original directory: {directory_path}")
    except Exception as e:
        print(f"Error securely deleting original directory {directory_path}: {e}")

def get_ntfs_trim_status():
    try:
        result = subprocess.run(
            ['fsutil', 'behavior', 'query', 'disabledeletenotify'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            if line.strip().lower().startswith('ntfs disabledeletenotify'):
                value = line.split('=', 1)[1].strip().split()[0]
                return value == '0'
    except Exception as e:
        error_files.append(('NTFS TRIM status', str(e)))
    return None

def check_trim_status():
    trim_enabled = get_ntfs_trim_status()
    if trim_enabled is True:
        print("NTFS TRIM is enabled.")
    elif trim_enabled is False:
        print("\033[91mNTFS TRIM is disabled.\033[0m")
    else:
        print("\033[91mUnable to determine NTFS TRIM status.\033[0m")
    return trim_enabled

def ensure_trim_enabled(skip_confirm=False):
    if check_trim_status() is True:
        return True

    print("TRIM should be enabled before secure cleanup on an SSD.")
    if not skip_confirm:
        response = input("Request administrator access to enable NTFS TRIM? (Y/N): ").strip().upper()
        if response not in ('Y', 'YES'):
            print("Cleanup cancelled because NTFS TRIM is not enabled.")
            return False

    ps_script = (
        "$process = Start-Process -FilePath 'fsutil.exe' "
        "-ArgumentList @('behavior','set','DisableDeleteNotify','0') "
        "-Verb RunAs -Wait -PassThru; exit $process.ExitCode"
    )
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            check=False,
        )
        if result.returncode != 0:
            print("Administrator request was cancelled or TRIM could not be enabled.")
            return False
    except Exception as e:
        error_files.append(('Enable NTFS TRIM', str(e)))
        print(f"Unable to request administrator access: {e}")
        return False

    print("Checking NTFS TRIM status again...")
    if check_trim_status() is not True:
        print("Cleanup cancelled because NTFS TRIM remains disabled or unknown.")
        return False
    return True

def clear_dns_cache():
    try:
        subprocess.run(['ipconfig', '/flushdns'], check=True)
        print("DNS cache cleared.")
    except Exception as e:
        error_files.append(('DNS cache', str(e)))
        print(f"Error clearing DNS cache: {e}")

def clear_event_logs():
    logs = ['Application', 'Security', 'System']
    for log in logs:
        try:
            subprocess.run(['wevtutil', 'cl', log], check=True)
            print(f"{log} log logically cleared; old extents require free-space cleanup.")
        except Exception as e:
            error_files.append((f'{log} event log', str(e)))
            print(f"Error clearing {log} log: {e}")

def clear_temp_files():
    temp_dirs = [os.getenv('TEMP'), os.getenv('TMP'), 'C:\\Windows\\Temp']
    for temp_dir in dict.fromkeys(path for path in temp_dirs if path):
        if os.path.isdir(temp_dir):
            if parallel_secure_delete(temp_dir, remove_directories=False):
                print(f"Temporary-file cleanup completed for {temp_dir}.")

def clear_icon_and_thumbnail_cache():
    try:
        # Clear IconCache.db
        icon_cache_path = os.path.join(os.getenv('LOCALAPPDATA'), 'IconCache.db')
        if os.path.exists(icon_cache_path):
            if secure_delete_file(icon_cache_path):
                print("Icon cache securely cleared. Please restart your computer to rebuild it.")
        else:
            print("Icon cache file not found.")

        # Clear thumbnail cache
        thumbnail_cache_path = os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Windows', 'Explorer')
        for file in os.listdir(thumbnail_cache_path):
            if file.startswith('thumbcache'):
                file_path = os.path.join(thumbnail_cache_path, file)
                secure_delete_file(file_path)
        print("Thumbnail cache securely cleared. Please restart your computer to rebuild it.")
    except Exception as e:
        error_files.append(('Icon and thumbnail cache', str(e)))
        print(f"Error clearing icon or thumbnail cache: {e}")

def clear_cmd_history():
    try:
        subprocess.run(['doskey', '/reinstall'], check=True)
        print("CMD history cleared.")
    except Exception as e:
        error_files.append(('CMD history', str(e)))
        print(f"Error clearing CMD history: {e}")

def clear_explorer_address_bar_history():
    key_path = r'Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths'
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        print("Windows Explorer address bar history cleared.")
    except FileNotFoundError:
        print("Windows Explorer address bar history is already clear.")
    except Exception as e:
        error_files.append(('Explorer address bar history', str(e)))
        print(f"Error clearing Windows Explorer address bar history: {e}")

def clear_powershell_history():
    try:
        ps_history_path = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'PowerShell', 'PSReadline', 'ConsoleHost_history.txt')
        if os.path.exists(ps_history_path):
            if secure_delete_file(ps_history_path, verbose=True):
                print("PowerShell history securely cleared.")
        else:
            print("PowerShell history file not found.")
    except Exception as e:
        error_files.append(('PowerShell history', str(e)))
        print(f"Error clearing PowerShell history: {e}")

def clear_chrome_temp_files(verbose=False):
    subprocess.run(
        ['taskkill', '/IM', 'chrome.exe', '/F'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    localappdata = os.getenv('LOCALAPPDATA')
    if not localappdata:
        error_files.append(('Chrome cache', 'LOCALAPPDATA is not set'))
        return

    user_data = os.path.join(localappdata, 'Google', 'Chrome', 'User Data')
    if not os.path.isdir(user_data):
        if verbose:
            print(f"Chrome user data directory not found: {user_data}")
        return

    profile_names = [
        entry.name
        for entry in os.scandir(user_data)
        if entry.is_dir(follow_symlinks=False)
        and (entry.name == 'Default' or entry.name == 'Guest Profile' or entry.name.startswith('Profile '))
    ]
    profile_cache_paths = [
        ('Cache',),
        ('Media Cache',),
        ('Code Cache',),
        ('GPUCache',),
        ('Service Worker', 'CacheStorage'),
        ('Service Worker', 'ScriptCache'),
    ]
    chrome_temp_dirs = [
        os.path.join(user_data, profile_name, *relative_path)
        for profile_name in profile_names
        for relative_path in profile_cache_paths
    ]
    chrome_temp_dirs.extend([
        os.path.join(user_data, 'ShaderCache'),
        os.path.join(user_data, 'GrShaderCache'),
        os.path.join(user_data, 'GraphiteDawnCache'),
    ])

    for temp_dir in chrome_temp_dirs:
        if os.path.isdir(temp_dir):
            parallel_secure_delete(temp_dir, remove_directories=False)
        elif verbose:
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

def clear_vlc_recent_media_secure(verbose=False):
    """
    Securely erase the VLC recent media list by overwriting and securely deleting the config file.
    Steps:
    1. Locate the VLC config file (vlc-qt-interface.ini).
    2. If it exists, use secure_delete_file to overwrite and securely delete it.
    3. Print status.
    """
    config_path = os.path.join(os.getenv('APPDATA'), 'vlc', 'vlc-qt-interface.ini')
    if not os.path.exists(config_path):
        print("VLC config file not found.")
        return

    if secure_delete_file(config_path, verbose=verbose):
        print("VLC recent media list securely erased.")

def clear_notepad_plus_plus_recent_files(verbose=False):
    """
    Securely erase the Notepad++ recent files list by removing individual File entries
    from the History section in the config.xml file.
    """
    config_path = os.path.join(os.getenv('APPDATA'), 'Notepad++', 'config.xml')
    
    if not os.path.exists(config_path):
        if verbose:
            print("Notepad++ config file not found.")
        return
    
    try:
        # Read the config file
        with open(config_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Remove only the File entries within the History section, preserve the History tag itself
        import re
        cleaned_content = re.sub(r'\s*<File\s+filename="[^"]*"\s*/>', '', content)
        
        if not secure_delete_file(config_path, verbose=verbose):
            return

        with open(config_path, 'w', encoding='utf-8') as file:
            file.write(cleaned_content)
        
        if verbose:
            print("Notepad++ recent files list cleared.")
    except Exception as e:
        error_files.append((config_path, str(e)))
        if verbose:
            print(f"Error clearing Notepad++ recent files: {e}")

def reset_paint_to_default(verbose=False):
    """
    Best-effort reset of Microsoft Paint to default.

    On modern Windows, Paint is typically a Microsoft Store (Appx) app. The Settings
    "Reset" button maps closely to `Reset-AppxPackage`.

    Paint is stopped, its per-user data is securely removed, and then the Appx
    package reset recreates the default state.
    """
    # 1) Stop Paint if running (ignore failures)
    try:
        subprocess.run(
            ['taskkill', '/IM', 'mspaint.exe', '/F'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception:
        pass

    localappdata = os.getenv('LOCALAPPDATA')
    if not localappdata:
        error_files.append(('Paint reset', 'LOCALAPPDATA is not set'))
        return False

    package_dirs = [
        os.path.join(localappdata, 'Packages', 'Microsoft.Paint_8wekyb3d8bbwe'),
        os.path.join(localappdata, 'Packages', 'Microsoft.MSPaint_8wekyb3d8bbwe'),
    ]
    errors_before = len(error_files)
    for package_dir in package_dirs:
        if os.path.isdir(package_dir):
            parallel_secure_delete(package_dir, remove_directories=False)

    if len(error_files) != errors_before:
        print("Paint reset cancelled because some app data could not be securely deleted.")
        return False

    ps_script = r"""
$ErrorActionPreference = 'Stop'

$resetCmd = Get-Command Reset-AppxPackage -ErrorAction SilentlyContinue
if (-not $resetCmd) {
  exit 2
}

$names = @('Microsoft.Paint', 'Microsoft.MSPaint')
foreach ($name in $names) {
  $pkg = Get-AppxPackage -Name $name -ErrorAction SilentlyContinue
  if ($pkg) {
    Reset-AppxPackage -Package $pkg.PackageFullName | Out-Null
  }
}
exit 0
"""

    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("Paint reset to default (Reset-AppxPackage).")
            return True
        reason = (result.stderr or result.stdout or f'exit code {result.returncode}').strip()
        error_files.append(('Paint reset', reason))
        if verbose:
            print(f"Paint reset via PowerShell did not run: {reason}")
    except Exception as e:
        error_files.append(('Paint reset', str(e)))
        if verbose:
            print(f"Paint reset via PowerShell failed: {e}")
    return False

def optimize_io_performance(target_path):
    """
    Disable Windows USN journal for better performance on the target drive.
    
    Args:
        target_path: The path being processed, used to determine the drive
    
    Returns:
        The drive letter that was optimized
    """
    # Extract drive letter from the target path
    drive = os.path.splitdrive(target_path)[0]
    if not drive:
        drive = os.path.splitdrive(os.getcwd())[0]  # Use current drive if target doesn't specify
    
    print(f"Temporarily disabling USN journal on {drive} for performance...")
    subprocess.run(['fsutil', 'usn', 'deletejournal', '/D', drive], 
                  stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    
    return drive

def restore_io_performance(drive):
    """
    Re-enable Windows USN journal on the drive that was previously optimized.
    
    Args:
        drive: The drive letter to restore
    """
    print(f"Re-enabling USN journal on {drive}...")
    subprocess.run(['fsutil', 'usn', 'createjournal', 'M=1000', 'N=100', drive],
                  stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    
def secure_delete_file_with_progress(file_path, verbose, progress_bar):
    try:
        secure_delete_file(file_path, verbose)
    finally:
        progress_bar.update(1)

def parallel_secure_delete(directory_path, thread_count=None, remove_directories=True):
    errors_before = len(error_files)

    if thread_count is None:
        thread_count = get_default_thread_count()

    # Gather all files to delete
    files = []
    for root, _, filenames in os.walk(directory_path):
        for f in filenames:
            files.append(os.path.join(root, f))

    total_files = len(files)

    # Create a thread-safe queue and fill it with file paths
    file_queue = queue.Queue()
    for file_path in files:
        file_queue.put(file_path)

    # Print the path being processed
    print(f"Path: {directory_path}")
    
    # Single shared progress bar for all threads
    progress_bar = ProgressBar(total=total_files, desc="Deleting files", unit="file")

    def worker():
        while True:
            try:
                file_path = file_queue.get_nowait()
            except queue.Empty:
                break
            secure_delete_file(file_path)
            progress_bar.update(1)
            file_queue.task_done()

    # Start threads
    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    # Wait for all threads to finish
    for t in threads:
        t.join()
    progress_bar.close()

    if remove_directories:
        for root, dirs, files in os.walk(directory_path, topdown=False):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    secure_delete_directory(dir_path)
                except Exception as e:
                    error_files.append((dir_path, str(e)))

    return len(error_files) == errors_before

def get_default_thread_count():
    """
    Returns the optimal default thread count for parallel operations.
    Uses the number of logical CPUs, but at least 1.
    """
    try:
        return max(1, multiprocessing.cpu_count())
    except Exception:
        return 4  # Fallback

def is_root_drive(path):
    """
    Detects if a path is a root drive (like C:, E:, C:\, E:\, etc.)
    Returns True if it's a root drive, False otherwise.
    """
    if not path:
        return False
    
    # Normalize the path
    normalized = os.path.normpath(path)
    
    # Check for patterns like C:, C:\, E:, E:\, etc.
    # Split by drive and rest
    drive, rest = os.path.splitdrive(normalized)
    
    # If there's a drive letter and the rest is empty or just a backslash, it's a root drive
    if drive and len(drive) == 2 and drive[1] == ':':
        if not rest or rest == '\\' or rest == '/':
            return True
    
    return False

def get_user_confirmation(target_path, is_destructive=True, skip_confirm=False):
    """
    Gets confirmation from the user before proceeding with destructive operations.
    Returns True if user confirms, False otherwise.
    If skip_confirm is True, bypasses the prompt and returns True immediately.
    """
    if skip_confirm:
        return True
    
    if is_destructive:
        print("\n" + "="*70)
        print("⚠️  WARNING: DESTRUCTIVE OPERATION")
        print("="*70)
        print(f"Target: {target_path}")
        print("\nThis operation will SECURELY DELETE files and directories.")
        print("Deleted data CANNOT be recovered.")
        print("="*70)
    
    while True:
        response = input("\nDo you want to proceed? (Y/N): ").strip().upper()
        if response in ('Y', 'YES'):
            return True
        elif response in ('N', 'NO'):
            print("Operation cancelled.")
            return False
        else:
            print("Invalid input. Please enter Y or N.")

def get_root_drive_confirmation(path, skip_confirm=False):
    """
    Gets DOUBLE confirmation for root drive operations.
    Returns True only if user confirms twice.
    If skip_confirm is True, bypasses the prompts and returns True immediately.
    """
    if skip_confirm:
        return True
    
    drive = os.path.splitdrive(path)[0] or os.path.splitdrive(os.getcwd())[0]
    
    print("\n" + "="*70)
    print("🚨 CRITICAL WARNING: ROOT DRIVE DETECTED")
    print("="*70)
    print(f"Target path is on root drive: {drive}")
    print("\nAttempting to delete from a root drive can cause SEVERE SYSTEM DAMAGE!")
    print("This may render your system UNBOOTABLE.")
    print("="*70)
    
    # First confirmation
    print("\nType the drive letter to confirm (e.g., C or E):")
    first_confirm = input("Enter drive letter: ").strip().upper()
    expected_letter = drive[0].upper() if drive else ''
    
    if first_confirm != expected_letter:
        print(f"Incorrect. Expected '{expected_letter}', got '{first_confirm}'.")
        print("Operation cancelled.")
        return False
    
    # Second confirmation
    print("\nEnter 'YES I UNDERSTAND' to proceed (this is your last chance):")
    second_confirm = input("> ").strip().upper()
    
    if second_confirm == 'YES I UNDERSTAND':
        print("\n⚠️  Proceeding with deletion on root drive...")
        return True
    else:
        print("Confirmation failed. Operation cancelled.")
        return False

def clean_free_space(drive, verbose=False):
    normalized_drive = drive.rstrip('\\/')
    if len(normalized_drive) != 2 or normalized_drive[1] != ':' or not normalized_drive[0].isalpha():
        error_files.append((drive, 'Free-space cleanup requires a drive letter such as C:'))
        return False

    try:
        command = ['sdelete', '-p', '1', '-q', '-c', normalized_drive.upper()]
        if verbose:
            print(f"Cleaning unallocated space on {normalized_drive.upper()} with one pass...")
        subprocess.run(command, check=True)
        print(f"Free space securely cleaned on {normalized_drive.upper()}.")
        return True
    except Exception as e:
        error_files.append((normalized_drive.upper(), str(e)))
        print(f"Error cleaning free space on {normalized_drive.upper()}: {e}")
        return False

def print_final_report():
    print("\nFinal Report:")
    if deleted_files_count:
        print("\nDeleted files summary:")
        for dir_path, count in deleted_files_count.items():
            print(f"{dir_path}: {count} files")
    if deleted_dirs_count:
        print("\nDirectories removed during this run (applications may recreate them):")
        for dir_path, count in deleted_dirs_count.items():
            print(f"{dir_path}: {count} directories")
    if error_files:
        print("\nErrors:")
        for file_path, error in error_files:
            print(f"{file_path}: {error}")
    else:
        print("No errors reported.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Securely delete files and directories.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('-Y', '-y', '--yes', action='store_true', help='Skip all confirmations (for automation)')
    parser.add_argument('directory', nargs='?', default=None, help='Directory to delete')
    parser.add_argument('--flatten', action='store_true', help='Flatten and obfuscate files instead of secure deletion')
    parser.add_argument('--output', default='flattened_files', help='Output directory for flattened files')
    parser.add_argument('--chrome', action='store_true', help='Securely delete Chrome temporary files')
    parser.add_argument('--steam', action='store_true', help='Securely delete Steam temporary files')
    parser.add_argument('--clean-free-space', action='append', metavar='DRIVE', help='After cleanup, securely clean unallocated space on a drive such as C: (slow)')
    parser.add_argument('--reset-paint', action='store_true', help='Reset Microsoft Paint to default (per-user); default no-args run also resets Paint')
    args = parser.parse_args()

    # Check if sdelete is installed
    check_sdelete()

    if not ensure_trim_enabled(skip_confirm=args.yes):
        sys.exit(2)

    if args.chrome:
        # Request confirmation before clearing Chrome
        if not get_user_confirmation("Chrome temporary files", is_destructive=True, skip_confirm=args.yes):
            sys.exit(1)
        clear_chrome_temp_files(args.verbose)
    elif args.steam:
        # Request confirmation before clearing Steam
        if not get_user_confirmation("Steam temporary files", is_destructive=True, skip_confirm=args.yes):
            sys.exit(1)
        clear_steam_temp_files(args.verbose)
    elif args.flatten:
        if args.directory:
            # Request confirmation before flattening
            if not get_user_confirmation(args.directory, is_destructive=True, skip_confirm=args.yes):
                sys.exit(1)
            flatten_and_obfuscate_directory(args.directory, args.output, args.verbose)
        else:
            print("Please specify a directory to flatten and obfuscate.")
    else:
        if args.directory is None:
            # Request confirmation before running default cleanup
            if not get_user_confirmation("Default cleanup paths", is_destructive=True, skip_confirm=args.yes):
                sys.exit(1)
            
            directory_paths = [
                '../params.txt',
                '../log/images',
                '../../ComfyUI/input',
                'C:\\Windows\\Temp',
                'C:\\Users\\JWC\\AppData\\Local\\Microsoft\\Windows\\Explorer',
                'C:\\Users\\JWC\\AppData\\Roaming\\Code\\User\\workspaceStorage\\vscode-chat-images',
                '\\\\wsl.localhost\\Trellis2-Ubuntu-22.04.5\\root\\audioboss\\work',
                os.path.join(os.getenv('LOCALAPPDATA'), 'Temp'),
                os.path.join(os.getenv('USERPROFILE'), '.cache', 'lm-studio', 'user-files'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Packages', 'Microsoft.ScreenSketch_8wekyb3d8bbwe', 'TempState', 'Snips'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Packages', 'Microsoft.Paint_8wekyb3d8bbwe', 'TempState'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Meltytech', 'Shotcut', 'cache'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Meltytech', 'Shotcut', 'thumbnails'),
                os.path.join(os.getenv('USERPROFILE'), 'Pictures', 'Screenshots'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Microsoft', 'Windows', 'Clipboard'),
                os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Recent'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Packages', 'Microsoft.ScreenSketch_8wekyb3d8bbwe', 'TempState'),
                os.path.join(os.getenv('LOCALAPPDATA'), 'Packages', 'Microsoft.ScreenSketch_8wekyb3d8bbwe', 'LocalState'),
            ]
            directory_paths = list(dict.fromkeys(directory_paths))
            for path in directory_paths:
                if os.path.isfile(path):
                    if secure_delete_file(path, args.verbose):
                        print(f"Securely deleted file: {path}")
                elif os.path.isdir(path):
                    # Handle directory
                    parallel_secure_delete(path, remove_directories=False)
                else:
                    print(f"Path not found or invalid: {path}")
        else:
            # User-provided directory - check for root drive and confirm
            if is_root_drive(args.directory):
                if not get_root_drive_confirmation(args.directory, skip_confirm=args.yes):
                    sys.exit(1)
            else:
                # Normal confirmation for non-root paths
                if not get_user_confirmation(args.directory, is_destructive=True, skip_confirm=args.yes):
                    sys.exit(1)
            
            if os.path.isfile(args.directory):
                secure_delete_file(args.directory, args.verbose)
            elif os.path.isdir(args.directory):
                parallel_secure_delete(args.directory)
            else:
                print(f"Path not found or invalid: {args.directory}")
                error_files.append((args.directory, 'Path not found or invalid'))

        # Additional cleanup tasks
        clear_dns_cache()
        clear_event_logs()
        clear_temp_files()
        clear_icon_and_thumbnail_cache()
        clear_cmd_history()
        clear_powershell_history()
        clear_vlc_recent_media_secure()
        clear_notepad_plus_plus_recent_files()
        clear_explorer_address_bar_history()

        # Default no-args run: always reset Paint.
        # Also allow explicit reset via --reset-paint for other invocation styles.
        if args.directory is None or args.reset_paint:
            reset_paint_to_default(args.verbose)

    for drive in args.clean_free_space or []:
        if not get_user_confirmation(
            f"Unallocated space on {drive}",
            is_destructive=True,
            skip_confirm=args.yes,
        ):
            sys.exit(1)
        clean_free_space(drive, args.verbose)

    print_final_report()
    sys.exit(1 if error_files else 0)