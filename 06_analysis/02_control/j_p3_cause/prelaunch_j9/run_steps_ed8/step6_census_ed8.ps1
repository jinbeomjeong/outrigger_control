#Requires -Version 7
# Step 6, census (spec v8 4 step 6, 5): run_v5 ed8_keys on the sealed census_keys_ed8.json (1043
# lines: C-J 388, C-S 460, C-D 24, C-G 171; sha256 278b332f..., run_v5.ED8_KEY_FILE_SHA256),
# then the identity check. No judge (T8 census-judge). Needs step 5 v0. Placement from
# compute-scheduler-expert.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed8.ps1"

$Requires = @('impl_scope', 'l1ref', 'impl_p80', 'impl_p816', 'impl_p85', 'impl_p88', 'impl_p815',
    'impl_t8', 'impl_cases', 'ho_v0')
$Folder = Initialize-Ed8Step 'census' $Attempt $Requires @('census_keys')
$Rows = "$Folder\census.jsonl"
$RunEstimatesS['census'] = [int](1043 * 143 / $Workers)
$Run = Start-Ed8Run -Label 'census' -MaskHex $MaskHex -TaskType 'run_v5_ed8_census' -Workers $Workers `
    -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed8_keys', '--jobs-file', (Get-InputPath 'census_keys'),
        '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

Complete-Step
