#Requires -Version 7.2
# 436.8 R3f Chrono judgement, path 1 (python-expert, 2026-11-16; DRAFT, not run). Copy of the unrun R3e draft
# run_path1_r3e.ps1, itself a copy of run_path1_r3d.ps1 (judge_0220671), with the changes rules rev24 R24-3 and
# rev25 R25-3 allow: (1) the output folder is judge_<R3f short hash>; (2) the reused inputs stay in the R3c folder
# (runner_judge\, t45_C5.json, R3c judge_C5.json, run_path1_r3c.ps1); (3) R3c and R3d before / after checks (each
# SHA256SUMS.txt file sha256 and every entry; nothing is written there; a failure ends the script with exit 4);
# (4) the new steps the rev24 tools need (R24-2): --runner-judge-dir for the row judge (CD-3 window end difference),
# the C-4 record bundle (CD-9) and --rows-judge for C-8 (CD-8 values); (5) the K-10 comparison against R3d with the
# CD-10 / CD-7 keys left out and the pre-registered allowed keys (compare_r3d.py, allowed_keys_path1.md);
# (6, rev25 R25-3) the run checkout check: `git rev-parse HEAD` must be the full R3f hash, else S-12 and exit 2;
# (7, rev25 R25-3) a C-1 / C-2 / C-3 bundle or row grade unlike R3d ends the compare stage with exit 3.
# Run commit R2 = b9f5707 (every --git-at-start). Path 2 outputs are not read. A stop (R19-5 t_lift, R21-1, R22-1,
# R23-1, CD-3 window end, CD-4 P3-6 limit, CD-7, CD-11, K-10 difference) ends the sequence: run stage by stage and
# stop on the first one.
# Before the first run: set $R3fShort / $R3fFull, copy view_check.py, td_basis.py, bundle_summary.py and
# sums_check.py from the R3d folder and compare_r3d.py / allowed_keys_path1.md into the R3f folder.
# Run:  pwsh -NoProfile -File <this file> -Stage <name>|all
param([string]$Stage = 'all')
$ErrorActionPreference = 'Continue'
$PSNativeCommandUseErrorActionPreference = $false
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
Remove-Item Env:R4368_OC5_STATE -ErrorAction SilentlyContinue

$Root = 'C:\workspace\outrigger_control'
$Py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
$R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$V = Join-Path $Root '06_analysis\02_control\verif_matrix\v5_resume_4368'
$R3fShort = '8a0c843'   # change (1): the R3f merge commit short hash, filled in by the main session
$R3fFull = '8a0c8432d23c9db0916bf6f9cb9139466bd32551'     # change (6): the R3f merge commit full hash
if ($R3fShort -like '<*' -or $R3fFull -like '<*') { Write-Output 'set $R3fShort and $R3fFull first'; exit 2 }
$Head = (& git -C $Root rev-parse HEAD).Trim()
if ($Head -ne $R3fFull -or -not $R3fFull.StartsWith($R3fShort)) {   # change (6): rev25 R25-3 checkout check
    Write-Output "S-12: checkout HEAD $Head is not R3f $R3fFull (rules rev25 R25-3)"
    exit 2
}
$J = Join-Path $V "judge_$R3fShort\chrono_path1"
$R3cJ = Join-Path $V 'judge_f9bc3c7\chrono_path1'   # change (2): R3c folder, read only
$R3dJ = Join-Path $V 'judge_0220671\chrono_path1'   # change (3): R3d folder, read only (comparison basis)
$SumsSha = @{ $R3cJ = '12f1f5b4e437f7f552410fc52089cd287df323d437c3adbbdb11a5b18cb8d10c'
              $R3dJ = '3a1b8a7a69540927bb5be00ec014b9a860bcbe1c19fd97c22af85b1606f41346' }   # rev24 R24-3
