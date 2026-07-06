# Windows Customization Environment Installer (GlazeWM + Zebar)
# This script can be run locally or via:
# irm https://raw.githubusercontent.com/tolgaozisik/glazewm-zebar-config/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

# Configurations
$repoOwner = "tolgaozisik"
$repoName = "glazewm-zebar-config"
$branch = "main"
$rawBaseUrl = "https://raw.githubusercontent.com/$repoOwner/$repoName/$branch"

$userHome = $env:USERPROFILE
$glazeConfigDir = Join-Path $userHome ".glzr\glazewm"
$zebarConfigDir = Join-Path $userHome ".glzr\zebar"
$zebarPackDir = Join-Path $userHome "AppData\Roaming\zebar\downloads\glzr-io.starter@0.0.0"
$binDir = Join-Path $userHome "bin"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting GlazeWM & Zebar Custom Environment Installation " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Dependency Validation: Python
Write-Host "`n[1/5] Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCmd) {
    Write-Warning "Python was not found on your system. The autotiler requires Python 3.10+."
    Write-Host "You can download it from: https://www.python.org/downloads/" -ForegroundColor Gray
} else {
    Write-Host "✔ Python found at: $($pythonCmd.Source)" -ForegroundColor Green
    
    Write-Host "Checking/Installing required 'websockets' Python library..." -ForegroundColor Yellow
    try {
        & python -m pip install websockets --quiet
        Write-Host "✔ Python websockets package is ready." -ForegroundColor Green
    } catch {
        Write-Warning "Could not install 'websockets' automatically. Please run: pip install websockets"
    }
}

# 2. Folder Creation
Write-Host "`n[2/5] Creating configuration directories..." -ForegroundColor Yellow
$dirs = @($glazeConfigDir, $zebarConfigDir, $zebarPackDir, Join-Path $zebarPackDir "resources", $binDir)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Gray
    }
}
Write-Host "✔ Directories ready." -ForegroundColor Green

# 3. Source Selection & File Sync
Write-Host "`n[3/5] Syncing configuration files..." -ForegroundColor Yellow
$isLocal = Test-Path (Join-Path $PSScriptRoot "glaze_autotile.py") -ErrorAction SilentlyContinue

$filesToSync = @(
    @{ Src = "glaze_autotile.py"; Dest = Join-Path $userHome "glaze_autotile.py" },
    @{ Src = "glaze-restart.bat"; Dest = Join-Path $userHome "glaze-restart.bat" },
    @{ Src = "bin/change_scale.ps1"; Dest = Join-Path $binDir "change_scale.ps1" },
    @{ Src = "glazewm/config.yaml"; Dest = Join-Path $glazeConfigDir "config.yaml" },
    @{ Src = "zebar/settings.json"; Dest = Join-Path $zebarConfigDir "settings.json" },
    @{ Src = "zebar/packs/glzr-io.starter/zpack.json"; Dest = Join-Path $zebarPackDir "zpack.json" },
    @{ Src = "zebar/packs/glzr-io.starter/styles.css"; Dest = Join-Path $zebarPackDir "styles.css" },
    @{ Src = "zebar/packs/glzr-io.starter/with-glazewm.html"; Dest = Join-Path $zebarPackDir "with-glazewm.html" },
    @{ Src = "zebar/packs/glzr-io.starter/with-komorebi.html"; Dest = Join-Path $zebarPackDir "with-komorebi.html" },
    @{ Src = "zebar/packs/glzr-io.starter/vanilla.html"; Dest = Join-Path $zebarPackDir "vanilla.html" },
    @{ Src = "zebar/packs/glzr-io.starter/README.md"; Dest = Join-Path $zebarPackDir "README.md" },
    @{ Src = "zebar/packs/glzr-io.starter/resources/preview-image-1.png"; Dest = Join-Path $zebarPackDir "resources\preview-image-1.png" }
)

foreach ($file in $filesToSync) {
    $destPath = $file.Dest
    if ($isLocal) {
        $srcPath = Join-Path $PSScriptRoot $file.Src
        Copy-Item -Path $srcPath -Destination $destPath -Force
        Write-Host "Copied local: $($file.Src)" -ForegroundColor Gray
    } else {
        $url = "$rawBaseUrl/$($file.Src)"
        Write-Host "Downloading: $($file.Src)..." -ForegroundColor Gray
        Invoke-RestMethod -Uri $url -OutFile $destPath
    }
}
Write-Host "✔ Configurations copied." -ForegroundColor Green

# 4. Tailoring Configurations (User Path Replacement)
Write-Host "`n[4/5] Tailoring configurations to your home folder..." -ForegroundColor Yellow
$homeUrlStyle = $userHome.Replace('\', '/')

# Update config.yaml path placeholders
$yamlPath = Join-Path $glazeConfigDir "config.yaml"
if (Test-Path $yamlPath) {
    $content = Get-Content $yamlPath -Raw
    $newContent = $content.Replace("C:/Users/tolgaozisik", $homeUrlStyle)
    Set-Content $yamlPath $newContent -Force
    Write-Host "✔ GlazeWM config.yaml updated dynamically." -ForegroundColor Gray
}

# Update change_scale.ps1 path placeholders
$scaleScriptPath = Join-Path $binDir "change_scale.ps1"
if (Test-Path $scaleScriptPath) {
    $content = Get-Content $scaleScriptPath -Raw
    $newContent = $content.Replace("C:\Users\tolgaozisik", $userHome)
    Set-Content $scaleScriptPath $newContent -Force
    Write-Host "✔ change_scale.ps1 updated dynamically." -ForegroundColor Gray
}
Write-Host "✔ Dynamic path updates completed." -ForegroundColor Green

# 5. Reload Application State
Write-Host "`n[5/5] Checking for running instances of GlazeWM and Zebar..." -ForegroundColor Yellow
$glazeProc = Get-Process glazewm -ErrorAction SilentlyContinue
$zebarProc = Get-Process zebar -ErrorAction SilentlyContinue

if ($glazeProc -or $zebarProc) {
    Write-Host "Running instances found. Would you like to restart them now to apply config? (y/n)" -ForegroundColor Cyan
    $response = Read-Host
    if ($response -eq 'y' -or $response -eq 'yes') {
        Write-Host "Restarting GlazeWM..." -ForegroundColor Gray
        Stop-Process -Name glazewm -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        
        Write-Host "Restarting Zebar..." -ForegroundColor Gray
        Stop-Process -Name zebar -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        
        # Start GlazeWM (Zebar is launched automatically by glazewm config startup command)
        Start-Process -FilePath "glazewm.exe" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Write-Host "✔ Applications restarted successfully!" -ForegroundColor Green
    } else {
        Write-Host "Skipped restart. Please restart GlazeWM/Zebar manually or press Alt+Shift+R to reload Glaze config." -ForegroundColor Cyan
    }
} else {
    Write-Host "GlazeWM/Zebar is not currently running. Start them normally to load configurations." -ForegroundColor Gray
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Installation Successful! Your system is now configured. " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
