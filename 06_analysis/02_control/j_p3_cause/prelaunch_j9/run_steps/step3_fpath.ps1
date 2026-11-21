#Requires -Version 7
# Step (3) 4a-3 5.2 F-A path equivalence: run_v5 j9_case_f_path (3 runs, --workers 3,
# mask 0xFFFF; run_v5 writes its own identity sidecar with --out) -> case-f-path.
# 4a-5 5.1: != 0 forbids case F (step 4b).
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'fpath' $Attempt @()
$Rows = "$Folder\j9_case_f_path.jsonl"

$Run = Start-Run -Label 'j9_case_f_path' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_case_f_path' -Workers 3 `
    -Arguments @("$Coupled/run_v5.py", 'j9_case_f_path', '--out', $Rows, '--workers', '3', '--mask', '0xFFFF')
Wait-Runs @($Run)
Invoke-IdentityCheck

Invoke-Judge 'case_f_path' @("$Coupled/jp3_case_judge.py", 'case-f-path', '--rows', $Rows,
    '--grid', (Get-FixedPath 'GRID_SHA256'), '--out', "$Folder\judge\case_f_path.json") | Out-Null

Complete-Step
