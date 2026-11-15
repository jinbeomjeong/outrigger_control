#Requires -Version 7.2
# 436.8 R3b Chrono judgement, path 1 (python-expert, 2026-11-15). Tool commit R3b = 062e051 (main checkout HEAD),
# run commit R2 = b9f5707 (every --git-at-start). Rules: rev18 R18-2 / R18-2a / R18-4, rev19 R19-1 .. R19-6,
# rev20 R20-2. Path 2 outputs are not read. The stages run in this order; a rev19 R19-5 t_lift stop in a bundle
# grade ends the sequence (caller note, user decision 67).
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
$J = Join-Path $V 'judge_f9bc3c7\chrono_path1'
$R3J = Join-Path $V 'judge_576eb87\chrono_path1'
$View = Join-Path $R3J 'chrono_view'
$RJ = Join-Path $J 'runner_judge'
$S9 = Join-Path $Root '07_results\S9'
$Rows = Join-Path $Root '04_scripts\02_chrono\v5_resume_4368_chrono_rows.py'
$Judge = Join-Path $Root '04_scripts\02_chrono\chrono_rows_judge_4368.py'
$Grade = Join-Path $Root '04_scripts\02_chrono\chrono_bundle_grade_4368.py'
$P1 = Join-Path $Root '06_analysis\02_control\verif_matrix\scripts\resume4368_judge.py'
$T45 = Join-Path $Root '04_scripts\04_hydraulic\coupled\chrono_t45_replay.py'

$self = [System.Diagnostics.Process]::GetCurrentProcess()
$self.ProcessorAffinity = [IntPtr][long]0xFF   # P cores 0-7 (caller note)
Set-Location $Root
New-Item -ItemType Directory -Force -Path $J, $RJ | Out-Null
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

if ($Stage -in 'all', 'seals_view') {
    Invoke-Step 'seals_rows_judge' @('-I', '-B', '-X', 'utf8', $Judge, 'seals')
    Invoke-Step 'seals_bundle_grade' @('-I', '-B', '-X', 'utf8', $Grade, 'seals')
    Invoke-Step 'view_check' @('-I', '-B', (Join-Path $J 'view_check.py'), $View, (Join-Path $J 'view_check.json'))
}
if ($Stage -in 'all', 'rows_judge') {
    foreach ($name in $Batches.Keys) {
        $arguments = @('-I', '-B', '-X', 'utf8', $Judge, 'judge', '--git-at-start', $R2,
                       '--out', (Join-Path $J "judge_$name.json"))
        foreach ($b in $Batches[$name]) { $arguments += @('--batch', (Batch $b)) }
        Invoke-Step "judge_$name" $arguments
    }
}
foreach ($key in 'C1', 'C2', 'C5') {
    if ($Stage -in 'all', "runner_$key") {
        Invoke-Step "runner_$key" @('-I', '-B', (Join-Path $J 'runner_judges.py'), $Py, $Root,
            (Join-Path $J "judge_$key.json"), $key, $RJ)
    }
}
if ($Stage -in 'all', 'grade_C1') {
    Grade-Bundle 'C-1' 'C1' @('--rows-judge', (Join-Path $J 'judge_C1.json'), '--runner-judge-dir', $RJ)
}
if ($Stage -in 'all', 'grade_C2C3') {
    Grade-Bundle 'C-2' 'C2' @('--rows-judge', (Join-Path $J 'judge_C2.json'), '--runner-judge-dir', $RJ)
    Grade-Bundle 'C-3' 'C3' @('--rows-judge', (Join-Path $J 'judge_C3.json'), '--runner-judge-dir', $RJ)
}
if ($Stage -in 'all', 't45') {
    $judgeC5 = Get-Content (Join-Path $J 'judge_C5.json') -Raw | ConvertFrom-Json
    $folders = @($judgeC5.rows | Where-Object { $_.case -in $T45Cases } | ForEach-Object { $_.dir })
    Invoke-Step 't45_C5' (@('run', '-n', 'dynamics-dev', 'python', '-I', '-B', $T45,
        (Join-Path $J 't45_C5.json')) + $folders + @('--t5')) 'conda'
}
if ($Stage -in 'all', 'grade_C5') {
    Grade-Bundle 'C-5' 'C5' @('--rows-judge', (Join-Path $J 'judge_C5.json'), '--runner-judge-dir', $RJ,
        '--t45', (Join-Path $J 't45_C5.json'))
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
        '--fmin-time', (Join-Path $J 'fmin_C-8a.json'), '--fmin-time', (Join-Path $J 'fmin_C-8b.json'))
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
if ($Stage -in 'all', 'compare') {
    Invoke-Step 'compare_r3' @('-I', '-B', (Join-Path $J 'compare_r3.py'), $R3J, $J, (Join-Path $J 'compare_r3.json'))
}
Write-Output "stage $Stage done"
