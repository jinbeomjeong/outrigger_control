#Requires -Version 7
# Step dg3 (spec v7 4 step 9, 6.4 = edition 6 6.5): T-JR-12a VBM against VBM0 on the Dg-3 135
# keys of the stored H-6 (VBM 0x00FF and VBM0 0xFF00, 4 workers each, the edition 6 placement;
# R79_ROD_MODEL=plant_truth, each run's T4h folder beside it), then the identity check. No judge:
# dg3-judge / t12 (with the L1a runs of the l1ref step) belong to the judge commit T (5.2).
# Needs the sens step.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed7.ps1"

$Folder = Initialize-Ed7Step 'dg3' $Attempt @('impl_scope', 'l1ref', 'impl_probe', 'confirm', 'j9main', 'sens')
$Placement = [ordered]@{ VBM = @('0x00FF', 4); VBM0 = @('0xFF00', 4) }
$RunEstimatesS['dg3_VBM'] = 2250; $RunEstimatesS['dg3_VBM0'] = 2250
# wall [s] of the edition 5 Dg-3 runs at 4 workers (dg3_a1 VBJ 2,205 s)
$Runs = @()
foreach ($Setting in $Placement.Keys) {
    $MaskHex, $RunWorkers = $Placement[$Setting]
    $Out = "$Folder\dg3_$Setting.json"
    $T4h = "$Folder\${Setting}_t4h"
    $Runs += Start-Ed7Run -Label "dg3_$Setting" -MaskHex $MaskHex -WrapOutput $Out -Outputs @($Out, $T4h) `
        -Environment (Get-R79Environment $Setting $T4h) -TaskType 'jp3_ed7_dg3_r79' -Workers $RunWorkers `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2,L3', '--keys-file', $H6Keys,
            '--workers', "$RunWorkers", '--affinity', $MaskHex)
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
