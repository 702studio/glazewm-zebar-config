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

# Detect local execution vs web download
$isLocal = $false
$localRoot = ""
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "glaze_autotile.py"))) {
    $isLocal = $true
    $localRoot = $PSScriptRoot
} elseif (Test-Path "glaze_autotile.py") {
    $isLocal = $true
    $localRoot = $PWD.Path
}

# 1. Dependency Validation: Python (Safe check to avoid Microsoft Store popups)
Write-Host "`n[1/5] Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$pythonOk = $false

if ($null -ne $pythonCmd) {
    # If it points to WindowsApps, it might be the fake Microsoft Store shortcut.
    # We run a quick 2-second inline check to verify if Python actually executes.
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        $process = Start-Process python -ArgumentList '-c "print(\"ok\")"' -NoNewWindow -PassThru -RedirectStandardOutput $tempFile -ErrorAction SilentlyContinue
        if ($process) {
            $process | Wait-Process -Timeout 2 -ErrorAction SilentlyContinue
            if ($process.HasExited -and $process.ExitCode -eq 0) {
                $output = Get-Content $tempFile -ErrorAction SilentlyContinue
                if ($output -eq "ok") {
                    $pythonOk = $true
                }
            } else {
                # Clean up frozen process if it's the Microsoft Store shortcut
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        # Silent ignore, $pythonOk remains false
    } finally {
        if (Test-Path $tempFile) { Remove-Item $tempFile -Force -ErrorAction SilentlyContinue }
    }
}

if ($pythonOk) {
    Write-Host "[OK] Python found at: $($pythonCmd.Source)" -ForegroundColor Green
    Write-Host "Checking/Installing required 'websockets' Python library..." -ForegroundColor Yellow
    try {
        & python -m pip install websockets --quiet
        Write-Host "[OK] Python websockets package is ready." -ForegroundColor Green
    } catch {
        Write-Warning "Could not install 'websockets' automatically. Please run: pip install websockets"
    }
} else {
    Write-Warning "Python 3.10+ was not found or is not fully configured on your system."
    Write-Host "The glaze_autotile script requires Python to manage AwesomeWM dynamic layouts." -ForegroundColor Yellow
    Write-Host "You can quickly install it by running this command in a new terminal:" -ForegroundColor Gray
    Write-Host "  winget install Python.Python.3.11" -ForegroundColor Cyan
}

# 2. Stop running instances to prevent file lock issues
Write-Host "`n[2/5] Stopping running instances of GlazeWM and Zebar to prevent file locks..." -ForegroundColor Yellow
$glazeProc = Get-Process glazewm -ErrorAction SilentlyContinue
$zebarProc = Get-Process zebar -ErrorAction SilentlyContinue

if ($glazeProc) {
    Write-Host "Stopping glazewm.exe..." -ForegroundColor Gray
    Stop-Process -Name glazewm -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}
if ($zebarProc) {
    Write-Host "Stopping zebar.exe..." -ForegroundColor Gray
    Stop-Process -Name zebar -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}
Write-Host "[OK] Applications stopped." -ForegroundColor Green

# 3. Create Target Folders
Write-Host "`n[3/5] Creating configuration directories..." -ForegroundColor Yellow
$dirs = @($glazeConfigDir, $zebarConfigDir, $zebarPackDir, (Join-Path $zebarPackDir "resources"), $binDir)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        try {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "Created folder: $dir" -ForegroundColor Gray
        } catch {
            Write-Error "Failed to create directory: $dir. Please check your user permissions."
        }
    }
}
Write-Host "[OK] Directories ready." -ForegroundColor Green

# 4. Copy / Download Files
Write-Host "`n[4/5] Syncing configuration files..." -ForegroundColor Yellow

$filesToSync = @(
    @{ Src = "glaze_autotile.py"; Dest = Join-Path $userHome "glaze_autotile.py" },
    @{ Src = "glaze-restart.bat"; Dest = Join-Path $userHome "glaze-restart.bat" },
    @{ Src = "bin/change_scale.ps1"; Dest = Join-Path $binDir "change_scale.ps1" },
    @{ Src = "bin/SetDpi.exe"; Dest = Join-Path $binDir "SetDpi.exe" },
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
    try {
        if ($isLocal) {
            $srcPath = Join-Path $localRoot $file.Src
            Copy-Item -Path $srcPath -Destination $destPath -Force
            Write-Host "Copied local: $($file.Src)" -ForegroundColor Gray
        } else {
            $url = "$rawBaseUrl/$($file.Src)"
            Write-Host "Downloading: $($file.Src)..." -ForegroundColor Gray
            Invoke-RestMethod -Uri $url -OutFile $destPath -TimeoutSec 15
        }
    } catch {
        Write-Warning "Failed to sync file: $($file.Src). Re-trying once..."
        try {
            Start-Sleep -Seconds 1
            if ($isLocal) {
                Copy-Item -Path $srcPath -Destination $destPath -Force
            } else {
                Invoke-RestMethod -Uri $url -OutFile $destPath -TimeoutSec 15
            }
            Write-Host "[OK] Successfully synced after retry." -ForegroundColor Green
        } catch {
            Write-Error "Failed permanently to sync $($file.Src). Details: $_"
        }
    }
}
Write-Host "[OK] Configuration files synced." -ForegroundColor Green

