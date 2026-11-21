#Requires -Version 7
# Step (3) F-A path equivalence (spec v5 8 4.(3); 4a-3 5.2): run_v5 j9_case_f_path (3 runs,
# --workers 3, mask 0xFFFF) -> case-f-path -> P5-1 against the 78fd5d2d rows.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'fpath' $Attempt @()
$Rows = "$Folder\j9_case_f_path.jsonl"

$Run = Start-Run -Label 'j9_case_f_path' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_case_f_path' -Workers 3 `
    -Arguments @("$Coupled/run_v5.py", 'j9_case_f_path', '--out', $Rows, '--workers', '3', '--mask', '0xFFFF')
Wait-Runs @($Run)
Invoke-IdentityCheck

Invoke-Judge 'case_f_path' @("$Coupled/jp3_case_judge.py", 'case-f-path', '--rows', $Rows,
    '--grid', (Get-FixedPath 'GRID_SHA256'), '--out', "$Folder\judge\case_f_path.json") | Out-Null
Invoke-P51 'fpath' "$(Get-PreviousStepFolder 'fpath')\j9_case_f_path.jsonl" $Rows

Complete-Step
