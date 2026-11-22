#Requires -Version 7
# Step (8) j9_main (spec v5 6.5, 8 5; erratum 2 2-6 10, 2-7.1): the H-10 main part only (user
# decision 2026-11-22) - run_v5 batch j9_main (required rows x VBJ, LSJ1 .. LSJ4, regression
# rows x VBJ; ③ rev 6, tag base final_C4G2_P3W) at the run commit.
#   preconditions (2-6 10): steps (1) .. (7) done (p1, dry, fpath, cases, casef, t8, dg3,
#     12b_vbk, records; 12b_vbk.done exists only after a 12b judge exit 0 = pass) and dg3.done
#   1. the V0 sample (2-7.1): run_v5 j9_v0_sample on the fixed V0 sample key file, then
#      jp3_j9main_judge.py v0-sample against the stored V0 lines (v5/main.jsonl, fixed sha):
#      a differing hash stops
#   2. run_v5 j9_main (the placement comes from compute-scheduler-expert: -MaskHex, -Workers)
#   3. the identity check of the folder
#   4. Assert-NoL1Inputs on every judge input (the j9_main rows, the V0 reference)
#   5. jp3_j9main_judge.py judge (v5 criteria 12 stage 1 on path 1, VB -> VBJ, LS -> LSJ; J-P3
#      rev 6): 0 pass goes on to j9main.done; 1 failed / 2 / 3 stop (2-7.1 stop conditions)
# Not here (2-7.1): the other H bundles and the rest of H-10 (436.9 main run), P5-1 (no 78fd5d2d
# pair). Run cost: about 6,779 s at 8 E threads (+25 %, assumption): batch table, reservation
# and monitoring by the main session.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers,
    [string]$SampleMaskHex = '', [int]$SampleWorkers = 0)
. "$PSScriptRoot\common_ed5.ps1"

$Required = @('p1', 'dry', 'fpath', 'cases', 'casef', 't8', 'dg3', '12b_vbk', 'records')
$Folder = Initialize-Ed5Step 'j9main' $Attempt $Required
$V0Rows = Get-FixedPath 'MAIN_JSONL_SHA256'
$V0Sha = $FixedInputs['MAIN_JSONL_SHA256'][1]
$Judge = "$Coupled/jp3_j9main_judge.py"
if (-not (Test-Path -LiteralPath $V0SampleKeysFile)) { Stop-Step 2 "$V0SampleKeysFile missing (fixed V0 sample key list)" }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $V0SampleKeysFile).Hash.ToLower() -ne (Get-ListedSha $V0SampleKeysFile)) {
    Stop-Step 2 "$V0SampleKeysFile is not the fixed list's file"
}
if (-not $SampleMaskHex) { $SampleMaskHex = $MaskHex }
if ($SampleWorkers -le 0) { $SampleWorkers = $Workers }

# 1. the V0 sample hash comparison
$Sample = "$Folder\v0_sample.jsonl"
$Run = Start-Run -Label 'j9_v0_sample' -MaskHex $SampleMaskHex -TaskType 'run_v5_j9_v0_sample' -Workers $SampleWorkers `
    -Arguments @("$Coupled/run_v5.py", 'j9_v0_sample', '--jobs-file', $V0SampleKeysFile, '--out', $Sample,
        '--workers', "$SampleWorkers", '--mask', $SampleMaskHex)
Wait-Runs @($Run)
Invoke-Judge 'v0_sample' @($Judge, 'v0-sample', '--sample-keys', $V0SampleKeysFile, '--sample', $Sample,
    '--v0', $V0Rows, '--v0-sha256', $V0Sha, '--out', "$Folder\judge\v0_sample.json") | Out-Null

# 2. the j9_main run
$Rows = "$Folder\j9_main.jsonl"
$RunEstimatesS['j9_main'] = 8474
$Run = Start-Run -Label 'j9_main' -MaskHex $MaskHex -TaskType 'run_v5_j9_main' -Workers $Workers `
    -Arguments @("$Coupled/run_v5.py", 'j9_main', '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

# 4. no L1 reference run among the judge inputs (erratum 2 2-1, G-1)
Assert-NoL1Inputs @($Rows, $V0Rows)

# 5. v5 criteria stage 1 (path 1) and J-P3 rev 6
Invoke-Judge 'j9main_judge' @($Judge, 'judge', '--rows', $Rows, '--v0', $V0Rows, '--v0-sha256', $V0Sha,
    '--out', "$Folder\judge\j9main_judge.json") | Out-Null

Complete-Step
