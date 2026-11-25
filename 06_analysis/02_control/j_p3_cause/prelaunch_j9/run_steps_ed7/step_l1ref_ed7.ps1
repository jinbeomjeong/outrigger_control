#Requires -Version 7
# Step l1ref (spec v7 6.4 = edition 6 6.4 / 6.5 and its erratum 1 1-2 carried over): the four L1
# reference runs at the run commit, before any 12a / 12b output (never made again afterwards):
#   L1_VBM0 / L1_VBM    12b grade references, the 167 keys of ed5_inputs\l1_keys_12b.txt
#   L1a_VBM0 / L1a_VBM  T-JR-12a references, the 102 keys of l1_keys_d3c6c57e.json
# R79_ROD_MODEL=plant_truth, 4 workers each on one P quarter (the edition 6 placement). No tool:
# the 12a / 12b judges of the judge commit T read these files. Exit 0 done, 2 a later output
# exists, 3 a failed run or a broken precondition.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed7.ps1"

if (Test-Path -LiteralPath $RunsRoot) {
    $Later = @(Get-ChildItem -LiteralPath $RunsRoot -Directory | Where-Object { $_.Name -like '12b_*' -or $_.Name -like 'dg3_*' })
    if ($Later.Count) { Exit-Ed7 2 "$($Later[0].FullName) exists (the L1 references are made before any 12a / 12b output)" }
}
$Folder = Initialize-Ed7Step 'l1ref' $Attempt @('impl_scope') @('l1_keys_12b', 'l1_keys_12a')
$Masks = @('0x000F', '0x00F0', '0x0F00', '0xF000')
$Estimates = @{ L1_VBM0 = 2250; L1_VBM = 2250; L1a_VBM0 = 1450; L1a_VBM = 1450 }
# wall [s] of the edition 5 L1 runs at 4 workers (l1ref_a1 2,198 / 2,233 s; dg3_a1 l1 1,324 / 1,423 s)

$Runs = @()
$Index = 0
foreach ($Label in $L1Labels.Keys) {
    $Setting, $KeysName = $L1Labels[$Label]
    $Out = "$Folder\$Label.json"
    $T4h = "$Folder\${Label}_t4h"
    $RunEstimatesS[$Label] = $Estimates[$Label]
    $Runs += Start-Ed7Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out -Outputs @($Out, $T4h) `
        -Environment (Get-R79Environment $Setting $T4h) -TaskType 'jp3_ed7_l1ref' -Workers 4 `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L1', '--keys-file',
            (Get-InputPath $KeysName), '--workers', '4', '--affinity', $Masks[$Index])
    $Index++
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
