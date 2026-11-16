param([string]$Only = '')
# 436.8 R4 harness re-judgement, path 1 (R4 common block e451f067, supplements 2..4).
# Run by the main session in the main checkout after the M4 merge (RD-1 5). It reads only and
# writes only to judge_<M4 short>/harness_path1/. The two hashes are the only placeholders:
# 932f1fb1724f074e4ee93a9c02193c7c840d13c4 (the merge commit on master) and 1ab93f0204eee35a39e84a85b2878b35310884b1 (the R4 integration merge commit).
# Nothing is judged when the head-check step does not exit 0. Path 2 blobs of RD-1 4 are compared
# by the main session with git (not here). Same step layout as the first path 1 run
# (first_judge_harness_b9f5707.ps1): every step logged into <Out>/logs/rc.tsv.
$ErrorActionPreference = 'Continue'
# CPU placement: set by the main session from the compute-scheduler-expert table (the first run
# used ProcessorAffinity 0x00FF0000 and BelowNormal).
Set-Location C:\workspace\outrigger_control
$M4 = '932f1fb1724f074e4ee93a9c02193c7c840d13c4'
$R4 = '1ab93f0204eee35a39e84a85b2878b35310884b1'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$PyDev = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$env:MKL_THREADING_LAYER = 'TBB'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONIOENCODING = 'utf-8'
foreach ($n in 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMBA_NUM_THREADS') { Set-Item "env:$n" '1' }
$R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$Base = '06_analysis/02_control/verif_matrix/v5_resume_4368'
$Out = "$Base/judge_$($M4.Substring(0, 7))/harness_path1_retry1"
$Log = "$Out/logs"; New-Item -ItemType Directory -Force $Log | Out-Null
$Rk = '06_analysis/03_hydraulic/coupled/v5/resume_k1'
$V5 = '06_analysis/03_hydraulic/coupled/v5'
$U3 = '06_analysis/02_control/v5_rerun/las_k1'
$Judge = '06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py'
$Co = '04_scripts/04_hydraulic/coupled'
$Steps = "$Base/run_b9f5707/src/csched/steps_s1/steps_h2.json"
$X = '07_results/S9/R4368X_b9f5707_20261115_013947'
$Path1Files = @(
    '04_scripts/04_hydraulic/coupled/judge_stage1_4368.py',
    '04_scripts/04_hydraulic/coupled/judge4368_common.py',
    '04_scripts/04_hydraulic/coupled/u3_judge_4368.py',
    '04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py',
    '04_scripts/04_hydraulic/coupled/h6_judge_4368.py',
    '04_scripts/04_hydraulic/coupled/README_judges_4368.md',
    '06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py',
    '05_tests/unit/test_judges_4368.py',
    '05_tests/unit/test_judges_4368_h6_h8.py',
    '05_tests/unit/test_resume4368.py',
    '05_tests/unit/test_resume4368_rev1.py',
    '05_tests/unit/test_resume4368_rev16.py', '05_tests/unit/test_resume4368_supplement4.py', '05_tests/unit/test_resume4368_supplement5.py'
)
# The first path 1 run's sidecar checker lives outside the repository (not an R4 blob); the main
# session runs it again from a preserved copy (sha256 0962f6397aaf3b16...), disclosed as outside the R4 blobs.
$FirstSidecars = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\scratchpad\main\sidecars_b9f5707.py'

function Invoke-Logged([string]$Name, [string]$Interpreter, [string[]]$Arguments, [switch]$Always) {
    # pre-run audit A-3: the gate steps (-Always) run even with -Only
    if (-not $Always -and $Only -and ($Only -split ',') -notcontains $Name) { return $null }
    $t0 = Get-Date
    & $Interpreter -I -B @Arguments > "$Log/$Name.out.txt" 2> "$Log/$Name.err.txt"
    $rc = $LASTEXITCODE
    Add-Content "$Log/rc.tsv" "$Name`t$rc`t$([math]::Round(((Get-Date) - $t0).TotalSeconds, 1))`t$($t0.ToString('MM-dd HH:mm:ss'))"
    return $rc
}

$Harness = @("$Rk/h1_d1.jsonl", "$Rk/h5_u9_v0.jsonl", "$Rk/h6_dg3_v4on.json", "$Rk/h7_dg3_off.json",
    "$Rk/h8_noise_VB.json", "$Rk/h8_noise_V0.json", "$Rk/h8_seedext_VB.json", "$Rk/h8_seedext_V0.json",
    "$Rk/h9_stage1.jsonl", "$Rk/h9_grid/grid_r67_main.json", "$Rk/h9_grid/grid_r67_top.json",
    "$Rk/h9_grid/grid_r69_bottom.json", "$Rk/h9_grid/grid_r69_top.json", "$Rk/h10_reuse_rerun.jsonl")
$Grid = @("$Rk/h9_grid/grid_r67_main.json", "$Rk/h9_grid/grid_r67_top.json",
    "$Rk/h9_grid/grid_r69_bottom.json", "$Rk/h9_grid/grid_r69_top.json")
$U3Files = @(Get-ChildItem $U3 -Filter 'u3_*.json' | Sort-Object Name | ForEach-Object { "$U3/$($_.Name)" })
$U6Files = @(Get-ChildItem $U3 -Filter 'u6_*.json' | Sort-Object Name | ForEach-Object { "$U3/$($_.Name)" })
# pre-run audit A-4 / supplement 4-4: the globs must pick exactly the 18 U-3 and 4 U-6 files
if ($U3Files.Count -ne 18 -or $U6Files.Count -ne 4) {
    throw "S-15: u3 files $($U3Files.Count) (18 expected), u6 files $($U6Files.Count) (4 expected)"
}
$All = $Harness + $U3Files + $U6Files

# pre-run audit A-4: the tracked work tree is clean at the start (and again at the end)
function Assert-CleanTree([string]$When) {
    $dirty = @(git status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) {
        throw "tracked work tree not clean at the $When (git status exit $LASTEXITCODE): $($dirty -join '; ')"
    }
}
Assert-CleanTree 'start'
Add-Content "$Log/rc.tsv" "RUNSTART`t0`t0`t$((Get-Date).ToString('MM-dd HH:mm:ss'))"

# --- 1 RD-1 5 / RD-1 4: HEAD = M4 (else S-12), path 1 allow-list blobs M4 = R4 and no
#       b9f5707..M4 change under 03_src / 02_params (else S-11); runs also with -Only (audit A-3)
$rc = Invoke-Logged 'head_check' $Py (@($Judge, 'head-check', '--expect', $M4, '--r4', $R4, '--files') +
    $Path1Files + @('--out', "$Out/head_check.json")) -Always
if ($rc -ne 0) { throw "head-check exit ${rc}: S-12 / S-11 stop, nothing judged" }

# --- 1b supplement 4-1 .. 4-4: the 43 original files, 5 key sources, 4 stored V0 grids, per-line
#        kinds and tags, S-15 counts; any finding stops before judging (S-15 / S-2 / S-3 / S-11)
$rc = Invoke-Logged 'r4_inputs' $Py @($Judge, 'r4-inputs', '--root', '.', '--out', "$Out/r4_inputs.json") -Always
if ($rc -ne 0) { throw "r4-inputs exit ${rc}: supplement 4 input stop, nothing judged" }

# --- 2 RD-5 key map and RD-13 item lists (fixed before any judgement output)
Invoke-Logged 'key_map' $Py @($Judge, 'key-map', '--out', "$Out/key_map.json") | Out-Null
Invoke-Logged 'item_list' $Py @($Judge, 'item-list', '--out-dir', "$Out/items", '--out', "$Out/item_list.json") | Out-Null

# --- 3 gates and identity (rev1 .. rev12 subcommands of the first run, new folder)
Invoke-Logged 'log_errors' $PyDev @('C:\Users\jinbeom\.claude\tools\verif\log_errors.py',
    "$Base/run_b9f5707/logs/run_harness", '--out', "$Out/log_errors_run_harness.json", '--format', 'json') | Out-Null
Invoke-Logged 'import_check' $Py @($Judge, 'import-check', '--steps', $Steps, '--out', "$Out/import_check.json") | Out-Null
Invoke-Logged 'appendix_a' $Py @($Judge, 'appendix-a', '--out', "$Out/appendix_a.json") | Out-Null
Invoke-Logged 'overlap_steps' $Py @($Judge, 'overlap', '--steps', $Steps, '--out', "$Out/overlap_steps.json") | Out-Null
# pre-run audit A-4: no silent skip of the sidecar check
$Identities = @(Get-ChildItem $Rk -Recurse -Filter '*.identity.json')
if (-not (Test-Path $FirstSidecars)) { throw "sidecars copy missing: $FirstSidecars" }
if ($Identities.Count -eq 0) { throw "no *.identity.json under ${Rk}: sidecar check would be empty" }
Invoke-Logged 'sidecars' $PyDev @($FirstSidecars, $Rk, $R2, "$Out/sidecars.json") | Out-Null
# RV1-6 family table, made anew in this run (the input of k1-class and r4-lists)
Invoke-Logged 'family_table' $Py @("$Co/resume_k1_family.py", "$Out/family_table.json") | Out-Null
Invoke-Logged 'anchor_map' $Py @($Judge, 'anchor-map', '--v5-dir', $V5, '--h1', "$Rk/h1_d1.jsonl", '--out', "$Out/anchor_map.json") | Out-Null
Invoke-Logged 'record_check' $Py (@($Judge, 'record-check', '--harness') + $All + @('--out', "$Out/record_check.json")) | Out-Null
Invoke-Logged 'k1_class' $Py (@($Judge, 'k1-class', '--harness') + $All + @('--anchor-map', "$Out/anchor_map.json",
    '--family-table', "$Out/family_table.json", '--out', "$Out/k1_class.json")) | Out-Null

# --- 4 R4: H-11 gate, C-9 .. C-11 records (before the H-3 / H-8 grades, RD-12), H-12, J_P, lists
Invoke-Logged 'h11' $Py @($Judge, 'h11', '--h11-dir', "$X/H-11", '--out', "$Out/h11.json") | Out-Null
Invoke-Logged 'x16_records' $PyDev @($Judge, 'x16-records', '--out-root', $X, '--out', "$Out/x16_records.json") | Out-Null
Invoke-Logged 'h12_t4h_replay' $Py @("$Co/t4h_replay.py", "$Out/h12_t4h_replay.json", "$X/H-12/t4h", '--check-recorded') | Out-Null
Invoke-Logged 'h12' $Py @($Judge, 'h12', '--h12-dir', "$X/H-12", '--replay', "$Out/h12_t4h_replay.json", '--out', "$Out/h12.json") | Out-Null
Invoke-Logged 'jp_reuse' $Py @($Judge, 'jp-reuse', '--root', '.', '--out', "$Out/jp_reuse.json") | Out-Null
Invoke-Logged 'r4_lists' $Py @($Judge, 'r4-lists', '--root', '.', '--family-table', "$Out/family_table.json",
    '--out', "$Out/r4_lists.json") | Out-Null

# --- 5 bundles (the regraded H-1 file is written by d1_judge_4368 in this run)
Invoke-Logged 'd1_judge' $Py @("$Co/d1_judge_4368.py", '--out', "$Out/d1_judge.json", '--h1', "$Rk/h1_d1.jsonl",
    '--regraded', "$Out/h1_d1_regraded.jsonl", '--select-out', "$Out/h2_select.json") | Out-Null
Invoke-Logged 'u3_judge_k1' $Py @("$Co/u3_judge_k1.py", 'judge', "$Out/u3_judge_k1.json", '--u3-dir', $U3,
    '--v4-dir', '06_analysis/02_control/s9') | Out-Null
Invoke-Logged 'u3_judge' $Py @("$Co/u3_judge_4368.py", '--out', "$Out/u3_judge.json", '--u3-dir', $U3,
    '--v4-dir', '06_analysis/02_control/s9', '--h1-d1', "$Rk/h1_d1.jsonl", '--g3', "$Out/h11.json",
    '--k1-report', "$Out/u3_judge_k1.json") | Out-Null
Invoke-Logged 'ind_las' $Py (@($Judge, 'ind-las', '--harness') + $U6Files + @('--out', "$Out/ind_las.json")) | Out-Null
Invoke-Logged 'u9_judge' $Py @("$Co/u9_judge_4368.py", '--out', "$Out/u9_judge.json", '--v0', "$Rk/h5_u9_v0.jsonl",
    '--h10', "$Rk/h10_reuse_rerun.jsonl", '--stored-p3-hash', "$V5/p3_hash.jsonl") | Out-Null
Invoke-Logged 'h8_noise_judge' $Py @("$Co/h8_noise_judge_4368.py", '--out', "$Out/h8_noise_judge.json",
    '--noise-vb', "$Rk/h8_noise_VB.json", '--noise-v0', "$Rk/h8_noise_V0.json", '--h6', "$Rk/h6_dg3_v4on.json",
    '--seedext-vb', "$Rk/h8_seedext_VB.json", '--seedext-v0', "$Rk/h8_seedext_V0.json",
    '--judge-dir', "$Out/h8_r79_judge", '--run-judge') | Out-Null
Invoke-Logged 'h6_judge' $Py @("$Co/h6_judge_4368.py", '--out', "$Out/h6_judge.json", '--h6', "$Rk/h6_dg3_v4on.json",
    '--l1-ref', "$Rk/h8_noise_VB.json", '--judge', "$Out/h6_r79_judge.json", '--run-judge') | Out-Null
Invoke-Logged 'dg3_hash' $Py @($Judge, 'dg3-hash', '--h6', "$Rk/h6_dg3_v4on.json", '--h7', "$Rk/h7_dg3_off.json",
    '--h8-vb', "$Rk/h8_noise_VB.json", '--seedext', "$Rk/h8_seedext_VB.json", "$Rk/h8_seedext_V0.json",
    '--noise', "$Rk/h8_noise_VB.json", "$Rk/h8_noise_V0.json", '--out', "$Out/dg3_hash.json") | Out-Null
foreach ($pair in @(@('h6', "$Rk/h6_dg3_v4on.json", "$V5/dg3/dg3_v4_on.json"),
        @('h7', "$Rk/h7_dg3_off.json", "$V5/dg3/off/dg3_off.json"),
        @('h8_noise_VB', "$Rk/h8_noise_VB.json", "$V5/noise_vb/r79_VB_L1L2L3.json"),
        @('h8_noise_V0', "$Rk/h8_noise_V0.json", "$V5/noise_v0/r79_V0_L1L2L3.json"),
        @('h8_seedext_VB', "$Rk/h8_seedext_VB.json", "$V5/seedext/r79_VB_seedext.json"),
        @('h8_seedext_V0', "$Rk/h8_seedext_V0.json", "$V5/seedext/r79_V0_seedext.json"))) {
    Invoke-Logged "keyset_$($pair[0])" $Py @($Judge, 'keyset', '--kind', 'r79', '--new', $pair[1], '--stored', $pair[2],
        '--out', "$Out/keyset_$($pair[0]).json") | Out-Null
}
foreach ($gname in 'grid_r67_main', 'grid_r67_top', 'grid_r69_bottom', 'grid_r69_top') {
    Invoke-Logged "keyset_$gname" $Py @($Judge, 'keyset', '--kind', 'grid', '--new', "$Rk/h9_grid/$gname.json",
        '--stored', "$V5/grid_vb/$gname.json", '--out', "$Out/keyset_$gname.json") | Out-Null
}
# R16-7 / supplement 2-2: --grid adds the grid J-P3 and J11 grade (new in R4)
Invoke-Logged 'stage1_judge' $Py (@("$Co/judge_stage1_4368.py", '--out', "$Out/stage1_judge.json", '--h9', "$Rk/h9_stage1.jsonl",
    '--h10', "$Rk/h10_reuse_rerun.jsonl", '--overlap-ref', "$Rk/h10_overlap_t_a.json", '--grid') + $Grid) | Out-Null
Invoke-Logged 'grid_v0_sample' $Py @($Judge, 'grid-v0-sample', '--sample-dir', "$Rk/h9_grid_v0_sample",
    '--stored-dir', '06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid', '--out', "$Out/grid_v0_sample.json") | Out-Null
# supplement 6-3: the application condition everywhere on the one 5-1 / 6-2 V0 pairing
#   (no V0 folder fixed here; the pair source comes from the R3-E1 / R4-B4 sample)
Invoke-Logged 'family_f_trigger' $Py @($Judge, 'family-f-trigger', '--grid-root', '.',
    '--out', "$Out/family_f_trigger.json") | Out-Null
# supplement 4-5 (audit B-2): family F R-1 .. R-4 on the 64 lines and their application
Invoke-Logged 'family_f' $Py @($Judge, 'family-f', '--lines', "$Rk/h9_family_F.jsonl", '--grid-root', '.',
    '--out', "$Out/family_f.json") | Out-Null
# supplements 5 / 6 (user decision 129): the 768 VB grid runs against their V0 pairs, N_raw /
# family F table / N_F and the v5 criteria H-10 grid term per application case (the judgement
# only picks); the only marker is h10_marker (the H-10 stop, supplement 6-4)
Invoke-Logged 'grid_h10' $Py @($Judge, 'grid-h10', '--root', '.', '--out', "$Out/grid_h10.json") | Out-Null
Invoke-Logged 'reagg_items' $Py @($Judge, 'reagg-items', '--out', "$Out/reagg_items.json") | Out-Null
foreach ($b in @(@('H-1', "$Rk/h1_d1.jsonl"), @('H-5', "$Rk/h5_u9_v0.jsonl"), @('H-6', "$Rk/h6_dg3_v4on.json"),
        @('H-7', "$Rk/h7_dg3_off.json"))) {
    Invoke-Logged "stroke_$($b[0])" $Py @($Judge, 'stroke-exposure', '--bundle', $b[0], '--harness', $b[1],
        '--out', "$Out/stroke_$($b[0]).json") | Out-Null
}
Invoke-Logged 'stroke_H-3' $Py (@($Judge, 'stroke-exposure', '--bundle', 'H-3', '--harness') + $U3Files + @('--out', "$Out/stroke_H-3.json")) | Out-Null
Invoke-Logged 'stroke_H-4' $Py (@($Judge, 'stroke-exposure', '--bundle', 'H-4', '--harness') + $U6Files + @('--out', "$Out/stroke_H-4.json")) | Out-Null
Invoke-Logged 'stroke_H-8' $Py @($Judge, 'stroke-exposure', '--bundle', 'H-8', '--harness', "$Rk/h8_noise_VB.json",
    "$Rk/h8_noise_V0.json", "$Rk/h8_seedext_VB.json", "$Rk/h8_seedext_V0.json", '--out', "$Out/stroke_H-8.json") | Out-Null
Invoke-Logged 'stroke_H-9' $Py (@($Judge, 'stroke-exposure', '--bundle', 'H-9', '--harness', "$Rk/h9_stage1.jsonl") + $Grid +
    @('--out', "$Out/stroke_H-9.json")) | Out-Null
Invoke-Logged 'stroke_H-10' $Py @($Judge, 'stroke-exposure', '--bundle', 'H-10', '--harness', "$Rk/h10_reuse_rerun.jsonl",
    '--out', "$Out/stroke_H-10.json") | Out-Null

# --- 6 sha256 of every output file before any comparison (RD-6)
Get-ChildItem $Out -Recurse -File | Where-Object { $_.Name -ne 'sha256_manifest.txt' -and $_.DirectoryName -notlike '*\logs' } |
    Get-FileHash -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash.ToLower())  $($_.Path.Substring((Resolve-Path $Out).Path.Length + 1))" } |
    Set-Content -Encoding utf8NoBOM "$Out/sha256_manifest.txt"
Add-Content "$Log/rc.tsv" "ALLDONE`t0`t0`t$((Get-Date).ToString('MM-dd HH:mm:ss'))"

# --- 7 pre-run audit A-3 / A-4: the work tree is still clean, and rc.tsv is a gate: any step of
#       this run (after the last RUNSTART line) with a non-zero exit fails the script
Assert-CleanTree 'end'
$rows = @(Get-Content "$Log/rc.tsv")
$start = ($rows | Select-String -Pattern '^RUNSTART' | Select-Object -Last 1).LineNumber
$failed = @($rows[$start..($rows.Count - 1)] | Where-Object { ($_ -split "`t")[1] -ne '0' })
if ($failed.Count -gt 0) {
    Write-Output "steps with a non-zero exit (findings or failures, read their reports):"
    $failed | ForEach-Object { Write-Output "  $_" }
    exit 1
}
exit 0
