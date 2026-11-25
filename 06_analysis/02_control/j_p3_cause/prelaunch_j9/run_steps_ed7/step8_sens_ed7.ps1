#Requires -Version 7
# Step sens (spec v7 4 step 8, 6.2): run_v5 batch ed7_keys on the sealed sens_keys_ed7.json
# (460 lines: the four judged settings VBMslow / VBMfast / VBMc005 / VBMc04 and the six record
# settings; sha256 be930b75..., also asserted by run_v5.ED7_KEY_FILE_SHA256), then the identity
# check. No judge (the sensitivity judge of the judge commit T, 5.2). Needs the j9main step.
# Placement from compute-scheduler-expert.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed7.ps1"

$Folder = Initialize-Ed7Step 'sens' $Attempt @('impl_scope', 'l1ref', 'impl_probe', 'confirm', 'j9main') @('sens_keys')
$Rows = "$Folder\sens.jsonl"
$RunEstimatesS['sens'] = [int](460 * 143 / $Workers)
$Run = Start-Ed7Run -Label 'sens' -MaskHex $MaskHex -TaskType 'run_v5_ed7_sens' -Workers $Workers `
    -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed7_keys', '--jobs-file', (Get-InputPath 'sens_keys'),
        '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

Complete-Step
