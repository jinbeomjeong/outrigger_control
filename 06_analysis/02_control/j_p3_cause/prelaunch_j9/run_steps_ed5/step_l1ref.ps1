#Requires -Version 7
# Prelaunch step: the 12b L1 grade reference (erratum 2 2-1), at the run commit, before the
# fixed list (its two outputs and the key file go into FIXED_INPUTS) and before any 12b run.
# The L1 key file of prelaunch_ed5.ps1 -Part l1keys under VBJ0 (the VBK0 arm's plant) and VBJ
# (the VBK arm's plant: the VBK options, no fault plan), R79_ROD_MODEL=plant_truth, 4 workers
# each on half of the P threads. No judge tool; grade-judge checks these files later.
# Run order: -Part dry, -Part l1keys, this step, -Part x11, -Part list, then step0_cdry.ps1.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

# the fixed list does not exist yet: the edition 4a step start (commit, tree, 4a fixed inputs)
$Folder = Initialize-Step 'l1ref' $Attempt @()
if (-not (Test-Path -LiteralPath $L1KeysFile)) { Stop-Step 3 "$L1KeysFile missing (prelaunch_ed5.ps1 -Part l1keys)" }
$Placement = [ordered]@{ VBJ0 = '0x00FF'; VBJ = '0xFF00' }

$Runs = @()
foreach ($Setting in $L1Settings) {
    $Label = "L1_$Setting"
    $Out = "$Folder\$Label.json"
    $RunEstimatesS[$Label] = 600
    $Runs += Start-Run -Label $Label -MaskHex $Placement[$Setting] -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Label}_t4h") -TaskType 'jp3_12b_l1ref' -Workers 4 `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L1',
            '--keys-file', $L1KeysFile, '--workers', '4', '--affinity', $Placement[$Setting])
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
