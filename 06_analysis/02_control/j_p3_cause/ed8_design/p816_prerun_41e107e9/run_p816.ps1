# P8-16 pre-run (spec v8 12 P8-16, time point 1: the implementation commit, before C8).
# Runs ed8_probe --part p816 --arms B_impl,L2_impl from the ed8-impl worktree with conda run
# (the P8-14 invocation), then p816_compare against the P8-14 raw/runs.jsonl.
param(
    [Parameter(Mandatory = $true)][string]$OutDir,
    [Parameter(Mandatory = $true)][string]$ExpectCommit,
    [string]$MaskHex = 'FFFF',
    [int]$Workers = 8
)
$ErrorActionPreference = 'Stop'
$Worktree = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-impl'
$Reference = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\raw'
$NumbaCache = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\python-ed8-c8t8\numba_cache'
$PythonDev = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$Conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'

if (Test-Path -LiteralPath $OutDir) { Write-Output "refused: $OutDir exists"; exit 2 }
$Head = (git -C $Worktree rev-parse HEAD).Trim()
if ($Head -ne $ExpectCommit) { Write-Output "refused: HEAD $Head is not $ExpectCommit"; exit 3 }
$Dirty = git -C $Worktree status --porcelain --untracked-files=all
if ($Dirty) { Write-Output "refused: worktree not clean"; exit 3 }
New-Item -ItemType Directory -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $NumbaCache | Out-Null

$env:MKL_THREADING_LAYER = 'TBB'
$env:NUMBA_CACHE_DIR = $NumbaCache
$env:OMP_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$Start = [ordered]@{ head = $Head; is_clean = $true; started_at = (Get-Date).ToString('o');
    mask = $MaskHex; workers = $Workers; invocation = 'conda run --no-capture-output -n dynamics-dev python -I -B' }
$Start | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath "$OutDir\run_identity_start.json"

Push-Location $Worktree
try {
    & $Conda run --no-capture-output -n dynamics-dev python -I -B 04_scripts\04_hydraulic\coupled\ed8_probe.py `
        --out "$OutDir\p816.jsonl" --part p816 --arms B_impl,L2_impl `
        --r79-plan "$Reference\plans\P814-B-VBKM0.json" --workers $Workers --mask $MaskHex *> "$OutDir\probe_console.txt"
    $ProbeCode = $LASTEXITCODE
} finally { Pop-Location }

$HeadEnd = (git -C $Worktree rev-parse HEAD).Trim()
$DirtyEnd = git -C $Worktree status --porcelain --untracked-files=all
[ordered]@{ head = $HeadEnd; is_clean = (-not $DirtyEnd); ended_at = (Get-Date).ToString('o');
    probe_exit = $ProbeCode } | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath "$OutDir\run_identity_end.json"

& $PythonDev -I -B "$Worktree\04_scripts\04_hydraulic\coupled\p816_compare.py" --reference "$Reference\runs.jsonl" `
    --run "$OutDir\p816.jsonl" --out "$OutDir\p816_compare.json" *> "$OutDir\compare_console.txt"
$CompareCode = $LASTEXITCODE
Write-Output "probe_exit=$ProbeCode compare_exit=$CompareCode head_end=$HeadEnd clean_end=$(-not $DirtyEnd)"
Get-Content -LiteralPath "$OutDir\compare_console.txt" -Tail 1

