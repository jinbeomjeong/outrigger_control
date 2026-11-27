#Requires -Version 7
# Stage 4 gate re-judgement at T8'''' 7ea78232 (decision D-2, 2026-11-27: the eight stage 4 gates
# again with the fixed P8-0 line key; C8 is not rerun; judge_2263b246 is kept as superseded).
# Copy of stage4_prejudge_t8ppp\run_stage4_gates_t8ppp.ps1 with the judge checkout, the head, the
# output folder, the numba cache and the clean checks changed; the gate arguments are the same.
# Run by the main session after the formal P8-4 at 7ea78232 has ended (its p84.done) and its
# ignored __pycache__ folders in ed8-judge4 are removed (t8pppp_evidence\clean_pycache.py).
# Exit: 0 every gate exit 0 / 1 a gate exit other than 0 (stop and ask) / 4 the judge checkout
# changed during the run (stop and ask). A throw before the first gate writes nothing.
$ErrorActionPreference = 'Stop'
$JudgeRoot = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4'
$JudgeHead = '7ea782323c427917709ecbb365a58044449beac2'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$RunRoot = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$OutRoot = Join-Path $RunRoot 'judge_7ea78232'
$P84Done = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84_t8pppp_7ea78232\out\p84.done'
if (Test-Path -LiteralPath $OutRoot) { throw "output folder exists: $OutRoot" }
if (-not (Test-Path -LiteralPath $P84Done)) { throw "P8-4 at 7ea78232 has not ended: $P84Done" }
$headBefore = (& git -C $JudgeRoot rev-parse HEAD)
if ($LASTEXITCODE -ne 0) { throw 'git rev-parse failed' }
if ($headBefore.Trim() -ne $JudgeHead) { throw "judge HEAD $headBefore" }
$dirtyBefore = @(& git -C $JudgeRoot status --porcelain --ignored)
if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
if ($dirtyBefore.Count -ne 0) {
    throw "judge checkout not clean (tracked, untracked or ignored): $($dirtyBefore.Count) lines"
}
$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\judge_7ea78232'
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
foreach ($gateName in $Codes.Keys) { Write-Output "$gateName exit $($Codes[$gateName])" }
$headAfter = (& git -C $JudgeRoot rev-parse HEAD)
$dirtyAfter = @(& git -C $JudgeRoot status --porcelain --ignored)
if ($headAfter.Trim() -ne $JudgeHead -or $dirtyAfter.Count -ne 0) {
    Write-Output "STOP: judge checkout changed (head $headAfter, $($dirtyAfter.Count) status lines)"
    exit 4
}
$nonZero = @($Codes.Keys | Where-Object { $Codes[$_] -ne 0 })
if ($nonZero.Count -ne 0) { exit 1 }
exit 0
