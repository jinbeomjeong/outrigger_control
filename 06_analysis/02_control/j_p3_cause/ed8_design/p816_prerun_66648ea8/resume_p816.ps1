# Resume of the P8-16 pre-run (one job lost by a vanished pool worker): the same command with
# --resume (same plan: ed8_probe checks plan_sha256), then p816_compare.
param([Parameter(Mandatory = $true)][string]$OutDir, [Parameter(Mandatory = $true)][string]$ExpectCommit,
    [int]$Workers = 2, [string]$MaskHex = 'FFFF', [string]$Tag = 'resume1')
$ErrorActionPreference = 'Stop'
$Worktree = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-impl'
$Reference = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\raw'
$NumbaCache = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\python-ed8-impl\numba_cache'
$PythonDev = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$Conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
$Head = (git -C $Worktree rev-parse HEAD).Trim()
if ($Head -ne $ExpectCommit) { Write-Output "refused: HEAD $Head"; exit 3 }
if (git -C $Worktree status --porcelain --untracked-files=all) { Write-Output 'refused: not clean'; exit 3 }
$env:MKL_THREADING_LAYER = 'TBB'; $env:NUMBA_CACHE_DIR = $NumbaCache; $env:OMP_NUM_THREADS = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
[ordered]@{ head = $Head; is_clean = $true; started_at = (Get-Date).ToString('o'); mask = $MaskHex; workers = $Workers
    invocation = 'conda run --no-capture-output -n dynamics-dev python -I -B'; resume = $Tag } |
    ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath "$OutDir\run_identity_start_$Tag.json"
Push-Location $Worktree
try {
    & $Conda run --no-capture-output -n dynamics-dev python -I -B 04_scripts\04_hydraulic\coupled\ed8_probe.py `
        --out "$OutDir\p816.jsonl" --part p816 --arms B_impl,L2_impl --resume `
        --r79-plan "$Reference\plans\P814-B-VBKM0.json" --workers $Workers --mask $MaskHex *> "$OutDir\probe_console_$Tag.txt"
    $ProbeCode = $LASTEXITCODE
} finally { Pop-Location }
$DirtyEnd = git -C $Worktree status --porcelain --untracked-files=all
[ordered]@{ head = (git -C $Worktree rev-parse HEAD).Trim(); is_clean = (-not $DirtyEnd); ended_at = (Get-Date).ToString('o')
    probe_exit = $ProbeCode } | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath "$OutDir\run_identity_end_$Tag.json"
& $PythonDev -I -B "$Worktree\04_scripts\04_hydraulic\coupled\p816_compare.py" --reference "$Reference\runs.jsonl" `
    --run "$OutDir\p816.jsonl" --out "$OutDir\p816_compare.json" *> "$OutDir\compare_console.txt"
Write-Output "probe_exit=$ProbeCode compare_exit=$LASTEXITCODE"
Get-Content -LiteralPath "$OutDir\compare_console.txt" -Tail 1
