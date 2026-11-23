#Requires -Version 7
# Step (6c) T-JR-12b VBK and judgement (spec v5 6.3.7 with erratum 8 8-2; erratum 8 8-9 "12b
# 진행" 4 .. 5 and (f): the script of the tool commit; the VBK runs at the run commit in
# ed5-run5 with --expect-commit of the run commit through the identity check; grade-judge and
# the judge in the tool checkout at the tool commit - the step record names both expectations).
#   1. the decision record (8-9 4): the one 12b_decide_e8_b4.done names, else the one
#      12b_decide_e8.done names; it must be decided (blocks, blocks_used, allow_k agree)
#   2. the VBK runs of its blocks (4 workers each on a P quarter), each with the run condition
#      of the b1 / b2 VBK0 runs (8-9 (c): environment and --workers before, identity after)
#   3. per arm grade-judge (r79_sensor_judge with the arm's own L1 run of step_l1ref.ps1,
#      erratum 2 2-1; control review W-6) and the judge (decision sha first: a changed or
#      refused decision opens no VBK file); the VBK0 files: b1 / b2 of 12b_vbk0_base_a1
#      (8-9 (e)), b4 of 12b_vbk0_b4
# Exit: the judge's code (0 pass; 1 failed = the cost gate failed, stop and re-design, 8 5;
# 2 / 3 stop and ask). The done marker names the judge file and its sha256 (2-9.6).
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Requires = @('dry', 'l1ref', '12b_decide_e8')
if (Test-Path -LiteralPath "$RunsRoot\12b_decide_e8_b4.done") { $Requires += @('12b_vbk0_b4', '12b_decide_e8_b4') }
$Folder = Initialize-E8Step '12b_vbk' $Attempt $Requires
$Choice = Get-E8DecisionChoice $RunsRoot
if ($Choice.ContainsKey('code')) { Stop-Step $Choice.code $Choice.reason }
$Decision = $Choice.path
$StepState.Codes['decision_step'] = $Choice.step
$StepState.Codes['decision_file'] = Get-RepoPath $Decision
$DecisionSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Decision).Hash.ToLower()
$StepState.Codes['decision_sha256'] = $DecisionSha
$Blocks = @((Get-Content -Raw -LiteralPath $Decision | ConvertFrom-Json).blocks)

# the VBK0 files of the decided blocks
$BaseFolder = Get-E8BaseVbk0Folder
$Vbk0 = @{ b1 = @("$BaseFolder\VBK0_b1.json", "$BaseFolder\VBK0_b1_t4h")
    b2 = @("$BaseFolder\VBK0_b2.json", "$BaseFolder\VBK0_b2_t4h") }
if ($Blocks -contains 'b4') {
    $B4Folder = Get-StepFolder '12b_vbk0_b4'
    $Vbk0['b4'] = @("$B4Folder\VBK0_b4.json", "$B4Folder\VBK0_b4_t4h")
}
foreach ($Block in $Blocks) {
    if (-not $Vbk0.ContainsKey($Block)) { Stop-Step 2 "decided block $Block has no VBK0 output (erratum 8 8-2: b1, b2, b4 only)" }
}

$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBK_$Block"
    $Out = "$Folder\$Label.json"
    $Environment = Get-R79Environment 'VBK' "$Folder\${Label}_t4h" "$X11Folder\${Block}_plan.json"
    Assert-E8RunCondition $BaseFolder 'VBK' $Environment $E8RequiredWorkers
    $RunEstimatesS[$Label] = 1900
    $Runs += Start-Run -Label $Label -MaskHex $E8RunMasks[$Index] -WrapOutput $Out -Environment $Environment `
        -TaskType 'jp3_12b_vbk' -Workers $E8RequiredWorkers -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$X11Folder\${Block}_keys.txt", '--workers', "$E8RequiredWorkers",
            '--affinity', $E8RunMasks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck
foreach ($Block in $Blocks) { Assert-E8RunIdentity $BaseFolder "$Folder\VBK_$Block.identity.json" }

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
        $RunFile = if ($Arm -eq 'vbk') { "$Folder\VBK_$Block.json" } else { $Vbk0[$Block][0] }
        $Arguments += @('--runs', "$Block=$RunFile")
    }
    # erratum 2 2-1 (audit F-1): the grade transitions are a record - grade-judge exit 2 (an L1
    # reference defect) and exit 3 (a tool error) both go on; the judge then records "not
    # computed" with the reason ("grade-judge 종료 <code>") and its status and exit code stay
    # the 12b judgement's
    $GradeCode = Invoke-ToolJudge "grade_judge_$Arm" $Arguments -ContinueCodes @(0, 2, 3)
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
Invoke-ToolJudge 'judge' $Arguments | Out-Null
# erratum 2 2-9.6: the done marker names the judge file and its sha256 (step 8 checks them)
$StepState.Codes['judge_file'] = Get-RepoPath "$Folder\judge\judge.json"
$StepState.Codes['judge_sha256'] = (Get-FileHash -Algorithm SHA256 -LiteralPath "$Folder\judge\judge.json").Hash.ToLower()

Complete-Step
