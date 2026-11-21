#Requires -Version 7
# Step (6c) T-JR-12b VBK and judgement (spec v5 6.3.7, 8 4.(6) 5 .. 6): -DecisionPhase names the
# 12b_vbk0_* phase whose decision record is "decided" (base, b3 or b4). The VBK runs of every
# decided block (4 workers each on a P quarter), then per arm grade-judge (r79_sensor_judge with
# the L1 lines of the fixed case source h8_noise_VB.json; control review W-6) and the judge
# (decision sha first: a changed or stopped decision opens no VBK file). Exit: the judge's code
# (0 pass; 1 failed = the cost gate failed, stop and re-design, 8 5; 2 / 3 stop and ask).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b3', 'b4')][string]$DecisionPhase)
. "$PSScriptRoot\common_ed5.ps1"

$Vbk0Phases = @(@('12b_vbk0_base', '12b_vbk0_b3', '12b_vbk0_b4') |
        Where-Object { Test-Path -LiteralPath "$RunsRoot\$_.done" })
$Folder = Initialize-Ed5Step '12b_vbk' $Attempt (@('dry') + $Vbk0Phases)
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
$Noise = Get-FixedPath 'NOISE_VB_SHA256'
$NoiseSha = $FixedInputs['NOISE_VB_SHA256'][1]
$GradeFiles = @{}
foreach ($Arm in @('vbk0', 'vbk')) {
    $Arguments = @($Judge, 'grade-judge', '--arm', $Arm, '--l1-reference', $Noise, '--l1-reference-sha256', $NoiseSha,
        '--judge-out', "$Folder\judge\grades_$Arm.json", '--out', "$Folder\judge\grades_${Arm}_record.json")
    foreach ($Block in $Blocks) {
        $Path = if ($Arm -eq 'vbk') { "$Folder\VBK_$Block.json" } else { $Vbk0[$Block][0] }
        $Arguments += @('--runs', "$Block=$Path")
    }
    Invoke-Judge "grade_judge_$Arm" $Arguments | Out-Null
    $GradeFiles[$Arm] = @("$Folder\judge\grades_$Arm.json",
        (Read-ReportField "$Folder\judge\grades_${Arm}_record.json" 'judge_sha256'))
}

$Arguments = @($Judge, 'judge', '--selection', $X11Selection, '--selection-sha256', (Get-X11Sha),
    '--decision', $Decision, '--decision-sha256', $DecisionSha, '--out', "$Folder\judge\judge.json")
foreach ($Block in $Blocks) {
    $Arguments += @('--vbk0', "$Block=$($Vbk0[$Block][0])", '--vbk0-t4h', "$Block=$($Vbk0[$Block][1])",
        '--vbk', "$Block=$Folder\VBK_$Block.json", '--vbk-t4h', "$Block=$Folder\VBK_${Block}_t4h")
}
foreach ($Arm in @('vbk0', 'vbk')) {
    $Arguments += @("--$Arm-grade-judge", $GradeFiles[$Arm][0], "--$Arm-grade-judge-sha256", $GradeFiles[$Arm][1])
}
Invoke-Judge 'judge' $Arguments | Out-Null

Complete-Step
