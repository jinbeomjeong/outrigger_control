#Requires -Version 7
# Step 12b_vbkl (spec v6 6.4): the VBKL runs of the decided blocks (the decision of
# 12b_decide_b4 when it is done, else of 12b_decide; status decided), the identity check, per
# arm grade-judge (each arm's own 12b L1 run of the l1ref step: VBKL0 -> L1_VBL0, VBKL -> L1_VBL,
# the L1 key file l1_keys_12b.txt; erratum 1 1-2; a record, exit 2 / 3 go on) and the judge (the
# decision's P-pred k_allow recomputed from the same VBKL0 lines; 6.4). Exit: the judge's code
# (0 pass, 1 failed, 2 / 3 stop). The done marker names the judge file and its sha256.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed6.ps1"

$WithB4 = Test-Path -LiteralPath "$RunsRoot\12b_decide_b4.done"
$Requires = @('l1ref', 'confirm', 'j9main', 'dg3', '12b_vbkl0', '12b_decide')
if ($WithB4) { $Requires += @('12b_vbkl0_b4', '12b_decide_b4') }
$Folder = Initialize-Ed6Step '12b_vbkl' $Attempt $Requires
$DecisionStep = if ($WithB4) { '12b_decide_b4' } else { '12b_decide' }
$Decision = "$(Get-StepFolder $DecisionStep)\decision.json"
if ($IsEd6Dry) { $Blocks = @('b1', 'b2'); $DecisionSha = 'dry' } else {
    $Document = Get-Content -Raw -LiteralPath $Decision | ConvertFrom-Json
    if ([string]$Document.status -ne 'decided') { Stop-Step 2 "decision status $($Document.status), not decided" }
    $Blocks = @($Document.blocks)
    $DecisionSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Decision).Hash.ToLower()
}
$StepState.Codes['decision_file'] = Get-RepoPath $Decision
$StepState.Codes['decision_sha256'] = $DecisionSha
$Vbkl0 = @{ b1 = (Get-StepFolder '12b_vbkl0'); b2 = (Get-StepFolder '12b_vbkl0') }
if ($Blocks -contains 'b4') { $Vbkl0['b4'] = Get-StepFolder '12b_vbkl0_b4' }

$Masks = @('0x000F', '0x00F0', '0x0F00')
$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBKL_$Block"
    $Out = "$Folder\$Label.json"
    $RunEstimatesS[$Label] = 3800  # edition 5 VBK blocks: 3,757 s at 4 workers
    $Runs += Start-Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out `
        -Environment (Get-R79Environment 'VBKL' "$Folder\${Label}_t4h" "$X11Folder\${Block}_plan.json") `
        -TaskType 'jp3_ed6_12b_vbkl' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$X11Folder\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck

$L1OfArm = @{ vbk0 = (Get-L1Run 'L1_VBL0'); vbk = (Get-L1Run 'L1_VBL') }
$GradeFiles = @{}
$GradeExits = @{}
foreach ($Arm in @('vbk0', 'vbk')) {
    $Arguments = @($Ed6Judge12b, 'grade-judge', '--arm', $Arm, '--l1-reference', $L1OfArm[$Arm],
        '--l1-reference-sha256', (Get-ListedSha $L1OfArm[$Arm]), '--l1-keys-sha256', (Get-ListedSha $L1Keys12b),
        '--judge-out', "$Folder\judge\grades_$Arm.json", '--out', "$Folder\judge\grades_${Arm}_record.json")
    foreach ($Block in $Blocks) {
        $RunFile = if ($Arm -eq 'vbk') { "$Folder\VBKL_$Block.json" } else { "$($Vbkl0[$Block])\VBKL0_$Block.json" }
        $Arguments += @('--runs', "$Block=$RunFile")
    }
    $GradeExits[$Arm] = Invoke-Judge "grade_judge_$Arm" $Arguments -ContinueCodes @(0, 2, 3)
    $GradeRecord = "$Folder\judge\grades_${Arm}_record.json"
    if ($GradeExits[$Arm] -eq 0 -and ($IsEd6Dry -or (Test-Path -LiteralPath $GradeRecord))) {
        $GradeFiles[$Arm] = @("$Folder\judge\grades_$Arm.json", (Read-ReportField $GradeRecord 'judge_sha256'))
    }
}
$Arguments = @($Ed6Judge12b, 'judge', '--selection', $X11Selection, '--selection-sha256', (Get-ListedSha $X11Selection),
    '--decision', $Decision, '--decision-sha256', $DecisionSha, '--out', "$Folder\judge\judge.json")
foreach ($Block in $Blocks) {
    $Arguments += @('--vbk0', "$Block=$($Vbkl0[$Block])\VBKL0_$Block.json", '--vbk0-t4h', "$Block=$($Vbkl0[$Block])\VBKL0_${Block}_t4h",
        '--vbk', "$Block=$Folder\VBKL_$Block.json", '--vbk-t4h', "$Block=$Folder\VBKL_${Block}_t4h")
}
foreach ($Arm in @('vbk0', 'vbk')) {
    if ($GradeFiles.ContainsKey($Arm)) {
        $Arguments += @("--$Arm-grade-judge", $GradeFiles[$Arm][0], "--$Arm-grade-judge-sha256", $GradeFiles[$Arm][1])
    } else { $Arguments += @("--$Arm-grade-judge-exit", "$($GradeExits[$Arm])") }
}
Invoke-Judge 'judge' $Arguments | Out-Null
$StepState.Codes['judge_file'] = Get-RepoPath "$Folder\judge\judge.json"
if (-not $IsEd6Dry) {
    $StepState.Codes['judge_sha256'] = (Get-FileHash -Algorithm SHA256 -LiteralPath "$Folder\judge\judge.json").Hash.ToLower()
}

Complete-Step
