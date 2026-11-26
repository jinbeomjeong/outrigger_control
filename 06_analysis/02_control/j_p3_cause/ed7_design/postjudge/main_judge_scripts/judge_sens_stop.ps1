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
$v0   = "$main\06_analysis\03_hydraulic\coupled\v5\main.jsonl"
$ft   = "$c\ed7_design\fixed_table_b46bdf8f\fixed_table_a2.json"
$sensKeys = "$c\ed7_design\keys_seal_b46bdf8f\sens_keys_ed7.json"
function Get-DoneFolder($s) { (Get-Content -Raw "$runs\$s.done" | ConvertFrom-Json).folder }
$mainFolder = Get-DoneFolder 'j9main'
$sensFolder = Get-DoneFolder 'sens'
foreach ($d in "$judgeRoot\j9main_a1", "$judgeRoot\sens_a1") {
    if (Test-Path $d) { throw "exists: $d" }
    New-Item -ItemType Directory -Path $d | Out-Null
}
Set-Location $wtj
& $dpy -I -B $tool j9main --edition 7 --rows "$mainFolder\j9_main.jsonl" --v0 $v0 --step-done "$runs\j9main.done" --out "$judgeRoot\j9main_a1\j9main.json" *> "$judgeRoot\j9main_a1\console.log"
"j9main exit=$LASTEXITCODE"
& $dpy -I -B $tool sens --rows "$sensFolder\sens.jsonl" --v0 $v0 --fixed-table $ft --step-done "$runs\sens.done" --keys $sensKeys --out "$judgeRoot\sens_a1\sens.json" *> "$judgeRoot\sens_a1\console.log"
"sens exit=$LASTEXITCODE"
