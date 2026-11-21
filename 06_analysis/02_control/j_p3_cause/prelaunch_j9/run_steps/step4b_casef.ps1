#Requires -Version 7
# Step (4b) case F (spec 13.8; 4a-2 R8): run_v5 j9_case_f (15 runs, --workers 8, mask 0xFFFF)
# -> jp3_case_judge.py case-f (F-A / F-B / F-E). Needs steps 2 and 3 (4a-5 5.1).
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'casef' $Attempt @('dry', 'fpath')
$Rows = "$Folder\j9_case_f.jsonl"

$Run = Start-Run -Label 'j9_case_f' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_case_f' -Workers 8 `
    -Arguments @("$Coupled/run_v5.py", 'j9_case_f', '--out', $Rows, '--workers', '8', '--mask', '0xFFFF')
Wait-Runs @($Run)
Invoke-IdentityCheck

Invoke-Judge 'case_f' @("$Coupled/jp3_case_judge.py", 'case-f', '--rows', $Rows,
    '--grid', (Get-FixedPath 'GRID_SHA256'), '--out', "$Folder\judge\case_f.json") | Out-Null

Complete-Step
