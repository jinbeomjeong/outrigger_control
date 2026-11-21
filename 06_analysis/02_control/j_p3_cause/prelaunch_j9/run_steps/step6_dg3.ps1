#Requires -Version 7
# Step (6) T-JR-12 (13.9; 4a-3 4; 4a-4 5, 6; 4a-5 3): the Dg-3 135 keys of the stored H-6 under
# VBH (--workers 4, 0x00FF), VBJ (--workers 4, 0xFF00) and VBJ0 (--workers 12, 0x0FFF0000, E
# cores) at once -> dg3-judge x 3 with the P-1a L1 extract -> t12 --bundle VBH, --bundle VBJ.
# Needs step 1 (self check passed, its P-1 output list committed) and step 2 (4a-5 5.1).
# A LockWindowMismatchError line ends t12 with exit 1 (the T-JR-14 failure, re-audit N-1).
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'dg3' $Attempt @('p1', 'dry')
$P1Folder = Get-StepFolder 'p1'
Assert-P1Outputs $P1Folder  # re-audit N-5: the committed P-1 list = bj.json = the files
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
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = "$Folder\${Setting}_t4h"
        R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    $Runs += Start-Run -Label "dg3_$Setting" -MaskHex $MaskHex -WrapOutput $Out -Environment $Environment `
        -TaskType 'jp3_dg3_r79' -Workers $Workers -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2,L3', '--keys-file', $H6, '--workers', "$Workers", '--affinity', $MaskHex)
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

$VbhCode = Invoke-Tool 't12_VBH' @($Tjr, 't12', '--bundle', 'VBH', '--base', $H6, '--base-judge', $BaseJudge,
    '--base-judge-sha256', $BaseJudgeSha, '--new', "$Folder\dg3_VBH.json",
    '--new-judge', "$Folder\judge\dg3_VBH_judge.json", '--new-judge-sha256', $JudgeSha['VBH'],
    '--out', "$Folder\judge\t12_VBH.json")
$VbjCode = Invoke-Tool 't12_VBJ' @($Tjr, 't12', '--bundle', 'VBJ', '--base', "$Folder\dg3_VBJ0.json",
    '--base-judge', "$Folder\judge\dg3_VBJ0_judge.json", '--base-judge-sha256', $JudgeSha['VBJ0'],
    '--new', "$Folder\dg3_VBJ.json", '--new-judge', "$Folder\judge\dg3_VBJ_judge.json",
    '--new-judge-sha256', $JudgeSha['VBJ'], '--out', "$Folder\judge\t12_VBJ.json")
$StepCode = Get-StepCode @($VbhCode, $VbjCode)  # re-audit N-2: a 1 makes the step 1
if ($StepCode -ne 0) { Stop-Step $StepCode "t12 VBH exit $VbhCode, VBJ exit $VbjCode" }

Complete-Step
