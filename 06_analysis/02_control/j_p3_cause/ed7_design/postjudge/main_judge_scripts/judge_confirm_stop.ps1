$ErrorActionPreference = 'Stop'
$env:MKL_THREADING_LAYER = 'TBB'
$env:NUMBA_CACHE_DIR = "$env:TEMP\ed7_judge_numba"
$dpy  = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$main = 'C:\workspace\outrigger_control'
$c    = "$main\06_analysis\02_control\j_p3_cause"
$wtj  = "$main\.claude\worktrees\ed7-judge"
$runs = "$c\j9_runs\8a2a52ce"
$judgeRoot = "$runs\judge_60ebb4a4"
$tool = '04_scripts/04_hydraulic/coupled/jp3_ed7_judge.py'
$ft   = "$c\ed7_design\fixed_table_b46bdf8f\fixed_table_a2.json"
$grid = "$c\ed6_design\keys\confirm_b_grid192.json"
$cfFolder = (Get-Content -Raw "$runs\confirm.done" | ConvertFrom-Json).folder
$outDir = "$judgeRoot\confirm_a1"
if (Test-Path $outDir) { throw "exists: $outDir" }
New-Item -ItemType Directory -Path $outDir | Out-Null
Set-Location $wtj
& $dpy -I -B $tool confirm --g1-keys "$c\ed7_design\keys_seal_b46bdf8f\confirm_g1_grid171.json" --g1-rows "$cfFolder\confirm_g1.jsonl" --d-rows "$cfFolder\ed7_probe_d.jsonl" --step-done "$runs\confirm.done" --fixed-table $ft --grid-keys $grid --grid-root $main --out "$outDir\confirm.json" *> "$outDir\console.log"
"confirm exit=$LASTEXITCODE"
