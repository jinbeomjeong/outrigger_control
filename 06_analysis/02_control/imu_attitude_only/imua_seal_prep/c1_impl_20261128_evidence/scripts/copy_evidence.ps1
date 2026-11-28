# Copy the C-1 evidence (scripts, logs, A-type case records) from the scratchpad to the project folder.
$ErrorActionPreference = 'Stop'
$sp = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\cad-imua-c1'
$ev = 'C:\workspace\outrigger_control\06_analysis\02_control\imu_attitude_only\imua_seal_prep\c1_impl_20261128_evidence'
New-Item -ItemType Directory -Force "$ev\scripts", "$ev\runs", "$ev\tests" | Out-Null
foreach ($f in 'l2b_row.py', 'compare.py', 'check_imua.py', 'replay_control.py', 'gd_summary.py', 'final_runs.ps1',
               'final_checks.ps1', 'regress.ps1', 'new_findings.py', 'eol.py', 'skips.py', 'show_vol.py',
               'copy_evidence.ps1', 'digest_checks.py', 'c5_list.py', 'row_argv.py', 'grades.py') {
    Copy-Item "$sp\$f" "$ev\scripts\$f"
}
foreach ($f in 'regress_c1.log', 'regress_files.txt', 'junit_c1.xml') { Copy-Item "$sp\$f" "$ev\tests\$f" }
Copy-Item "$sp\final\rc.txt", "$sp\final\pids.txt" "$ev\runs\"
foreach ($n in 'l2b_v0', 'l2b_vb', 'scm_vb', 'imua_l2b_vb20', 'imua_scm_vb', 'gd_v0_full') {
    $dst = "$ev\runs\$n"
    New-Item -ItemType Directory -Force $dst | Out-Null
    Copy-Item "$sp\final\$n.log", "$sp\final\$n.err" $dst
    foreach ($f in 'result.json', 'driver.json', 'controller_events.json', 'imua_attitude.npz') {
        if (Test-Path "$sp\final\$n\$f") { Copy-Item "$sp\final\$n\$f" "$dst\$f" }
    }
}
Get-ChildItem $ev -Recurse -File | Measure-Object -Property Length -Sum | ForEach-Object { "files $($_.Count) bytes $($_.Sum)" }
