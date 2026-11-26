#Requires -Version 7
# Step 5, G' V0 pre-run (spec v8 4 step 5, 7.3, 7.4): V0 only, never VBN (G' VBN waits for step 8
# after the S8-C seal).
#   -Part v0    run_v5 ed8_heldout_v0: each slot's condition V0 and its first A/A candidate V0
#               (678 lines)
#   -Part aa2   run_v5 ed8_heldout_aa2: every slot's second A/A candidate V0 (339; T8 uses only
#               the slots whose earlier candidate fell in the other layer, at most 3 tries)
#   -Part aa3   run_v5 ed8_heldout_aa3: the third candidates (339)
# The key file is the sealed heldout_g_ed8.json (sha256 a18b5818..., run_v5.ED8_KEY_FILE_SHA256).
# Needs every step 4 part. Placement from compute-scheduler-expert.
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('v0', 'aa2', 'aa3')][string]$Part,
    [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed8.ps1"

$Step4 = @('impl_scope', 'l1ref', 'impl_p80', 'impl_p816', 'impl_p85', 'impl_p88', 'impl_p815',
    'impl_t8', 'impl_cases')
$Requires = switch ($Part) { 'v0' { $Step4 } 'aa2' { $Step4 + @('ho_v0') } 'aa3' { $Step4 + @('ho_v0', 'ho_aa2') } }
$Folder = Initialize-Ed8Step "ho_$Part" $Attempt $Requires @('heldout_keys')
$Batch = @{ v0 = 'ed8_heldout_v0'; aa2 = 'ed8_heldout_aa2'; aa3 = 'ed8_heldout_aa3' }[$Part]
$Lines = @{ v0 = 678; aa2 = 339; aa3 = 339 }[$Part]
$Rows = "$Folder\$Batch.jsonl"
$RunEstimatesS[$Batch] = [int]($Lines * 143 / $Workers)
$Run = Start-Ed8Run -Label $Batch -MaskHex $MaskHex -TaskType "run_v5_$Batch" -Workers $Workers `
    -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", $Batch, '--jobs-file', (Get-InputPath 'heldout_keys'),
        '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

Complete-Step
