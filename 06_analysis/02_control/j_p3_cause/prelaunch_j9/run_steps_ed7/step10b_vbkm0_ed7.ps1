#Requires -Version 7
# Step 12b_vbkm0 (spec v7 6.4 = edition 6 6.4): the VBKM0 arm of T-JR-12b with the rod fault
# plans of the 12b_plan step (its selection.json sha256 as that step recorded it).
#   -Phase base   b1 and b2 at once (4 workers each on one P quarter)
#   -Phase b4     only when the P-pred decision of the judge commit T says needs_b4: the b4 VBKM0
#                 run (-Decision = T's decision file, -DecisionSha256 = its sha256; status
#                 needs_b4)
#   (b3 is never run: N_opp < 0.9 N is not judgeable, edition 6 6.4)
# No VBKM file exists before the decision (the P-pred allowance is set on VBKM0 b1 / b2 only).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b4')][string]$Phase,
    [string]$Decision = '', [string]$DecisionSha256 = '')
. "$PSScriptRoot\common_ed7.ps1"

$Before = @('impl_scope', 'l1ref', 'impl_probe', 'confirm', 'j9main', 'sens', 'dg3', '12b_plan')
$Masks = @('0x000F', '0x00F0')
if ($Phase -eq 'base') {
    $Folder = Initialize-Ed7Step '12b_vbkm0' $Attempt $Before
    $Blocks = @('b1', 'b2')
} else {
    if (-not $Decision -or -not $DecisionSha256) { Exit-Ed7 3 '-Phase b4 needs -Decision and -DecisionSha256 (the P-pred decision of T)' }
    $Folder = Initialize-Ed7Step '12b_vbkm0_b4' $Attempt ($Before + @('12b_vbkm0'))
    Read-Decision $Decision $DecisionSha256 @('needs_b4') | Out-Null
    $Blocks = @('b4')
}
$PlanDir = "$(Get-StepFolder '12b_plan')\x11"
$SelectionSha = Get-DoneCode '12b_plan' 'selection_sha256'
if (-not $IsEd7Dry -and (Get-FileHash -Algorithm SHA256 -LiteralPath "$PlanDir\selection.json").Hash.ToLower() -ne $SelectionSha) {
    Stop-Step 2 "$PlanDir\selection.json is not the file the 12b_plan step wrote"
}
$StepState.Codes['selection_sha256'] = $SelectionSha
$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBKM0_$Block"
    $Out = "$Folder\$Label.json"
    $T4h = "$Folder\${Label}_t4h"
    $RunEstimatesS[$Label] = 3600  # edition 5 VBK0 blocks: 3,550 s at 4 workers
    $Runs += Start-Ed7Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out -Outputs @($Out, $T4h) `
        -Environment (Get-R79Environment 'VBKM0' $T4h "$PlanDir\${Block}_plan.json") `
        -TaskType 'jp3_ed7_12b_vbkm0' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$PlanDir\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
