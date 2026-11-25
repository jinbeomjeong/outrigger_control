#Requires -Version 7
# Step j9main (spec v7 4 step 7, 6.2): run_v5 batch ed7_j9_main (VBM 100 + LSM1 .. LSM4 x 72 =
# 388 lines), then the identity check. No judge (j9main --edition 7 of the judge commit T,
# 5.2 item 11). Needs the confirm step. Placement from compute-scheduler-expert.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed7.ps1"

$Folder = Initialize-Ed7Step 'j9main' $Attempt @('impl_scope', 'l1ref', 'impl_probe', 'confirm')
$Rows = "$Folder\j9_main.jsonl"
$RunEstimatesS['j9_main'] = [int](388 * 143 / $Workers)
$Run = Start-Ed7Run -Label 'j9_main' -MaskHex $MaskHex -TaskType 'run_v5_ed7_j9_main' -Workers $Workers `
    -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed7_j9_main', '--out', $Rows,
        '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

Complete-Step
