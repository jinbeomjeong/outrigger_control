#Requires -Version 7
# Step 8, held-out G' (spec v8 4 step 8, 7): run_v5 ed8_keys on the sealed heldout_g_ed8.json
# (339 VBN lines), after the S8-C seal (-S8cRules, -S8cSha256), then the identity check. No
# judge (T8 heldout-judge). Needs the census step. Placement from compute-scheduler-expert.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers,
    [string]$S8cRules = '', [string]$S8cSha256 = '')
. "$PSScriptRoot\common_ed8.ps1"

$Requires = @('impl_scope', 'l1ref', 'impl_p816', 'ho_v0', 'census')
$Folder = Initialize-Ed8Step 'heldout' $Attempt $Requires @('heldout_keys')
Assert-S8cSeal $S8cRules $S8cSha256
$Rows = "$Folder\heldout.jsonl"
$RunEstimatesS['heldout'] = [int](339 * 143 / $Workers)
$Run = Start-Ed8Run -Label 'heldout' -MaskHex $MaskHex -TaskType 'run_v5_ed8_heldout' -Workers $Workers `
    -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed8_keys', '--jobs-file', (Get-InputPath 'heldout_keys'),
        '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

Complete-Step
