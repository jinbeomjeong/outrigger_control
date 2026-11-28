$ErrorActionPreference = 'Stop'
$main = 'C:\workspace\outrigger_control'
$wt = Join-Path $main '.claude\worktrees\ed9-impl'
$runs = Join-Path $main '06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$out = Join-Path $main '06_analysis\02_control\j_p3_cause\ed9_design\d1_prerun\judge_smoke_320a1f64'
$py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
New-Item -ItemType Directory -Force $out | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location $wt
$common = @('04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py', 'stage5',
    '--keys', (Join-Path $main '06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json'),
    '--grid-keys', (Join-Path $main '06_analysis\02_control\j_p3_cause\ed6_design\keys\confirm_b_grid192.json'),
    '--grid-root', $main,
    '--v0-rows', (Join-Path $runs 'ho_v0_a1\ed8_heldout_v0.jsonl'), '--step-done', (Join-Path $runs 'ho_v0.done'),
    '--v0-rows', (Join-Path $runs 'ho_aa2_a1\ed8_heldout_aa2.jsonl'), '--step-done', (Join-Path $runs 'ho_aa2.done'),
    '--v0-rows', (Join-Path $runs 'ho_aa3_a1\ed8_heldout_aa3.jsonl'), '--step-done', (Join-Path $runs 'ho_aa3.done'))
foreach ($ruleSet in 'ed8', 'ed8_j7a', 'ed9') {
    $report = Join-Path $out "stage5_$ruleSet.json"
    $log = Join-Path $out "stage5_$ruleSet.console.txt"
    "start $(Get-Date -Format o)" | Set-Content -Encoding utf8 $log
    & $py -I -B @common '--rule-set' $ruleSet '--out' $report *>> $log
    "exit $LASTEXITCODE end $(Get-Date -Format o)" | Add-Content -Encoding utf8 $log
}
& $py -I -B 04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py aa-candidates --keys (Join-Path $main '06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json') --rule-set ed9 --out (Join-Path $out 'aa_candidates_ed9.json') *> (Join-Path $out 'aa_candidates_ed9.console.txt')
"aa-candidates exit $LASTEXITCODE" | Add-Content -Encoding utf8 (Join-Path $out 'aa_candidates_ed9.console.txt')
