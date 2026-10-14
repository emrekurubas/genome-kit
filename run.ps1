# genome-kit launcher for Windows (started by run.bat).
# The analysis tools need Linux, so genome-kit runs inside WSL (Windows Subsystem for Linux). This script makes sure
# WSL is installed and responsive, explains every step, never hangs silently, and asks before changing anything.
param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $KitArgs)
$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'   # newer WSL: print its own messages as UTF-8 instead of UTF-16

function Say([string]$msg, [string]$color = '') { if ($color) { Write-Host $msg -ForegroundColor $color } else { Write-Host $msg } }
function Ask([string]$q) {
    while ($true) {
        $a = (Read-Host "$q [y/n]").Trim().ToLower()
        if ($a -in 'y', 'yes') { return $true }
        if ($a -in 'n', 'no') { return $false }
    }
}
function Finish([int]$code) { Write-Host ''; Read-Host 'Press Enter to close this window' | Out-Null; exit $code }

# Run wsl.exe with a time limit. Returns @{ TimedOut; ExitCode; Out } and never hangs.
function Wsl([string[]]$wslArgs, [int]$seconds = 60, [string]$waitMsg = '') {
    $out = [IO.Path]::GetTempFileName(); $err = [IO.Path]::GetTempFileName()
    # Start-Process joins arguments with plain spaces, so quote any that contain one ('echo ok' must stay one argument).
    $argLine = ($wslArgs | ForEach-Object { if ($_ -match '\s') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' '
    $p = Start-Process -FilePath 'wsl.exe' -ArgumentList $argLine -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    $null = $p.Handle   # keep the process handle open, otherwise ExitCode comes back empty
    $t0 = Get-Date; $shown = $false
    while (-not $p.WaitForExit(1000)) {
        $el = [int]((Get-Date) - $t0).TotalSeconds
        if ($waitMsg -and $el -ge 5) { Write-Host -NoNewline "`r      $waitMsg ($el s of up to $seconds s)   "; $shown = $true }
        if ($el -ge $seconds) {
            try { $p.Kill() } catch {}
            if ($shown) { Write-Host '' }
            return @{ TimedOut = $true; ExitCode = -1; Out = '' }
        }
    }
    if ($shown) { Write-Host '' }
    $p.WaitForExit()   # let the output files be flushed and closed
    $text = ((Get-Content -Raw $out -ErrorAction SilentlyContinue) + (Get-Content -Raw $err -ErrorAction SilentlyContinue)) -replace "`0", ''
    Remove-Item $out, $err -ErrorAction SilentlyContinue
    return @{ TimedOut = $false; ExitCode = $p.ExitCode; Out = "$text".Trim() }
}

function Elevated([string]$command, [string]$why) {
    Say "      This needs administrator rights ($why). Windows will ask you to confirm." 'Yellow'
    try {
        $p = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile', '-Command', $command -Verb RunAs -PassThru -Wait
        return $p.ExitCode -eq 0
    } catch { Say '      The administrator request was declined or failed.' 'Red'; return $false }
}

function Explain-Error([string]$text) {
    if ($text -match '0x80370102|virtualization|Virtual Machine Platform|HCS_E_HYPERV_NOT_INSTALLED|0x80370114') {
        Say '      Windows reports that virtualization is not available, which WSL needs.' 'Yellow'
        # Right after WSL is turned on, this is only Windows waiting for its restart.
        if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') { Offer-Restart }
        Say '      To fix it:'
        Say '        1. Turn on "Virtualization" (Intel VT-x / AMD-V / SVM) in the computer''s BIOS/UEFI settings.'
        Say '        2. In "Turn Windows features on or off", tick "Virtual Machine Platform" and "Windows Subsystem for Linux".'
        Say '        3. Restart, then start run.bat again.'
        return $true
    }
    return $false
}

Write-Host ''
Say 'genome-kit: a private reading of your consumer DNA file' 'Cyan'
Say 'Everything runs on this computer; your DNA file is never uploaded.'
Say 'The analysis tools need Linux, so genome-kit runs inside WSL (Windows Subsystem for Linux), which Windows includes.'
Write-Host ''

# ---------------------------------------------------------------- 1. is WSL installed?
function Test-WslMissing {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { return $true }
    # Windows 11 keeps a small wsl.exe even when WSL is not installed; it only prints a "not installed" note (aka.ms/wslinstall).
    $v = Wsl @('--version') 30
    return (-not $v.TimedOut -and $v.ExitCode -ne 0 -and $v.Out -match 'aka\.ms/wslinstall|is not installed')
}

# After a restart, Windows starts run.bat again by itself (once), so nobody has to remember how to continue.
function Offer-Restart {
    $bat = Join-Path $PSScriptRoot 'run.bat'
    try {
        New-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'genome-kit' -Force `
            -Value "$env:ComSpec /c `"`"$bat`"`"" | Out-Null
        $resume = $true
    } catch { $resume = $false }
    Say '      Windows needs to restart once to finish turning on WSL.' 'Yellow'
    if ($resume) { Say '      genome-kit will start again by itself after the restart, once you sign in.' }
    else { Say '      After the restart, start run.bat again.' }
    if (Ask '      Restart the computer now? (save and close your other work first)') {
        Say '      Restarting in 10 seconds...'
        & shutdown.exe /r /t 10 /c 'Restarting to finish installing WSL for genome-kit.'
        exit 0
    }
    if ($resume) { Say '      No problem. Restart whenever it suits you; genome-kit will continue after you sign in.' }
    Finish 0
}

function Install-Wsl {
    Say '      WSL is not installed on this computer yet. genome-kit can install it for you (a free part of Windows).' 'Yellow'
    if (-not (Ask '      Install WSL now?')) {
        Say '      Nothing changed. To install it later, start run.bat again, or open PowerShell as Administrator and run:  wsl --install'
        Finish 1
    }
    # Turn on both Windows features, note whether Windows needs a restart for them, then install WSL itself.
    $res = Join-Path $env:TEMP 'genome-kit-wsl-install.txt'
    Remove-Item $res -ErrorAction SilentlyContinue
    $cmd = "`$r = @(); foreach (`$f in 'Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform') { try { `$r += (Enable-WindowsOptionalFeature -Online -FeatureName `$f -All -NoRestart -WarningAction SilentlyContinue).RestartNeeded } catch { `$r += `$true } }; " +
           "Write-Host 'Installing WSL (download progress is shown below)...'; wsl.exe --install --no-distribution; " +
           "Set-Content -Path '$res' -Value ('restart=' + (`$r -contains `$true))"
    if (-not (Elevated $cmd 'installing a Windows feature')) {
        Say '      WSL was not installed. You can install it yourself: open PowerShell as Administrator and run:  wsl --install'
        Finish 1
    }
    $needRestart = -not (Test-Path $res) -or ((Get-Content -Raw $res) -match 'restart=True')
    if ($needRestart -or (Test-WslMissing)) { Offer-Restart }
    Say '      WSL is installed.' 'Green'
}

Say '[1/4] Checking that WSL is installed...'
if (Test-WslMissing) { Install-Wsl }

# ---------------------------------------------------------------- 2. does WSL respond?
Say '[2/4] Checking that WSL responds...'
$st = Wsl @('--status') 45 'waiting for WSL to answer'
if ($st.TimedOut) {
    Say '      WSL is not responding. This happens after sleep, Windows updates or Docker changes, and a restart of WSL usually fixes it.' 'Yellow'
    if (-not (Ask '      Restart WSL now? (closes any open Linux windows and stops Docker Desktop''s Linux engine for a moment)')) {
        Say '      Nothing changed. Restart the computer, or run "wsl --shutdown" yourself, then start run.bat again.'; Finish 1
    }
    $sd = Wsl @('--shutdown') 60 'stopping WSL'
    if ($sd.TimedOut) {
        Say '      WSL did not stop on its own. Restarting its Windows service usually helps.' 'Yellow'
        if (Ask '      Restart the WSL service? (administrator rights)') {
            $null = Elevated "Get-Process wsl*,wslhost*,wslservice* -ErrorAction SilentlyContinue | Stop-Process -Force; Restart-Service -Force -Name (Get-Service WSLService,LxssManager -ErrorAction SilentlyContinue | Select-Object -First 1).Name" 'restarting a Windows service'
        }
    }
    $st = Wsl @('--status') 60 'waiting for WSL to start again'
    if ($st.TimedOut) {
        Say '      WSL still does not respond. Please restart the computer, then start run.bat again.' 'Red'
        Say '      If it keeps happening, updating WSL often fixes it: open PowerShell and run  wsl --update'
        Finish 1
    }
    Say '      WSL responds again.' 'Green'
}
if ($st.ExitCode -eq 50 -or $st.Out -match 'is not installed|aka\.ms/wslinstall') { Install-Wsl }
if ($st.ExitCode -ne 0 -and (Explain-Error $st.Out)) { Finish 1 }

# ---------------------------------------------------------------- 3. genome-kit's own Linux system
# genome-kit keeps its own small Ubuntu, named "genome-kit", so it never touches a Linux the person may already use.
# It is always started with a command as root, which skips Ubuntu's first-start questions (user name, password).
$distro = 'genome-kit'
Say '[3/4] Checking genome-kit''s Linux system...'
$ls = Wsl @('--list', '--quiet') 45 'listing installed Linux systems'
$have = (-not $ls.TimedOut -and $ls.ExitCode -eq 0 -and ($ls.Out -split "`r?`n" | ForEach-Object { $_.Trim() }) -contains $distro)
if (-not $have) {
    Say '      genome-kit needs its own small Linux system (Ubuntu): a one-time download of about 500 MB.' 'Yellow'
    Say '      It is separate from anything else on this computer and asks you nothing.'
    if (-not (Ask '      Set it up now?')) { Say '      Nothing changed. Start run.bat again when you are ready.'; Finish 1 }
    & wsl.exe --install Ubuntu --name $distro --no-launch
    $ls = Wsl @('--list', '--quiet') 45 'checking the installation'
    $have = (-not $ls.TimedOut -and $ls.ExitCode -eq 0 -and ($ls.Out -split "`r?`n" | ForEach-Object { $_.Trim() }) -contains $distro)
    if (-not $have) {
        Say '      The Linux system could not be set up. The message above says why.' 'Red'
        Say '      Updating WSL usually helps: open PowerShell and run  wsl --update  then start run.bat again.'
        Finish 1
    }
}
$hello = Wsl @('-d', $distro, '-u', 'root', '-e', 'sh', '-c', 'echo ok') 90 'starting Linux (the first start can take a minute)'
if ($hello.TimedOut -or $hello.Out -notmatch 'ok') {
    if (-not (Explain-Error $hello.Out)) {
        Say '      The Linux system did not start properly.' 'Red'
        if ($hello.Out) { Say "      WSL said: $($hello.Out)" }
        Say '      Try restarting the computer. If that does not help, open PowerShell and run  wsl --update'
    }
    Finish 1
}
Say '      Linux is ready.' 'Green'
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -Name 'genome-kit' -ErrorAction SilentlyContinue

# ---------------------------------------------------------------- 4. run genome-kit inside Linux
$win = (Resolve-Path $PSScriptRoot).Path
$drive = $win.Substring(0, 1).ToLower()
$linuxPath = "/mnt/$drive" + ($win.Substring(2) -replace '\\', '/')
Say '[4/4] Starting genome-kit'
Write-Host ''
& wsl.exe -d $distro -u root --cd $linuxPath bash ./run.sh @KitArgs
$code = $LASTEXITCODE
if ($code -ne 0) { Write-Host ''; Say 'genome-kit stopped with an error. The message above says why.' 'Red' }
Finish $code
