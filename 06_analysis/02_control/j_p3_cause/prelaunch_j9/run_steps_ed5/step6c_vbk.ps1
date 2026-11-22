#Requires -Version 7
# Step (6c) T-JR-12b VBK and judgement (spec v5 6.3.7, 8 4.(6) 5 .. 6): -DecisionPhase names the
# 12b_vbk0_* phase whose decision record is "decided" (base, b3 or b4). The VBK runs of every
# decided block (4 workers each on a P quarter), then per arm grade-judge (r79_sensor_judge with
# the arm's own L1 run of step_l1ref.ps1, erratum 2 2-1; control review W-6) and the judge
# (decision sha first: a changed or stopped decision opens no VBK file). Exit: the judge's code
# (0 pass; 1 failed = the cost gate failed, stop and re-design, 8 5; 2 / 3 stop and ask).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b3', 'b4')][string]$DecisionPhase)
. "$PSScriptRoot\common_ed5.ps1"

$Vbk0Phases = @(@('12b_vbk0_base', '12b_vbk0_b3', '12b_vbk0_b4') |
        Where-Object { Test-Path -LiteralPath "$RunsRoot\$_.done" })
$Folder = Initialize-Ed5Step '12b_vbk' $Attempt (@('dry', 'l1ref') + $Vbk0Phases)
$DecisionFolder = Get-StepFolder "12b_vbk0_$DecisionPhase"
$Decision = "$DecisionFolder\judge\decision.json"
$DecisionSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Decision).Hash.ToLower()
$Record = Get-Content -Raw -LiteralPath $Decision | ConvertFrom-Json
if ($Record.status -ne 'decided') { Stop-Step 2 "decision of $DecisionPhase is $($Record.status), not decided" }
$Blocks = @($Record.blocks)
$Masks = @('0x000F', '0x00F0', '0x0F00', '0xF000')

$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBK_$Block"
    $Out = "$Folder\$Label.json"
    $RunEstimatesS[$Label] = 1900
    $Runs += Start-Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out `
        -Environment (Get-R79Environment 'VBK' "$Folder\${Label}_t4h" "$X11Folder\${Block}_plan.json") `
        -TaskType 'jp3_12b_vbk' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$X11Folder\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck

# the VBK0 files of the decided blocks (the folders of the done VBK0 phases)
$Vbk0 = @{}
foreach ($Phase in $Vbk0Phases) {
    $Source = Get-StepFolder $Phase
    foreach ($File in @(Get-ChildItem -LiteralPath $Source -File -Filter 'VBK0_b?.json')) {
        $Vbk0[$File.BaseName.Substring(5)] = @($File.FullName, "$Source\$($File.BaseName)_t4h")
    }
}
$Judge = "$Coupled/jp3_12b_judge.py"
# erratum 2 2-1: each arm's own L1 run of the l1ref step (VBK0: VBJ0, VBK: VBJ), its sha256 and
# the L1 key file's from the fixed list
$L1OfArm = @{ vbk0 = (Get-L1Run 'VBJ0'); vbk = (Get-L1Run 'VBJ') }
$L1KeysSha = Get-ListedSha $L1KeysFile
$GradeFiles = @{}
$GradeExits = @{}
foreach ($Arm in @('vbk0', 'vbk')) {
    $Arguments = @($Judge, 'grade-judge', '--arm', $Arm, '--l1-reference', $L1OfArm[$Arm],
        '--l1-reference-sha256', (Get-ListedSha $L1OfArm[$Arm]), '--l1-keys-sha256', $L1KeysSha,
        '--judge-out', "$Folder\judge\grades_$Arm.json", '--out', "$Folder\judge\grades_${Arm}_record.json")
    foreach ($Block in $Blocks) {
        $Path = if ($Arm -eq 'vbk') { "$Folder\VBK_$Block.json" } else { $Vbk0[$Block][0] }
        $Arguments += @('--runs', "$Block=$Path")
    }
    # erratum 2 2-1 (audit F-1): the grade transitions are a record - grade-judge exit 2 (an L1
    # reference defect) and exit 3 (a tool error) both go on; the judge then records "not
    # computed" with the reason ("grade-judge 종료 <code>") and its status and exit code stay
    # the 12b judgement's
    $GradeCode = Invoke-Judge "grade_judge_$Arm" $Arguments -ContinueCodes @(0, 2, 3)
    $GradeExits[$Arm] = $GradeCode
    $GradeRecord = "$Folder\judge\grades_${Arm}_record.json"
    if ($GradeCode -eq 0 -and (Test-Path -LiteralPath $GradeRecord)) {
        $GradeFiles[$Arm] = @("$Folder\judge\grades_$Arm.json", (Read-ReportField $GradeRecord 'judge_sha256'))
    }
}

$Arguments = @($Judge, 'judge', '--selection', $X11Selection, '--selection-sha256', (Get-X11Sha),
    '--decision', $Decision, '--decision-sha256', $DecisionSha, '--out', "$Folder\judge\judge.json")
foreach ($Block in $Blocks) {
    $Arguments += @('--vbk0', "$Block=$($Vbk0[$Block][0])", '--vbk0-t4h', "$Block=$($Vbk0[$Block][1])",
        '--vbk', "$Block=$Folder\VBK_$Block.json", '--vbk-t4h', "$Block=$Folder\VBK_${Block}_t4h")
}
foreach ($Arm in @('vbk0', 'vbk')) {
    if ($GradeFiles.ContainsKey($Arm)) {
        $Arguments += @("--$Arm-grade-judge", $GradeFiles[$Arm][0], "--$Arm-grade-judge-sha256", $GradeFiles[$Arm][1])
    } else {  # a missing arm: the judge records "not computed" with the grade-judge exit code
        $Arguments += @("--$Arm-grade-judge-exit", "$($GradeExits[$Arm])")
    }
}
Invoke-Judge 'judge' $Arguments | Out-Null
# erratum 2 2-9.6: the done marker names the judge file and its sha256 (step 8 checks them)
$StepState.Codes['judge_file'] = Get-RepoPath "$Folder\judge\judge.json"
$StepState.Codes['judge_sha256'] = (Get-FileHash -Algorithm SHA256 -LiteralPath "$Folder\judge\judge.json").Hash.ToLower()

Complete-Step
