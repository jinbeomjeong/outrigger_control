#Requires -Version 7
# Step (8) j9_main (spec v5 6.5, 8 5; erratum 2 2-6 10, 2-7.1): the H-10 main part only (user
# decision 2026-11-22) - run_v5 batch j9_main (required rows x VBJ, LSJ1 .. LSJ4, regression
# rows x VBJ; ③ rev 6, tag base final_C4G2_P3W) at the run commit.
#   preconditions (2-6 10): steps (1) .. (7) done (p1, dry, fpath, cases, casef, t8, dg3,
#     12b_vbk, records) and dg3.done; the 12b judge file of 12b_vbk.done with its sha256,
#     status pass and exit 0 (2-9.6), and with erratum 8 8-10 its ready_rule: verdict pass
#     and allow_k = the 8-2 value of blocks_used (a missing block or key is no pass);
#     T-CK / DROPOUT are not a precondition (2-9.5)
#   erratum 8 8-9 (f): the script of the tool commit (Initialize-E8Step), the runs at the run
#     commit in ed5-run5, the judge commands (v0-sample, the L1 input guard, judge) in the
#     tool checkout (the same blobs as the run commit's)
#   1. the V0 sample (2-7.1): run_v5 j9_v0_sample on the fixed V0 sample key file, the identity
#      check of the folder so far (re-audit warning 4: Invoke-IdentityCheckPart v0_sample), then
#      jp3_j9main_judge.py v0-sample against the stored V0 lines (v5/main.jsonl, fixed sha):
#      a differing hash stops
#   2. run_v5 j9_main (the placement comes from compute-scheduler-expert: -MaskHex, -Workers)
#   3. the identity check of the folder
#   4. Assert-NoL1Inputs on every judge input (the j9_main rows, the V0 reference)
#   5. jp3_j9main_judge.py judge (v5 criteria 12 stage 1 on path 1, VB -> VBJ, LS -> LSJ; J-P3
#      rev 6): 0 pass goes on to j9main.done; 1 failed / 2 / 3 stop (2-7.1 stop conditions)
# Not here (2-7.1): the other H bundles and the rest of H-10 (436.9 main run), P5-1 (no 78fd5d2d
# pair). Run cost (erratum 2 2-7.1, assumption): the 436.8 R2 H-10 main share 6,036 s at 8 E
# threads x 1.25 (③ rev 6, edition 4a 7) = about 7,545 s (2.1 h); about 2,360 s (0.7 h) on
# P 8 + E 12; the V0 sample about 2 min (2-9.1). Batch table, reservation and monitoring by the
# main session.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers,
    [string]$SampleMaskHex = '', [int]$SampleWorkers = 0)
. "$PSScriptRoot\common_ed5.ps1"

$Required = @('p1', 'dry', 'fpath', 'cases', 'casef', 't8', 'dg3', '12b_vbk', 'records')
# (the record bundles T-CK / DROPOUT are no precondition, erratum 2 2-9.5)
$Folder = Initialize-E8Step 'j9main' $Attempt $Required

# erratum 2 2-9.6: the 12b judge file the 12b_vbk.done marker names - its sha256 the marker's,
# status pass, exit 0 (else j9_main does not start)
$MarkerCodes = (Get-Content -Raw -LiteralPath "$RunsRoot\12b_vbk.done" | ConvertFrom-Json).codes
$FileProperty = $MarkerCodes.PSObject.Properties['judge_file']
$ShaProperty = $MarkerCodes.PSObject.Properties['judge_sha256']
if (-not $FileProperty -or -not $ShaProperty) { Stop-Step 2 '12b_vbk.done names no judge file / sha256' }
$JudgeFile12b = Join-Path $MainRoot ([string]$FileProperty.Value)
if (-not (Test-Path -LiteralPath $JudgeFile12b)) { Stop-Step 2 "12b judge file $JudgeFile12b missing" }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $JudgeFile12b).Hash.ToLower() -ne [string]$ShaProperty.Value) {
    Stop-Step 2 "12b judge file $JudgeFile12b is not of the marker's sha256"
}
$Judged12b = Get-Content -Raw -LiteralPath $JudgeFile12b | ConvertFrom-Json
$StatusProperty = $Judged12b.PSObject.Properties['status']
$ExitProperty = $Judged12b.PSObject.Properties['exit']
if (-not $StatusProperty -or -not $ExitProperty -or $StatusProperty.Value -ne 'pass' -or $ExitProperty.Value -ne 0) {
    Stop-Step 2 '12b judge file: status pass and exit 0 required'
}
$ReadyRuleStop = Get-E8ReadyRuleStop $JudgeFile12b  # erratum 2 2-9.6 with erratum 8 8-10 (W-5)
if ($ReadyRuleStop) { Stop-Step $ReadyRuleStop.code $ReadyRuleStop.reason }
$StepState.Codes['12b_judge_sha256'] = [string]$ShaProperty.Value
$StepState.Codes['12b_ready_rule'] = 'verdict pass, allow_k of blocks_used (erratum 8 8-10)'
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
Invoke-IdentityCheckPart 'v0_sample'
Invoke-ToolJudge 'v0_sample' @($Judge, 'v0-sample', '--sample-keys', $V0SampleKeysFile, '--sample', $Sample,
    '--v0', $V0Rows, '--v0-sha256', $V0Sha, '--out', "$Folder\judge\v0_sample.json") | Out-Null

# 2. the j9_main run
$Rows = "$Folder\j9_main.jsonl"
$RunEstimatesS['j9_main'] = 7545  # 6,036 s x 1.25 at 8 E threads (2-7.1, assumption)
$Run = Start-Run -Label 'j9_main' -MaskHex $MaskHex -TaskType 'run_v5_j9_main' -Workers $Workers `
    -Arguments @("$Coupled/run_v5.py", 'j9_main', '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

# 4. no L1 reference run among the judge inputs (erratum 2 2-1, G-1)
Assert-NoL1Inputs @($Rows, $V0Rows)

# 5. v5 criteria stage 1 (path 1) and J-P3 rev 6
Invoke-ToolJudge 'j9main_judge' @($Judge, 'judge', '--rows', $Rows, '--v0', $V0Rows, '--v0-sha256', $V0Sha,
    '--out', "$Folder\judge\j9main_judge.json") | Out-Null

Complete-Step