# 5. Tailor Configuration Paths Dynamically
Write-Host "`n[5/5] Tailoring configurations to your local system..." -ForegroundColor Yellow
$homeUrlStyle = $userHome.Replace('\', '/')

# Update config.yaml path placeholders
$yamlPath = Join-Path $glazeConfigDir "config.yaml"
if (Test-Path $yamlPath) {
    try {
        $content = Get-Content $yamlPath -Raw
        $newContent = $content.Replace("{{USERPROFILE_FORWARD}}", $homeUrlStyle)
        Set-Content $yamlPath $newContent -Force
        Write-Host "[OK] GlazeWM config.yaml updated dynamically." -ForegroundColor Gray
    } catch {
        Write-Warning "Could not customize config.yaml: $_"
    }
}

# Update change_scale.ps1 path placeholders
$scaleScriptPath = Join-Path $binDir "change_scale.ps1"
if (Test-Path $scaleScriptPath) {
    try {
        $content = Get-Content $scaleScriptPath -Raw
        $newContent = $content.Replace("{{USERPROFILE_BACKWARD}}", $userHome)
        Set-Content $scaleScriptPath $newContent -Force
        Write-Host "[OK] change_scale.ps1 updated dynamically." -ForegroundColor Gray
    } catch {
        Write-Warning "Could not customize change_scale.ps1: $_"
    }
}

# Update with-glazewm.html path placeholders
$htmlPath = Join-Path $zebarPackDir "with-glazewm.html"
if (Test-Path $htmlPath) {
    try {
        $content = Get-Content $htmlPath -Raw
        $newContent = $content.Replace("{{USERPROFILE_FORWARD}}", $homeUrlStyle)
        Set-Content $htmlPath $newContent -Force
        Write-Host "[OK] Zebar with-glazewm.html updated dynamically." -ForegroundColor Gray
    } catch {
        Write-Warning "Could not customize with-glazewm.html: $_"
    }
}

# 6. Startup Applications
Write-Host "`nDiscovering installation paths for GlazeWM..." -ForegroundColor Yellow
$glazeExePath = "C:\Program Files\glzr.io\GlazeWM\glazewm.exe"
if (-not (Test-Path $glazeExePath)) {
    $altPaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\GlazeWM\glazewm.exe"),
        (Join-Path $userHome "scoop\apps\glazewm\current\glazewm.exe")
    )
    foreach ($path in $altPaths) {
        if (Test-Path $path) {
            $glazeExePath = $path
            break
        }
    }
}
if (-not (Test-Path $glazeExePath)) {
    # Fallback to PATH search
    $findGlaze = Get-Command glazewm -ErrorAction SilentlyContinue
    if ($findGlaze) {
        $glazeExePath = $findGlaze.Source
    } else {
        $glazeExePath = $null
    }
}

if ($null -eq $glazeExePath) {
    Write-Host "GlazeWM / Zebar was not detected on your system." -ForegroundColor Yellow
    $response = "n"
    if ([Environment]::UserInteractive) {
        try {
            Write-Host "Would you like to install GlazeWM and Zebar automatically via Windows Package Manager (winget)? (y/n)" -ForegroundColor Cyan
            $response = Read-Host
        } catch {
            $response = "n"
        }
    }
    
    if ($response -eq 'y' -or $response -eq 'yes') {
        Write-Host "Installing GlazeWM..." -ForegroundColor Gray
        try {
            & winget install glzr-io.glazewm --accept-package-agreements --accept-source-agreements --exact
            Write-Host "Installing Zebar..." -ForegroundColor Gray
            & winget install glzr-io.zebar --accept-package-agreements --accept-source-agreements --exact
            
            # Re-verify path after installation
            $glazeExePath = "C:\Program Files\glzr.io\GlazeWM\glazewm.exe"
            if (-not (Test-Path $glazeExePath)) {
                $findGlaze = Get-Command glazewm -ErrorAction SilentlyContinue
                if ($findGlaze) { $glazeExePath = $findGlaze.Source }
            }
        } catch {
            Write-Warning "winget installation encountered an error: $_"
        }
    } else {
        Write-Warning "GlazeWM/Zebar is not installed. To install them manually, run:"
        Write-Host "  winget install glzr-io.glazewm" -ForegroundColor Cyan
        Write-Host "  winget install glzr-io.zebar" -ForegroundColor Cyan
    }
}

if ($null -ne $glazeExePath) {
    Write-Host "[OK] GlazeWM found at: $glazeExePath" -ForegroundColor Green
    Write-Host "Starting GlazeWM (Zebar status bar will auto-launch with it)..." -ForegroundColor Cyan
    try {
        Start-Process -FilePath $glazeExePath -WindowStyle Hidden
        Write-Host "[OK] Application environment started successfully!" -ForegroundColor Green
    } catch {
        Write-Warning "Could not start GlazeWM automatically. Please launch it manually."
    }
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " Installation Successful! Your system is now configured. " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
