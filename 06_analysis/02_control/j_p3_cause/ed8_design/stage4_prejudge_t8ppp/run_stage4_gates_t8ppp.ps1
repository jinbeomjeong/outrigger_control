# Stage 4 gate judgement at T8''' 2263b246 (prejudge_report.md 4 draft with the judge checkout,
# the output folder and the clean check changed). Run by the main session after P8-4 ends and the
# P8-4 __pycache__ folders in ed8-judge3 are removed. Stop and ask on any exit other than 0.
$ErrorActionPreference = 'Stop'
$JudgeRoot = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3'
$JudgeHead = '2263b2461238da7f93eda147838c01c847315561'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$RunRoot = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$OutRoot = Join-Path $RunRoot 'judge_2263b246'
if (Test-Path -LiteralPath $OutRoot) { throw "output folder exists: $OutRoot" }
$head = (& git -C $JudgeRoot rev-parse HEAD).Trim()
if ($head -ne $JudgeHead) { throw "judge HEAD $head" }
$dirty = & git -C $JudgeRoot status --porcelain --ignored
if ($dirty) { throw 'judge checkout not clean (tracked, untracked or ignored files)' }
$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\judge_2263b246'
$Gate = '04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py'
$Ed8 = '04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py'
$Codes = [ordered]@{}
Push-Location -LiteralPath $JudgeRoot
try {
    & $Py -I -B $Gate p80 --rows "$RunRoot\impl_p80_a1\ed7_probe_a2.jsonl" --step-done "$RunRoot\impl_p80.done" --reference 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl' --out "$OutRoot\p80.json"
    $Codes['p80'] = $LASTEXITCODE
    & $Py -I -B $Gate p816 --rows "$RunRoot\impl_p816_a1\p816.jsonl" --step-done "$RunRoot\impl_p816.done" --reference 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\raw\runs.jsonl' --out "$OutRoot\p816.json"
    $Codes['p816'] = $LASTEXITCODE
    & $Py -I -B $Gate p85 --rows "$RunRoot\impl_p85_a1\p85.jsonl" --step-done "$RunRoot\impl_p85.done" --out "$OutRoot\p85.json"
    $Codes['p85'] = $LASTEXITCODE
    & $Py -I -B $Gate p88 --rows "$RunRoot\impl_p88_a1\p88.jsonl" --step-done "$RunRoot\impl_p88.done" --out "$OutRoot\p88.json"
    $Codes['p88'] = $LASTEXITCODE
    & $Py -I -B $Gate p815 --rows "$RunRoot\impl_p815_a1\p815.jsonl" --step-done "$RunRoot\impl_p815.done" --out "$OutRoot\p815.json"
    $Codes['p815'] = $LASTEXITCODE
    & $Py -I -B $Gate t8 --rows "$RunRoot\impl_t8_a1\ed8_t8.jsonl" --step-done "$RunRoot\impl_t8.done" --main-jsonl 'C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl' --out "$OutRoot\t8.json"
    $Codes['t8'] = $LASTEXITCODE
    & $Py -I -B $Ed8 cases --rows "$RunRoot\impl_cases_a1\ed8_cases.jsonl" --step-done "$RunRoot\impl_cases.done" --out "$OutRoot\cases.json"
    $Codes['cases'] = $LASTEXITCODE
    & $Py -I -B $Ed8 l1ref --rows "$RunRoot\l1ref_a1\L1_VBN0.json" --rows "$RunRoot\l1ref_a1\L1_VBN.json" --rows "$RunRoot\l1ref_a1\L1a_VBN0.json" --rows "$RunRoot\l1ref_a1\L1a_VBN.json" --step-done "$RunRoot\l1ref.done" --out "$OutRoot\l1ref.json"
    $Codes['l1ref'] = $LASTEXITCODE
}
finally {
    Pop-Location
}
foreach ($name in $Codes.Keys) { Write-Output "$name exit $($Codes[$name])" }
$after = & git -C $JudgeRoot status --porcelain
if ($after) { Write-Output 'WARNING: judge checkout changed' }
