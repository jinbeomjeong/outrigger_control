#Requires -Version 7
# Step (5) T-JR-10 / T-JR-11 (spec v5 8 4.(5); 4a-3 2, 3; 4a-4 4, 5; 4a-5 2): run_v5 j9_t8 (88
# runs, --workers 8, mask 0xFFFF) -> jp3_tjr_judge.py t8 -> P5-1 against the 78fd5d2d rows.
# Needs step 2.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 't8' $Attempt @('dry')
$Rows = "$Folder\j9_t8.jsonl"
$MainJsonl = Get-FixedPath 'MAIN_JSONL_SHA256'

$Run = Start-Run -Label 'j9_t8' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_t8' -Workers 8 `
    -Arguments @("$Coupled/run_v5.py", 'j9_t8', '--out', $Rows, '--workers', '8', '--mask', '0xFFFF',
        '--p3-hash-source', $MainJsonl)
Wait-Runs @($Run)
Invoke-IdentityCheck

Invoke-Judge 't8' @("$Coupled/jp3_tjr_judge.py", 't8', '--stored', (Get-FixedPath 'H10_SHA256'),
    '--rerun', $Rows, '--main-jsonl', $MainJsonl, '--out', "$Folder\judge\t8.json") | Out-Null
$Previous = Get-PreviousStepFolder 't8'
Invoke-P51 't8' "$Previous\j9_t8.jsonl" $Rows "$Previous\j9_t8_t4h" "$Folder\j9_t8_t4h"

Complete-Step
