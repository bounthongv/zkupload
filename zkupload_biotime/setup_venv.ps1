# Clean PowerShell script to create venv
$env:PATH = "C:\Python314;C:\Python314\Scripts;" + $env:PATH
Set-Location D:\zkupload\zkupload_biotime

# Remove old venv
if (Test-Path venv) {
    Remove-Item -Recurse -Force venv
}

# Create new venv using Python 3.14
& C:\Python314\python.exe -m venv venv

# Activate and install
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "===================================="
Write-Host "Virtual environment created!"
Write-Host "===================================="
