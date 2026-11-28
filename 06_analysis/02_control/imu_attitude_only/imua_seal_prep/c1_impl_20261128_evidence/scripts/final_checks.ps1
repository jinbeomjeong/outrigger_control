# C-1 acceptance checks on the final runs (scratch final\), outputs into the evidence folder.
$ErrorActionPreference = 'Continue'
$sp = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\cad-imua-c1'
$wt = 'C:\workspace\outrigger_control\.claude\worktrees\v5-imua'
$ev = 'C:\workspace\outrigger_control\06_analysis\02_control\imu_attitude_only\imua_seal_prep\c1_impl_20261128_evidence'
$cd = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$dd = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$fin = "$sp\final"
New-Item -ItemType Directory -Force "$ev\checks" | Out-Null
Set-Location $wt
$log = "$ev\checks\final_checks.log"
"commit $(git rev-parse HEAD)  start $(Get-Date -Format o)" | Set-Content $log
foreach ($n in 'l2b_v0', 'l2b_vb', 'scm_vb') {
    "== bit $n" | Add-Content $log
    & $cd -I -B -X utf8 "$sp\compare.py" "$sp\base\$n" "$fin\$n" --out "$ev\checks\bit_$n.json" *>> $log
    "rc=$LASTEXITCODE" | Add-Content $log
}
foreach ($x in @(@('imua_l2b_vb20', 'final_C4G2_P3_LAS_K1_IMUA'), @('imua_scm_vb', 'final_C4G2_P3_LAS_K1_IMUA'),
                 @('gd_v0_full', 'final_C4G2_LAS_K1_IMUA'))) {
    "== meta $($x[0])" | Add-Content $log
    & $cd -I -B -X utf8 "$sp\check_imua.py" $wt "$fin\$($x[0])" $x[1] --out "$ev\checks\meta_$($x[0]).json" *> $null
    "rc=$LASTEXITCODE" | Add-Content $log
    "== expected_sensor $($x[0])" | Add-Content $log
    & $dd -I -B -X utf8 04_scripts/04_hydraulic/coupled/imua_expected_sensor.py --chrono-result "$fin\$($x[0])\result.json" `
        --out "$ev\checks\expected_sensor_$($x[0]).json" *>> $log
    "rc=$LASTEXITCODE" | Add-Content $log
}
foreach ($n in 'imua_l2b_vb20', 'gd_v0_full') {
    "== replay $n" | Add-Content $log
    & $dd -I -B -X utf8 04_scripts/04_hydraulic/coupled/chrono_t45_replay.py "$ev\checks\replay_$n.json" "$fin\$n" *>> $log
    "rc=$LASTEXITCODE" | Add-Content $log
    & $dd -I -B -X utf8 "$sp\replay_control.py" $wt "$fin\$n" "$ev\checks\replay_control_$n.json" *> $null
    "control rc=$LASTEXITCODE" | Add-Content $log
}
& $cd -I -B -X utf8 "$sp\gd_summary.py" "$fin\gd_v0_full" "$ev\checks\gd_summary.json" *> $null
"gd_summary rc=$LASTEXITCODE" | Add-Content $log
"end $(Get-Date -Format o)" | Add-Content $log
Get-Content $log
