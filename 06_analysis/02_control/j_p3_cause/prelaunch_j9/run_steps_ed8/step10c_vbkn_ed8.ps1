#Requires -Version 7
# Step 12b_vbkn (spec v8 8 = edition 7 6.4): the VBKN runs of the decided blocks. The P-pred
# decision (status decided, its blocks) is the judge commit T8's file, given with its sha256
# (-Decision, -DecisionSha256); a block b4 needs the 12b_vbkn0_b4 step. Then the identity check.
# No judge (grade-judge and the 12b judge belong to T). One P quarter of 4 workers per block.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$Decision, [Parameter(Mandatory)][string]$DecisionSha256,
    [string]$S8cRules = '', [string]$S8cSha256 = '')
. "$PSScriptRoot\common_ed8.ps1"

$Requires = @('impl_scope', 'l1ref', 'census', 'heldout', 'dg3', '12b_plan', '12b_vbkn0')
if (Test-Path -LiteralPath "$RunsRoot\12b_vbkn0_b4.done") { $Requires += @('12b_vbkn0_b4') }
$Folder = Initialize-Ed8Step '12b_vbkn' $Attempt $Requires
Assert-S8cSeal $S8cRules $S8cSha256
$Document = Read-Decision $Decision $DecisionSha256 @('decided')
$Blocks = @($Document.blocks | ForEach-Object { [string]$_ })
$Allowed = @('b1', 'b2', 'b4')
if (-not $Blocks.Count -or @($Blocks | Where-Object { $Allowed -notcontains $_ }).Count) {
    Stop-Step 2 "decision blocks '$($Blocks -join ',')' are not a set of b1 / b2 / b4"
}
if ($Blocks -contains 'b4' -and $Requires -notcontains '12b_vbkn0_b4') { Stop-Step 2 'decision names b4 but 12b_vbkn0_b4 is not done' }
$StepState.Codes['decision_blocks'] = $Blocks -join ','
$PlanDir = "$(Get-StepFolder '12b_plan')\x11"
$SelectionSha = Get-DoneCode '12b_plan' 'selection_sha256'
if (-not $IsEd8Dry -and (Get-FileHash -Algorithm SHA256 -LiteralPath "$PlanDir\selection.json").Hash.ToLower() -ne $SelectionSha) {
    Stop-Step 2 "$PlanDir\selection.json is not the file the 12b_plan step wrote"
}
$StepState.Codes['selection_sha256'] = $SelectionSha

$Masks = @('0x000F', '0x00F0', '0x0F00')
$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBKN_$Block"
    $Out = "$Folder\$Label.json"
    $T4h = "$Folder\${Label}_t4h"
    $RunEstimatesS[$Label] = 3800  # edition 5 VBK blocks: 3,757 s at 4 workers
    $Runs += Start-Ed8Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out -Outputs @($Out, $T4h) `
        -Environment (Get-R79Environment 'VBKN' $T4h "$PlanDir\${Block}_plan.json") `
        -TaskType 'jp3_ed8_12b_vbkn' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$PlanDir\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
