# Change 12 item 4: short 12a runs of VBL / VBL0 on the r79 / las_t3_dg3 path (Dg-3 keys
# L2 + L3) and the L1 plant_truth path (one L1 key). Code checkout = worktree ed6-impl.
$ErrorActionPreference = 'Stop'
$py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$root = 'C:\workspace\outrigger_control\.claude\worktrees\ed6-impl'
$out = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\python-ed6\12a_v2'
New-Item -ItemType Directory -Force $out | Out-Null
[IO.File]::WriteAllText("$out\dg3_keys.txt", "L2|s0|g6|52|ref|J1|top|Fs0`nL3|s0|g6|5|g6|G1+J1@FR|top|Fs4`n")
[IO.File]::WriteAllText("$out\l1_keys.txt", "L1|s0|g6|52|ref|J1|top|Fs0`n")
$runs = @(
    @{name = 'dg3_VBL'; setting = 'VBL'; levels = 'L2,L3'; keys = 'dg3_keys.txt'; mask = '0x000F'},
    @{name = 'dg3_VBL0'; setting = 'VBL0'; levels = 'L2,L3'; keys = 'dg3_keys.txt'; mask = '0x00F0'},
    @{name = 'L1_VBL'; setting = 'VBL'; levels = 'L1'; keys = 'l1_keys.txt'; mask = '0x0F00'},
    @{name = 'L1_VBL0'; setting = 'VBL0'; levels = 'L1'; keys = 'l1_keys.txt'; mask = '0xF000'}
)
$env:LAS_T3_DG3_K1 = 'on'; $env:LAS_T3_DG3_P3 = 'on'; $env:LAS_T3_DG3_LAS = 'on'
$env:R72_PATH = 'per_leg'; $env:R79_ROD_MODEL = 'plant_truth'; $env:PYTHONDONTWRITEBYTECODE = '1'
$procs = @()
foreach ($run in $runs) {
    $env:R79_V5_SETTING = $run.setting
    $env:R79_T4H_DIR = "$out\$($run.name)_t4h"
    $arguments = @('-I', '-B', '04_scripts/04_hydraulic/coupled/jp3_run_identity.py', 'wrap',
        "`"$out\$($run.name).json`"", '--', $py, '-I', '-B',
        '04_scripts/04_hydraulic/coupled/las_t3_dg3.py', $root, 'run', "`"$out\$($run.name).json`"",
        '--levels', $run.levels, '--keys-file', "`"$out\$($run.keys)`"", '--workers', '2',
        '--affinity', $run.mask)
    $proc = Start-Process -FilePath $py -ArgumentList $arguments -WorkingDirectory $root `
        -RedirectStandardOutput "$out\$($run.name).out.log" -RedirectStandardError "$out\$($run.name).err.log" `
        -NoNewWindow -PassThru
    $procs += $proc
    "$($run.name) pid=$($proc.Id)"
}
$procs | ForEach-Object { $_.Id } | Set-Content "$out\pids.txt"