$R3J = Join-Path $V 'judge_576eb87\chrono_path1'
$View = Join-Path $R3J 'chrono_view'
$RJ = Join-Path $R3cJ 'runner_judge'               # change (2): reused runner judge outputs
$T45Out = Join-Path $R3cJ 't45_C5.json'           # change (2): reused t45 output
$S9 = Join-Path $Root '07_results\S9'
$Rows = Join-Path $Root '04_scripts\02_chrono\v5_resume_4368_chrono_rows.py'
$Judge = Join-Path $Root '04_scripts\02_chrono\chrono_rows_judge_4368.py'
$Grade = Join-Path $Root '04_scripts\02_chrono\chrono_bundle_grade_4368.py'
$P1 = Join-Path $Root '06_analysis\02_control\verif_matrix\scripts\resume4368_judge.py'
$T45 = Join-Path $Root '04_scripts\04_hydraulic\coupled\chrono_t45_replay.py'

$self = [System.Diagnostics.Process]::GetCurrentProcess()
$self.ProcessorAffinity = [IntPtr][long]0xFF   # P cores 0-7 (caller note)
Set-Location $Root
New-Item -ItemType Directory -Force -Path $J | Out-Null
$CodesFile = Join-Path $J 'exit_codes.json'
$Codes = if (Test-Path $CodesFile) { Get-Content $CodesFile -Raw | ConvertFrom-Json -AsHashtable } else { [ordered]@{} }

function Invoke-Step([string]$Id, [string[]]$Arguments, [string]$Exe = $Py) {
    $log = Join-Path $J "$Id.stdout.txt"
    & $Exe @Arguments 2>&1 | ForEach-Object { "$_" } | Set-Content -Path $log -Encoding utf8
    $Codes[$Id] = $LASTEXITCODE
    $Codes | ConvertTo-Json | Set-Content -Path $CodesFile -Encoding utf8
    Write-Output "[$Id] exit $LASTEXITCODE"
}
function Batch([string]$Name) { Join-Path $S9 $Name }

$Batches = [ordered]@{
    C1       = @('batch_V5-RESUME-K1-C1_20261114_110925')
    C2       = @('batch_V5-RESUME-K1-C2_20261114_222633', 'batch_V5-RESUME-K1-C2_20261114_230123')
    C3       = @('batch_V5-RESUME-K1-C3_20261114_010541')
    C4       = @('batch_V5-RESUME-K1-C4_20261113_222912')
    C5       = @('batch_V5-RESUME-K1-C5_20261114_032426', 'batch_V5-RESUME-K1-C5_20261114_113720',
                 'batch_V5-RESUME-K1-C5_20261114_131025')
    C6C7     = @('batch_V5-RESUME-K1-C6C7_20261113_215638')
    OC5PROBE = @('batch_V5-RESUME-K1-OC5PROBE_20261113_215123')
    OC5      = @('batch_V5-RESUME-K1-OC5_20261114_210626')
}
$T45Cases = @('K0V_top_fup3.5_Fs0', 'K0_top_fup3.2_Fs0', 'K0V_top_roll5.5_Fs0', 'K0_top_fdown3.2_Fs0',
    'K0V_top_fdown3.5_Fs0', 'E_G4_Fs8', 'K0_top_rpBop_Fs0', 'E_RE1bF_Fs0', 'E_RE1bF_Fs8', 'K8_top_rpB_Fs8',
    'S_top_fdown3.5_wika_Fs8', 'K8_top_fdown3.5_Fs8', 'K0V_top_fup3.5_Fs0_LS1', 'E_G4_Fs8_LS1',
    'E_RE1bF_Fs8_LS1', 'K0V_top_fup3.5_Fs0_LS4', 'E_G4_Fs8_LS4', 'E_RE1bF_Fs8_LS4')

function Grade-Bundle([string]$Bundle, [string]$Key, [string[]]$Extra) {
    $arguments = @('-I', '-B', '-X', 'utf8', $Grade, 'grade', '--bundle', $Bundle, '--git-at-start', $R2,
                   '--out', (Join-Path $J "bundle_$Key.json"))
    foreach ($b in $Batches[$Key]) { $arguments += @('--batch', (Batch $b)) }
    Invoke-Step "bundle_$Key" ($arguments + $Extra)
}

