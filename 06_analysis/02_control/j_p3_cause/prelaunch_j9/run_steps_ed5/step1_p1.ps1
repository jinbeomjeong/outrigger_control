#Requires -Version 7
# Step (1) P-1 (spec v5 8 4.(1); 4a-4 6, erratum 1 R-2; stored data only): base-judge -> R-2
# record -> t12-selfcheck, single, mask 0xFFFF; the P-1 output list at its end (the main session
# commits it before step 6). Edition 5 changes the simulation code by design: no 4a-7 2.2 path
# check and no fa997f4c rerun match (P5-1 compares the rows of steps 3 .. 6 with 78fd5d2d).
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'p1' $Attempt @()
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

Invoke-Judge 't12_selfcheck' @("$Coupled/jp3_tjr_judge.py", 't12-selfcheck', '--h6', $H6,
    '--judge', $JudgeFile, '--judge-sha256', $JudgeSha, '--out', "$Folder\judge\h6_selfcheck.json") | Out-Null

Write-P1Outputs $Folder
Complete-Step
