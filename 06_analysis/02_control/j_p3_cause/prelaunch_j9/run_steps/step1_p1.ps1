#Requires -Version 7
# Step (1) P-1 (addendum 4a-4 6, erratum 1 R-2; stored data only): base-judge -> R-2 record ->
# t12-selfcheck. Placement: single, mask 0xFFFF. Exit 0 only when the self check passes
# (4a-5 5.1: selfcheck != 0 forbids step 6). At its end it writes the P-1 output list
# (re-audit N-5); the main session commits that list (audit R-7) before step 6.
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'p1' $Attempt @()
$JudgeFile = "$Folder\h6_base_judge.json"           # its L1 extract: h6_base_judge_L1_reference.json
$BaseReport = "$Folder\judge\bj.json"
$H6 = Get-FixedPath 'H6_SHA256'

# base-judge under the identity wrapper (the P-1 creation record of 4a-5 4)
$Run = Start-Run -Label 'base_judge' -MaskHex '0xFFFF' -WrapOutput $JudgeFile -TaskType 'jp3_base_judge' -Workers 1 `
    -Arguments @("$Coupled/jp3_tjr_judge.py", 'base-judge', '--h6', $H6, '--noise', (Get-FixedPath 'NOISE_VB_SHA256'),
        '--judge-out', $JudgeFile, '--out', $BaseReport)
Wait-Runs @($Run)
Invoke-IdentityCheck
$JudgeSha = Read-ReportField $BaseReport 'judge_sha256'

# R-2 (a record: exit 1 = other grades, its cause is written down; 2 / 3 stop)
Invoke-Judge 'base_judge_compare' @("$Coupled/jp3_tjr_judge.py", 'base-judge-compare', '--h6', $H6,
    '--new-judge', $JudgeFile, '--new-judge-sha256', $JudgeSha,
    '--stored-judge', (Get-FixedPath 'STORED_H6_R79_JUDGE_SHA256'),
    '--stored-h6-judge', (Get-FixedPath 'STORED_H6_JUDGE_SHA256'),
    '--new-l1-reference', "$Folder\h6_base_judge_L1_reference.json",
    '--stored-l1-reference', (Get-FixedPath 'STORED_H6_L1_REFERENCE_SHA256'),
    '--out', "$Folder\judge\h6_judge_compare.json") -ContinueCodes @(0, 1) | Out-Null

Invoke-Judge 't12_selfcheck' @("$Coupled/jp3_tjr_judge.py", 't12-selfcheck', '--h6', $H6,
    '--judge', $JudgeFile, '--judge-sha256', $JudgeSha, '--out', "$Folder\judge\h6_selfcheck.json") | Out-Null

# re-audit N-5: the P-1 output list prelaunch_j9\P1_OUTPUTS_(run commit 8).SHA256SUMS; the main
# session commits it before step 6 (step 6 checks it is tracked and equal to bj.json)
Write-P1Outputs $Folder

Complete-Step
