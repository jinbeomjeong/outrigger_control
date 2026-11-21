#Requires -Version 7
# Step (6) T-JR-12a, a record (spec v5 6.2, 8 4.(6)): the Dg-3 135 keys of the stored H-6 under
# VBH (rev 6; --workers 4, 0x00FF), VBJ (rev 6; --workers 4, 0xFF00) and VBJ0 (--workers 12,
# 0x0FFF0000) at once -> dg3-judge x 3 with the P-1 L1 extract -> t12 --bundle VBH / VBJ (12a:
# records; their exit 1 is written down and the step goes on) -> P5-1 of the three run files
# against 78fd5d2d dg3_a1. Needs step 1 (its P-1 list committed) and step 2.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'dg3' $Attempt @('p1', 'dry')
$P1Folder = Get-StepFolder 'p1'
Assert-P1Outputs $P1Folder
$H6 = Get-FixedPath 'H6_SHA256'
$Tjr = "$Coupled/jp3_tjr_judge.py"
$BaseJudge = "$P1Folder\h6_base_judge.json"
$BaseJudgeSha = Read-ReportField "$P1Folder\judge\bj.json" 'judge_sha256'
$L1Reference = "$P1Folder\h6_base_judge_L1_reference.json"
$L1ReferenceSha = Read-ReportField "$P1Folder\judge\bj.json" 'l1_reference_sha256'
$Placement = [ordered]@{ VBH = @('0x00FF', 4); VBJ = @('0xFF00', 4); VBJ0 = @('0x0FFF0000', 12) }

$Runs = @()
foreach ($Setting in $Placement.Keys) {
    $MaskHex, $Workers = $Placement[$Setting]
    $Out = "$Folder\dg3_$Setting.json"
    $Runs += Start-Run -Label "dg3_$Setting" -MaskHex $MaskHex -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Setting}_t4h") -TaskType 'jp3_dg3_r79' -Workers $Workers `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2,L3', '--keys-file', $H6,
            '--workers', "$Workers", '--affinity', $MaskHex)
}
Wait-Runs $Runs
Invoke-IdentityCheck

$JudgeSha = @{}
foreach ($Setting in $Placement.Keys) {
    $Report = "$Folder\judge\dg3_${Setting}_judge_report.json"
    Invoke-Judge "dg3_judge_$Setting" @($Tjr, 'dg3-judge', '--setting', $Setting, '--dg3', "$Folder\dg3_$Setting.json",
        '--l1-reference', $L1Reference, '--l1-reference-sha256', $L1ReferenceSha,
        '--judge-out', "$Folder\judge\dg3_${Setting}_judge.json", '--out', $Report) | Out-Null
    $JudgeSha[$Setting] = Read-ReportField $Report 'judge_sha256'
}

# 6.2: T-JR-12a is a record (exit 1 = the 13.9 indicators moved; written down, not a stop)
Invoke-Judge 't12_VBH' @($Tjr, 't12', '--bundle', 'VBH', '--base', $H6, '--base-judge', $BaseJudge,
    '--base-judge-sha256', $BaseJudgeSha, '--new', "$Folder\dg3_VBH.json",
    '--new-judge', "$Folder\judge\dg3_VBH_judge.json", '--new-judge-sha256', $JudgeSha['VBH'],
    '--out', "$Folder\judge\t12_VBH.json") -ContinueCodes @(0, 1) | Out-Null
Invoke-Judge 't12_VBJ' @($Tjr, 't12', '--bundle', 'VBJ', '--base', "$Folder\dg3_VBJ0.json",
    '--base-judge', "$Folder\judge\dg3_VBJ0_judge.json", '--base-judge-sha256', $JudgeSha['VBJ0'],
    '--new', "$Folder\dg3_VBJ.json", '--new-judge', "$Folder\judge\dg3_VBJ_judge.json",
    '--new-judge-sha256', $JudgeSha['VBJ'], '--out', "$Folder\judge\t12_VBJ.json") -ContinueCodes @(0, 1) | Out-Null

$Previous = Get-PreviousStepFolder 'dg3'
foreach ($Setting in $Placement.Keys) {
    Invoke-P51 "dg3_$Setting" "$Previous\dg3_$Setting.json" "$Folder\dg3_$Setting.json" `
        "$Previous\${Setting}_t4h" "$Folder\${Setting}_t4h"
}

Complete-Step
