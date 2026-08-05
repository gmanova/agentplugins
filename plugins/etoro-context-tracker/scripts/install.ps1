# Thin Windows wrapper around the cross-platform install.py
# (macOS/Linux: ./install.sh or python3 install.py)
param(
    [ValidateSet('Cursor', 'Claude', 'Codex', 'All')]
    [string]$Target = 'All',

    [string]$Python = '',

    [switch]$AlsoSyncGlobalRule,
    [switch]$RemoveGlobalRule
)

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot
$InstallPy = Join-Path $ScriptDir 'install.py'
if (-not (Test-Path $InstallPy)) {
    throw "install.py not found next to install.ps1: $InstallPy"
}

function Resolve-Python {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path $Explicit)) { return (Resolve-Path $Explicit).Path }
    foreach ($name in @('python3', 'python', 'py')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($name -eq 'py') {
            try {
                $ver = & py -3 -c "import sys; print(sys.executable)" 2>$null
                if ($ver) { return $ver.Trim() }
            } catch {}
            continue
        }
        try {
            $major = & $cmd.Source -c "import sys; print(sys.version_info.major)" 2>$null
            if ($major -eq '3') { return $cmd.Source }
        } catch {}
    }
    throw "Need Python 3 on PATH (python3, python, or py -3). Or pass -Python C:\Path\python.exe"
}

$py = Resolve-Python -Explicit $Python
$argv = @($InstallPy, '--target', $Target.ToLowerInvariant())
if ($AlsoSyncGlobalRule) { $argv += '--also-sync-global-rule' }
if ($RemoveGlobalRule) { $argv += '--remove-global-rule' }
if ($Python) { $argv += @('--python', $py) }

Write-Host "Delegating to install.py via $py"
& $py @argv
exit $LASTEXITCODE
