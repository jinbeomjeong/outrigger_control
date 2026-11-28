# ed9 R4: stage5 design reading at T9' (ed9-t9b). Prints only exit code and status.
$Py  = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$WTJ = 'C:\workspace\outrigger_control\.claude\worktrees\ed9-t9b'
$J   = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause'
$K   = "$J\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json"
$B   = "$J\ed9_design\r3_runs\r3b_on_15d3a4a4"
$O   = "$J\ed9_design\r3_runs\r4_c79b009a"
New-Item -ItemType Directory -Force $O | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed9-r3\numba_cache\r4'
Push-Location $WTJ
$t0 = Get-Date -Format s
& $Py -I -B 04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py stage5 --rule-set ed9 --design-reading `
    --keys $K --grid-keys "$J\ed6_design\keys\confirm_b_grid192.json" --grid-root C:\workspace\outrigger_control `
    --v0-rows "$B\ho_v0_a1\ed9_heldout_v0.jsonl" --step-done "$B\ho_v0.done" `
    --v0-rows "$B\ho_aa2_a1\ed9_heldout_aa2.jsonl" --step-done "$B\ho_aa2.done" `
    --v0-rows "$B\ho_aa3_a1\ed9_heldout_aa3.jsonl" --step-done "$B\ho_aa3.done" `
    --same-shape-rows "$B\same_shape_a1\ed9_heldout_same_shape.jsonl" --same-shape-step-done "$B\same_shape.done" `
    --out "$O\ho_k_selection.json" *> "$O\r4.console.txt"
$code = $LASTEXITCODE
Pop-Location
$status = '?'
try { $status = (Get-Content "$O\ho_k_selection.json" -Raw | ConvertFrom-Json).status } catch { }
Write-Host ("R4 exit={0} status={1} start={2} end={3}" -f $code, $status, $t0, (Get-Date -Format s))
