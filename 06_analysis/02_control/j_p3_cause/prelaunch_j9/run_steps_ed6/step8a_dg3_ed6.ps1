#Requires -Version 7
# Step dg3 (spec v6 4 step 8, 6.5; erratum 1 1-3, Y-13): T-JR-12a VBL against VBL0 on the Dg-3
# 135 keys of the stored H-6 (VBL 0x00FF and VBL0 0xFF00, 4 workers each), then per setting
# dg3-judge with its own T-JR-12a L1 run of the l1ref step (L1a_SETTING, 4a-8 4.3 checks) and
# t12 --bundle VBL with --new-t4h / --base-t4h (6.1 identity of both sides; J-P3 judged rows 1).
# t12 is a record tool (exit 1 = 13.9 indicators moved, written down) and its report goes
# through Assert-RecordReport: J-P3 H-7 stops 1, no J-P3 judgement / a setting defect / a
# not-judgeable reason stops 2, and an H-7 leaves 'judged:t12_VBL_jp3' (erratum 2 2-4). Needs
# the j9main step.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed6.ps1"

$Folder = Initialize-Ed6Step 'dg3' $Attempt @('l1ref', 'confirm', 'j9main')
$H6 = Get-FixedPath 'H6_SHA256'
$Placement = [ordered]@{ VBL = @('0x00FF', 4); VBL0 = @('0xFF00', 4) }
$RunEstimatesS['dg3_VBL'] = 2250; $RunEstimatesS['dg3_VBL0'] = 2250
# wall [s] of the edition 5 Dg-3 runs at 4 workers (dg3_a1 VBJ 2,205 s)
$Runs = @()
foreach ($Setting in $Placement.Keys) {
    $MaskHex, $RunWorkers = $Placement[$Setting]
    $Out = "$Folder\dg3_$Setting.json"
    $Runs += Start-Run -Label "dg3_$Setting" -MaskHex $MaskHex -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Setting}_t4h") -TaskType 'jp3_ed6_dg3_r79' -Workers $RunWorkers `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2,L3', '--keys-file', $H6,
            '--workers', "$RunWorkers", '--affinity', $MaskHex)
}
Wait-Runs $Runs
Invoke-IdentityCheck

$JudgeSha = @{}
foreach ($Setting in $Placement.Keys) {
    $L1 = Get-L1Run "L1a_$Setting"
    $Report = "$Folder\judge\dg3_${Setting}_judge_report.json"
    Invoke-Judge "dg3_judge_$Setting" @($Tjr, 'dg3-judge', '--setting', $Setting, '--dg3', "$Folder\dg3_$Setting.json",
        '--l1-reference', $L1, '--l1-reference-sha256', (Get-ListedSha $L1), '--l1-keys-file', $L1Keys12a,
        '--judge-out', "$Folder\judge\dg3_${Setting}_judge.json", '--out', $Report) | Out-Null
    $JudgeSha[$Setting] = Read-ReportField $Report 'judge_sha256'
}
# erratum 2 2-4: the command hash record of the two L1a runs (a record, never a stop)
Invoke-RecordTool 'l1_hash_record' @($Tjr, 'l1-hash-record', '--bundle', 'VBL', '--vbl-l1', (Get-L1Run 'L1a_VBL'),
    '--vbl0-l1', (Get-L1Run 'L1a_VBL0'), '--out', "$Folder\judge\l1_hash_record.json") | Out-Null
Invoke-Judge 't12_VBL' @($Tjr, 't12', '--bundle', 'VBL', '--base', "$Folder\dg3_VBL0.json",
    '--base-judge', "$Folder\judge\dg3_VBL0_judge.json", '--base-judge-sha256', $JudgeSha['VBL0'],
    '--new', "$Folder\dg3_VBL.json", '--new-judge', "$Folder\judge\dg3_VBL_judge.json",
    '--new-judge-sha256', $JudgeSha['VBL'], '--new-t4h', "$Folder\VBL_t4h", '--base-t4h', "$Folder\VBL0_t4h",
    '--out', "$Folder\judge\t12_VBL.json") -ContinueCodes @(0, 1) | Out-Null
Assert-RecordReport "$Folder\judge\t12_VBL.json" -VbjJp3

Complete-Step
