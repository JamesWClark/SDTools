# Clear File Explorer address bar history
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths' -Name 'url*' -ErrorAction SilentlyContinue