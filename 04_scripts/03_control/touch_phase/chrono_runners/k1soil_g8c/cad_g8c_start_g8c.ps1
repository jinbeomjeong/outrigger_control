# Detached, labelled start of g8c_runner.py (project rule: WMI + window title). -DryRun prints the command line only.
param([string[]]$Rows = @('E1', 'R2', 'R3', 'R2L1', 'R3L1'), [ValidateSet(3, 4, 5)][int]$Slots = 3, [switch]$DryRun)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$log = Join-Path $here 'logs\console.log'
New-Item -ItemType Directory -Force (Join-Path $here 'logs') | Out-Null
$title = "[Chrono] G8C3 $($Rows.Count)건 - 닫지 마세요"
$time = if ($Slots -ge 5) { '예상 약 12분, FAULT 행이 있으면 최대 약 20분' } else { '5건 기준 예상 약 21분, FAULT 행이 있으면 최대 약 30분' }
$lines = @(
    "G8C3 강체 Chrono: edge RL g230 C4G2 L1-R, rpB RL g230 끔 켬 L2b Fs4 및 L1-R Fs0. 행 $($Rows -join ' ')",
    "P 코어 $Slots 슬롯, OMP 4. $time",
    "진행: $here\logs\runner.log",
    '결과: C:\workspace\outrigger_control\07_results\S9\batch_g8c3_20261105',
    '이 창을 닫으면 중단됩니다'
)
$echo = ($lines | ForEach-Object { "echo $_" }) -join '&& '
$cmd = "cmd.exe /c title $title&& $echo&& `"$py`" -I -B -X utf8 -u `"$here\g8c_runner.py`" --rows $($Rows -join ' ') --slots $Slots > `"$log`" 2>&1"
if ($DryRun) { Write-Output $cmd; return }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $here }
Write-Output "ReturnValue $($r.ReturnValue) cmd pid $($r.ProcessId)"
