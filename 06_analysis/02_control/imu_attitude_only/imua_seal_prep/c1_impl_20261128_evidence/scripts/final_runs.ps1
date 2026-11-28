# C-1 final evidence runs at the commit (worktree v5-imua), six Chrono-dev processes in parallel.
# L2b rows self-pin to the P pool (st.run_placement); SCM rows: --threads 4, OMP_WAIT_POLICY=PASSIVE before start,
# OUTRIGGER_HULL_HOOK=off (no validated DLL in this checkout or the main checkout), P pool (run_S9 place()).
$ErrorActionPreference = 'Stop'
$sp = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\cad-imua-c1'
$wt = 'C:\workspace\outrigger_control\.claude\worktrees\v5-imua'
$py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$out = "$sp\final"
New-Item -ItemType Directory -Force $out | Out-Null
$scmBase = @('04_scripts/02_chrono/run_S9.py', 'level', '--soil', 'J1', '--pad-variant', 'dwg_rear250', '--level', 'top',
    '--fs-kN', '4', '--grid', '0.04', '--crawler-grid', '0.08', '--settle-dashpot', 'zrp', '--threads', '4',
    '--duration', '2', '--t-settle', '4', '--pressure-grade', 'normal', '--imu-grade', 'ideal', '--seed', '20261026',
    '--approved', '--flow-eta-v', '0.85', '--flow-dp-comp-bar', '10', '--flow-dp-unload-bar', '20',
    '--flow-width-bar', '1', '--flow-law', 'priority', '--valve-tau-s', '0.1', '--rod-release-force',
    '--lock-overlap-ratio', '0.02', '--lock-closing-delay-s', '0.05', '--lock-window-follows-plant',
    '--extend-start-tracked', '--out-root', $out)
$jobs = @(
    @{n = 'l2b_v0'; a = @("$sp\l2b_row.py", $wt, "$out\l2b_v0", 'K0_top_roll4.4_Fs0', 'V0', '--duration', '20',
        '--expect', 'final_C4G2_LAS_K1')},
    @{n = 'l2b_vb'; a = @("$sp\l2b_row.py", $wt, "$out\l2b_vb", 'K0_top_roll4.4_Fs0', 'VB', '--duration', '20',
        '--expect', 'final_C4G2_P3_LAS_K1')},
    @{n = 'scm_vb'; a = $scmBase + @('--expect-controller', 'final_C4G2_P3_LAS_K1', '--case', 'scm_vb')},
    @{n = 'imua_l2b_vb20'; a = @("$sp\l2b_row.py", $wt, "$out\imua_l2b_vb20", 'K0_top_roll4.4_Fs0', 'VB',
        '--duration', '20', '--expect', 'final_C4G2_P3_LAS_K1_IMUA', '--imu-model', 'inclinometer', '--imu-gains', 'v5_A')},
    @{n = 'imua_scm_vb'; a = $scmBase + @('--expect-controller', 'final_C4G2_P3_LAS_K1_IMUA', '--imu-model',
        'inclinometer', '--imu-gains', 'v5_A', '--case', 'imua_scm_vb')},
    @{n = 'gd_v0_full'; a = @("$sp\l2b_row.py", $wt, "$out\gd_v0_full", 'K0_top_roll4.4_Fs0', 'V0',
        '--expect', 'final_C4G2_LAS_K1_IMUA', '--imu-model', 'inclinometer', '--imu-gains', 'v5_A')}
)
$env:OMP_WAIT_POLICY = 'PASSIVE'
$env:OUTRIGGER_HULL_HOOK = 'off'
Set-Location $wt
$procs = foreach ($j in $jobs) {
    $p = Start-Process -FilePath $py -ArgumentList (@('-I', '-B', '-X', 'utf8') + $j.a | ForEach-Object { '"' + $_ + '"' }) `
        -RedirectStandardOutput "$out\$($j.n).log" -RedirectStandardError "$out\$($j.n).err" -NoNewWindow -PassThru
    $null = $p.Handle  # keep the handle so ExitCode is readable after the exit
    [pscustomobject]@{n = $j.n; p = $p; t0 = Get-Date}
}
$procs | ForEach-Object { "{0} pid {1}" -f $_.n, $_.p.Id } | Set-Content "$out\pids.txt"
foreach ($x in $procs) { $x.p.WaitForExit(); "{0} rc {1} wall {2:n0} s" -f $x.n, $x.p.ExitCode, ((Get-Date) - $x.t0).TotalSeconds |
    Add-Content "$out\rc.txt" }
Get-Content "$out\rc.txt"
