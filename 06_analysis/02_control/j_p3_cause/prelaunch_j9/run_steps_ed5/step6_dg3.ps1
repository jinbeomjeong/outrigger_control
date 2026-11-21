#Requires -Version 7
# Step (6) T-JR-12a, a record (spec v5 6.2, 8 4.(6); 4a-8 4.2 .. 4.5, 5): the Dg-3 135 keys of the
# stored H-6 under VBH (rev 6; --workers 4, 0x00FF), VBJ (rev 6; --workers 4, 0xFF00) and VBJ0
# (--workers 12, 0x0FFF0000) at once, then the plant_truth L1 runs of VBJ and VBJ0 on the fixed
# 4a-8 L1 key file (l1_keys_d3c6c57e.json, 102 keys) -> the 4a-8 4.5 command hash record ->
# dg3-judge (VBH with the P-1 L1 extract; VBJ / VBJ0 each with its own L1 run) -> t12 --bundle
# VBH / VBJ (12a: records; exit 1 is written down and the step goes on) -> P5-1 of the three
# Dg-3 files against 78fd5d2d dg3_a1 -> the overlap record of the 12b and the 12a L1 references
# (erratum 2 2-1, a record). Needs steps 1 (its P-1 list committed), 2 and the l1ref step.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'dg3' $Attempt @('p1', 'dry', 'l1ref')
$P1Folder = Get-StepFolder 'p1'
Assert-P1Outputs $P1Folder
$H6 = Get-FixedPath 'H6_SHA256'
$Tjr = "$Coupled/jp3_tjr_judge.py"
$BaseJudge = "$P1Folder\h6_base_judge.json"
$BaseJudgeSha = Read-ReportField "$P1Folder\judge\bj.json" 'judge_sha256'
$P1Extract = "$P1Folder\h6_base_judge_L1_reference.json"
$P1ExtractSha = Read-ReportField "$P1Folder\judge\bj.json" 'l1_reference_sha256'
$Placement = [ordered]@{ VBH = @('0x00FF', 4); VBJ = @('0xFF00', 4); VBJ0 = @('0x0FFF0000', 12) }
$L1Placement = [ordered]@{ VBJ = '0x00FF'; VBJ0 = '0xFF00' }
$Dg3L1KeysFile = "$PrelaunchDir\l1_keys_d3c6c57e.json"
$Dg3L1KeysSha256 = 'eea8ed0d5f3aa79ecb5cf1cb892fa82f7d4bac780f8b3b17dbd069200765c6af'
# 4a-8 erratum 1 3: the fixed L1 key file of the T-JR-12a VBJ bundle (fixed list entry too)
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Dg3L1KeysFile).Hash.ToLower() -ne $Dg3L1KeysSha256) {
    Stop-Step 2 "$Dg3L1KeysFile is not the fixed 4a-8 L1 key file"
}

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
$Runs = @()
foreach ($Setting in $L1Placement.Keys) {  # 4a-8 4.3: plant_truth (R79RodModel of VBJ / VBJ0)
    $Out = "$Folder\l1_$Setting.json"
    $Runs += Start-Run -Label "l1_$Setting" -MaskHex $L1Placement[$Setting] -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Setting}_L1_t4h") -TaskType 'jp3_l1_r79' -Workers 4 `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L1', '--keys-file', $Dg3L1KeysFile,
            '--workers', '4', '--affinity', $L1Placement[$Setting])
}
Wait-Runs $Runs
Invoke-IdentityCheck
Invoke-Judge 'l1_hash_record' @($Tjr, 'l1-hash-record', '--vbj-l1', "$Folder\l1_VBJ.json",
    '--vbj0-l1', "$Folder\l1_VBJ0.json", '--out', "$Folder\judge\l1_hash_record.json") | Out-Null

$JudgeSha = @{}
foreach ($Setting in $Placement.Keys) {
    $Report = "$Folder\judge\dg3_${Setting}_judge_report.json"
    $Reference = if ($Setting -eq 'VBH') { @('--l1-reference', $P1Extract, '--l1-reference-sha256', $P1ExtractSha) } else {
        @('--l1-reference', "$Folder\l1_$Setting.json", '--l1-reference-sha256',
            (Get-FileHash -Algorithm SHA256 -LiteralPath "$Folder\l1_$Setting.json").Hash.ToLower(),
            '--l1-keys-file', $Dg3L1KeysFile)
    }
    Invoke-Judge "dg3_judge_$Setting" (@($Tjr, 'dg3-judge', '--setting', $Setting, '--dg3', "$Folder\dg3_$Setting.json") +
        $Reference + @('--judge-out', "$Folder\judge\dg3_${Setting}_judge.json", '--out', $Report)) | Out-Null
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

# erratum 2 2-1 (audit warning 5): the keys the 12b and the 12a L1 references share, same /
# differing command hash counts (a record; a differing key is published and looked into)
Invoke-Judge 'l1_overlap' @("$Coupled/jp3_12b_judge.py", 'l1-overlap',
    '--pair', "VBJ=$(Get-L1Run 'VBJ'),$Folder\l1_VBJ.json", '--pair', "VBJ0=$(Get-L1Run 'VBJ0'),$Folder\l1_VBJ0.json",
    '--out', "$Folder\judge\l1_overlap.json") | Out-Null

Complete-Step
