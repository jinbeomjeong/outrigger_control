#Requires -Version 7
# Step (1) P-1 (spec v5 8 4.(1); 4a-4 6, erratum 1 R-2; stored data only): base-judge -> R-2
# record -> t12-selfcheck, single, mask 0xFFFF; the P-1 output list at its end (the main session
# commits it before step 6). Edition 5 changes the simulation code by design: no 4a-7 2.2 path
# check and no fa997f4c match (erratum 2 2-4); instead git diff --stat 78fd5d2d..run commit
# into the record, and the P-1 outputs against 78fd5d2d's (4a-6 4 row (1): the sha256 of the
# judge file and its L1 extract, the base-judge-compare and t12-selfcheck codes; P-1 reads
# stored data only, so they are the same - a difference stops; the import closure of the
# judge code picks the sha or the sorted-content comparison, erratum 2 2-4).
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'p1' $Attempt @()
Write-DiffStat
$JudgeFile = "$Folder\h6_base_judge.json"
$BaseReport = "$Folder\judge\bj.json"
$H6 = Get-FixedPath 'H6_SHA256'

$Run = Start-Run -Label 'base_judge' -MaskHex '0xFFFF' -WrapOutput $JudgeFile -TaskType 'jp3_base_judge' -Workers 1 `
    -Arguments @("$Coupled/jp3_tjr_judge.py", 'base-judge', '--h6', $H6, '--noise', (Get-FixedPath 'NOISE_VB_SHA256'),
        '--judge-out', $JudgeFile, '--out', $BaseReport)
Wait-Runs @($Run)
Invoke-IdentityCheck
$JudgeSha = Read-ReportField $BaseReport 'judge_sha256'

Invoke-Judge 'base_judge_compare' @("$Coupled/jp3_tjr_judge.py", 'base-judge-compare', '--h6', $H6,
    '--new-judge', $JudgeFile, '--new-judge-sha256', $JudgeSha,
    '--stored-judge', (Get-FixedPath 'STORED_H6_R79_JUDGE_SHA256'),
    '--stored-h6-judge', (Get-FixedPath 'STORED_H6_JUDGE_SHA256'),
    '--new-l1-reference', "$Folder\h6_base_judge_L1_reference.json",
    '--stored-l1-reference', (Get-FixedPath 'STORED_H6_L1_REFERENCE_SHA256'),
    '--out', "$Folder\judge\h6_judge_compare.json") -ContinueCodes @(0, 1) | Out-Null
Assert-RecordReport "$Folder\judge\h6_judge_compare.json"  # exit 1 is a record; defects stop (2-10)

Invoke-Judge 't12_selfcheck' @("$Coupled/jp3_tjr_judge.py", 't12-selfcheck', '--h6', $H6,
    '--judge', $JudgeFile, '--judge-sha256', $JudgeSha, '--out', "$Folder\judge\h6_selfcheck.json") | Out-Null

Write-P1Outputs $Folder
# erratum 2 2-4 / 2-7 (audit warning 4): the static import closure of the judge code (entries
# r79_sensor_judge.py, h8_noise_judge_4368.py, jp3_tjr_judge.py) against git diff
# 78fd5d2d..run commit picks the comparison; 2 / 3 stop; the path is recorded.
#   disjoint (0): item p1 - the two file sha256 and the two codes as 78fd5d2d's
#   meets (1):    item p1_content - the judge file's sorted runs / table / unmatched / errors
#                 and the L1 extract JSON as 78fd5d2d's; t12-selfcheck judged by its 4a-4 6
#                 expectation table (its exit 0 above) and base-judge-compare exit 0
$ClosureCode = Invoke-Judge 'p1_import_closure' @("$Coupled/jp3_import_closure.py", '--repo', $Worktree,
    '--entry', '04_scripts/03_control/s8/r79_sensor_judge.py',
    '--entry', "$Coupled/h8_noise_judge_4368.py", '--entry', "$Coupled/jp3_tjr_judge.py",
    '--base', $PreviousRunCommit, '--head', $RunCommit,
    '--out', "$Folder\judge\p1_import_closure.json") -ContinueCodes @(0, 1)
$MatchItem = if ($ClosureCode -eq 0) { 'p1' } else { 'p1_content' }
$StepState.Codes['p1_match_path'] = $MatchItem
if ($MatchItem -eq 'p1_content' -and $StepState.Codes['tool:base_judge_compare'] -ne 0) {
    Stop-Step 1 "erratum 2 2-4 content path: base-judge-compare exit $($StepState.Codes['tool:base_judge_compare']), 0 required"
}
Invoke-RerunMatch $MatchItem  # against 78fd5d2d ($PreviousRunsRoot, its p1.done)

Complete-Step