# change (3): the R3c and R3d SHA256SUMS.txt files (sha256 of the file, then every entry) before the run and again
# in the *_check_after stage; a difference is S-11 and ends the script with exit 4 (rev25 R25-3: an exit code, not
# only the log)
function Check-Sums([string]$Folder, [string]$Id) {
    $sums = (Get-FileHash -Algorithm SHA256 (Join-Path $Folder 'SHA256SUMS.txt')).Hash.ToLower()
    if ($sums -ne $SumsSha[$Folder]) { Write-Output "S-11: $Folder SHA256SUMS.txt sha256 $sums (rev24 R24-3)"; exit 4 }
    Invoke-Step $Id @('-I', '-B', (Join-Path $J 'sums_check.py'), $Folder, (Join-Path $J "$Id.json"))
    if ($Codes[$Id] -ne 0) { Write-Output "S-11: $Id found a changed or missing file (rev24 R24-3)"; exit 4 }
}
if ($Stage -in 'all', 'r3c_check_before') {
    Check-Sums $R3cJ 'r3c_check_before'
    Check-Sums $R3dJ 'r3d_check_before'
}
if ($Stage -in 'all', 'seals_view') {
    Invoke-Step 'seals_rows_judge' @('-I', '-B', '-X', 'utf8', $Judge, 'seals')
    Invoke-Step 'seals_bundle_grade' @('-I', '-B', '-X', 'utf8', $Grade, 'seals')
    Invoke-Step 'view_check' @('-I', '-B', (Join-Path $J 'view_check.py'), $View, (Join-Path $J 'view_check.json'))
}
if ($Stage -in 'all', 'rows_judge') {   # the row-judge re-run with the R3f tool; change (4): CD-3 window record
    foreach ($name in $Batches.Keys) {
        $arguments = @('-I', '-B', '-X', 'utf8', $Judge, 'judge', '--git-at-start', $R2,
                       '--out', (Join-Path $J "judge_$name.json"), '--runner-judge-dir', $RJ)
        foreach ($b in $Batches[$name]) { $arguments += @('--batch', (Batch $b)) }
        Invoke-Step "judge_$name" $arguments
    }
}
foreach ($key in 'C1', 'C2', 'C5') {
    if ($Stage -eq "runner_$key") {   # change (2): reused, never re-run (it would write into the R3c folder)
        throw "runner_$key is reused from $RJ (rev22 R22-3), not re-run"
    }
}
if ($Stage -in 'all', 'grade_C1') {
    Grade-Bundle 'C-1' 'C1' @('--rows-judge', (Join-Path $J 'judge_C1.json'), '--runner-judge-dir', $RJ)
}
if ($Stage -in 'all', 'grade_C2C3') {
    Grade-Bundle 'C-2' 'C2' @('--rows-judge', (Join-Path $J 'judge_C2.json'), '--runner-judge-dir', $RJ)
    Grade-Bundle 'C-3' 'C3' @('--rows-judge', (Join-Path $J 'judge_C3.json'), '--runner-judge-dir', $RJ)
}
if ($Stage -eq 't45') {   # change (2): reused, never re-run
    throw "t45 is reused from $T45Out (rev22 R22-3), not re-run"
}
if ($Stage -in 'all', 'grade_C5') {   # change (3): the R22-1 pairing inputs (R3c judge_C5.json, R3c $T45Cases)
    Grade-Bundle 'C-5' 'C5' @('--rows-judge', (Join-Path $J 'judge_C5.json'), '--runner-judge-dir', $RJ,
        '--t45', $T45Out, '--t45-reference-judge', (Join-Path $R3cJ 'judge_C5.json'),
        '--t45-cases-script', (Join-Path $R3cJ 'run_path1_r3c.ps1'))
}
if ($Stage -in 'all', 'records') {
    Grade-Bundle 'C-6C7' 'C6C7' @()
    $oc5 = Batch $Batches['OC5'][0]
    foreach ($pair in @(@('C-8a', 'OC5_mixed_rigid_J1FR_Kc3_VB_top'), @('C-8b', 'OC5_mixed_rigid_J1FR_Kc1_V0_top'))) {
        Invoke-Step "fmin_$($pair[0])" @('-I', '-B', '-X', 'utf8', $P1, 'fmin-time', '--case', (Join-Path $oc5 $pair[1]),
            '--out', (Join-Path $J "fmin_$($pair[0]).json"))
        Invoke-Step "oc5_$($pair[0])" @('-I', '-B', '-X', 'utf8', $P1, 'oc5', '--result',
            (Join-Path $oc5 "$($pair[1])\result.json"), '--out', (Join-Path $J "oc5_$($pair[0]).json"))
    }
    Grade-Bundle 'C-8' 'OC5' @('--oc5', (Join-Path $J 'oc5_C-8a.json'), '--oc5', (Join-Path $J 'oc5_C-8b.json'),
        '--fmin-time', (Join-Path $J 'fmin_C-8a.json'), '--fmin-time', (Join-Path $J 'fmin_C-8b.json'),
        '--rows-judge', (Join-Path $J 'judge_OC5.json'))   # change (4): CD-8 P3 record values
    Grade-Bundle 'C-4' 'C4' @('--rows-judge', (Join-Path $J 'judge_C4.json'))   # change (4): CD-9 record bundle
}
if ($Stage -in 'all', 'compare') {   # change (5): judge C-1 .. C-8 and every R3d bundle output against R3d (K-10)
    Invoke-Step 'compare_r3d' @('-I', '-B', (Join-Path $J 'compare_r3d.py'), $R3dJ, $J, (Join-Path $J 'compare_r3d.json'))
    # change (7), rev25 R25-3: C-1 .. C-3 bundle / row grade differences taken apart; any -> exit 3 at this stage
    $cmp = Get-Content (Join-Path $J 'compare_r3d.json') -Raw | ConvertFrom-Json -AsHashtable
    $grades = foreach ($b in 'C1', 'C2', 'C3') { foreach ($g in $cmp['bundle'][$b]['grade_differences']) { "${b}: $g" } }
    $grades | Set-Content -Path (Join-Path $J 'grade_differences_C1_C3.txt') -Encoding utf8
    if (@($grades).Count -gt 0) { Write-Output "C-1 .. C-3 grade differences: $(@($grades).Count) (stop and ask)"; exit 3 }
}
if ($Stage -in 'all', 'k1view') {
    $Chrono = @(
        (Join-Path $View 'batch_V5-RESUME-K1-C1_20261114_110925'),
        (Join-Path $View 'batch_V5-RESUME-K1-C2_20261114_222633'),
        (Batch 'batch_V5-RESUME-K1-C2_20261114_230123'), (Batch 'batch_V5-RESUME-K1-C3_20261114_010541'),
        (Batch 'batch_V5-RESUME-K1-C4_20261113_222912'), (Batch 'batch_V5-RESUME-K1-C5_20261114_032426'),
        (Join-Path $View 'batch_V5-RESUME-K1-C5_20261114_113720'),
        (Batch 'batch_V5-RESUME-K1-C5_20261114_131025'), (Batch 'batch_V5-RESUME-K1-C6C7_20261113_215638'),
        (Batch 'batch_V5-RESUME-K1-OC5PROBE_20261113_215123'), (Batch 'batch_V5-RESUME-K1-OC5_20261114_210626'))
    Invoke-Step 'k1_class_view' (@('-I', '-B', '-X', 'utf8', $P1, 'k1-class', '--chrono') + $Chrono +
        @('--out', (Join-Path $J 'k1_classification_7_2_view.json')))
    Invoke-Step 'record_check_view' (@('-I', '-B', '-X', 'utf8', $P1, 'record-check', '--chrono') + $Chrono +
        @('--out', (Join-Path $J 'record_check_chrono_view.json')))
}
if ($Stage -in 'all', 'r3c_check_after') {   # change (3): the R3c and R3d folders unchanged after the run
    Check-Sums $R3cJ 'r3c_check_after'
    Check-Sums $R3dJ 'r3d_check_after'
}
Write-Output "stage $Stage done"
