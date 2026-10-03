param(
    [string]$Python = "python",
    [string]$InstallDirectory
)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Push-Location $repo
try {
    & $Python -m PyInstaller --clean --noconfirm packaging/BrakeDesignStudio.spec
    if ($LASTEXITCODE -ne 0) { throw "Build failed; installed application was not changed." }
    $built = Join-Path $repo 'dist/Brake Design Studio'
    $revision = & git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw "Cannot identify source revision." }
    $dirty = [bool](& git status --porcelain)
    @{ commit = $revision; uncommittedChanges = $dirty; builtAtUtc = [DateTime]::UtcNow.ToString('o'); source = $repo } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $built 'build-info.json')
    $oldSmoke = $env:BRAKELAB_SMOKE
    $oldQt = $env:QT_QPA_PLATFORM
    try {
        $env:BRAKELAB_SMOKE = '1'
        $env:QT_QPA_PLATFORM = 'offscreen'
        1..2 | ForEach-Object {
            $process = Start-Process -FilePath (Join-Path $built 'Brake Design Studio.exe') -WindowStyle Hidden -PassThru
            if (-not $process.WaitForExit(60000)) {
                $process.Kill()
                throw "Application launch timed out; installed application was not changed."
            }
            if ($process.ExitCode -ne 0) { throw "Application launch failed: $($process.ExitCode)" }
        }
    } finally {
        $env:BRAKELAB_SMOKE = $oldSmoke
        $env:QT_QPA_PLATFORM = $oldQt
    }
    if ($InstallDirectory) {
        $target = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
        if ($target -eq [IO.Path]::GetPathRoot($target).TrimEnd('\') -or
            $target -eq $repo -or $target -eq $built -or
            $repo.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase) -or
            $target.StartsWith($built + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "Choose a separate application folder, not the repository, build folder, or drive root."
        }
        $running = Get-CimInstance Win32_Process | Where-Object {
            $_.ExecutablePath -and $_.ExecutablePath.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase)
        }
        if ($running) { throw "Close the installed application before updating it." }
        if (Test-Path -LiteralPath $target) {
            $backup = $target + '.backup-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff')
            Move-Item -LiteralPath $target -Destination $backup
        }
        try { Copy-Item -LiteralPath $built -Destination $target -Recurse }
        catch {
            throw "Installation failed. Previous application is preserved at '$backup'. $($_.Exception.Message)"
        }
        Write-Host "Updated application: $target"
        if ($backup) { Write-Host "Previous application: $backup" }
    }
    Write-Host "Built and launched twice successfully: $built"
} finally { Pop-Location }
