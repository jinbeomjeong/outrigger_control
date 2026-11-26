#Requires -Version 7
# Step 9, T-JR-12a (spec v8 8 = edition 7 6.4): VBN against VBN0 on the Dg-3 135 keys of the
# stored H-6 (VBN 0x00FF and VBN0 0xFF00, 4 workers each; R79_ROD_MODEL=plant_truth), after the
# S8-C seal, then the identity check. No judge (T8). Needs the heldout step.
param([int]$Attempt = 1, [string]$S8cRules = '', [string]$S8cSha256 = '')
. "$PSScriptRoot\common_ed8.ps1"

$Folder = Initialize-Ed8Step 'dg3' $Attempt @('impl_scope', 'l1ref', 'census', 'heldout')
Assert-S8cSeal $S8cRules $S8cSha256
$Placement = [ordered]@{ VBN = @('0x00FF', 4); VBN0 = @('0xFF00', 4) }
$RunEstimatesS['dg3_VBN'] = 2250; $RunEstimatesS['dg3_VBN0'] = 2250
$Runs = @()
foreach ($Setting in $Placement.Keys) {
    $MaskHex, $RunWorkers = $Placement[$Setting]
    $Out = "$Folder\dg3_$Setting.json"
    $T4h = "$Folder\${Setting}_t4h"
    $Runs += Start-Ed8Run -Label "dg3_$Setting" -MaskHex $MaskHex -WrapOutput $Out -Outputs @($Out, $T4h) `
        -Environment (Get-R79Environment $Setting $T4h) -TaskType 'jp3_ed8_dg3_r79' -Workers $RunWorkers `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2,L3', '--keys-file', $H6Keys,
            '--workers', "$RunWorkers", '--affinity', $MaskHex)
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
