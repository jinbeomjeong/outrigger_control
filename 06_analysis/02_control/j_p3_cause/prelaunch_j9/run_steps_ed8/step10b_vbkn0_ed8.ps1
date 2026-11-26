#Requires -Version 7
# Step 12b_vbkn0 (spec v8 8 = edition 7 6.4): the VBKN0 arm of T-JR-12b with the rod fault
# plans of the 12b_plan step (its selection.json sha256 as that step recorded it).
#   -Phase base   b1 and b2 at once (4 workers each on one P quarter)
#   -Phase b4     only when the P-pred decision of the judge commit T8 says needs_b4: the b4 VBKN0
#                 run (-Decision = T's decision file, -DecisionSha256 = its sha256; status
#                 needs_b4)
#   (b3 is never run: N_opp < 0.9 N is not judgeable, edition 6 6.4)
# No VBKN file exists before the decision (the P-pred allowance is set on VBKN0 b1 / b2 only).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b4')][string]$Phase,
    [string]$Decision = '', [string]$DecisionSha256 = '',
    [string]$S8cRules = '', [string]$S8cSha256 = '')
. "$PSScriptRoot\common_ed8.ps1"

$Before = @('impl_scope', 'l1ref', 'census', 'heldout', 'dg3', '12b_plan')
$Masks = @('0x000F', '0x00F0')
if ($Phase -eq 'base') {
    $Folder = Initialize-Ed8Step '12b_vbkn0' $Attempt $Before
    $Blocks = @('b1', 'b2')
} else {
    if (-not $Decision -or -not $DecisionSha256) { Exit-Ed8 3 '-Phase b4 needs -Decision and -DecisionSha256 (the P-pred decision of T)' }
    $Folder = Initialize-Ed8Step '12b_vbkn0_b4' $Attempt ($Before + @('12b_vbkn0'))
    Read-Decision $Decision $DecisionSha256 @('needs_b4') | Out-Null
    $Blocks = @('b4')
}
Assert-S8cSeal $S8cRules $S8cSha256
$PlanDir = "$(Get-StepFolder '12b_plan')\x11"
$SelectionSha = Get-DoneCode '12b_plan' 'selection_sha256'
if (-not $IsEd8Dry -and (Get-FileHash -Algorithm SHA256 -LiteralPath "$PlanDir\selection.json").Hash.ToLower() -ne $SelectionSha) {
    Stop-Step 2 "$PlanDir\selection.json is not the file the 12b_plan step wrote"
}
$StepState.Codes['selection_sha256'] = $SelectionSha
$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBKN0_$Block"
    $Out = "$Folder\$Label.json"
    $T4h = "$Folder\${Label}_t4h"
    $RunEstimatesS[$Label] = 3600  # edition 5 VBK0 blocks: 3,550 s at 4 workers
    $Runs += Start-Ed8Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out -Outputs @($Out, $T4h) `
        -Environment (Get-R79Environment 'VBKN0' $T4h "$PlanDir\${Block}_plan.json") `
        -TaskType 'jp3_ed8_12b_vbkn0' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$PlanDir\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
