#Requires -Version 7
# Step confirm (spec v7 4 step 6, 6.3; unseen rows): 195 lines at the run commit
#   confirm_g1        run_v5 ed7_keys on the sealed confirm_g1_grid171.json (171 lines, VBM;
#                     sha256 684054ab..., also asserted by run_v5.ED7_KEY_FILE_SHA256)
#   ed7_probe_d       ed7_probe.py --part d (D 12 keys x VBM, VBMslow x arm a2 = 24 lines, the D
#                     key file asserted by ed7_probe.D_KEY_FILE_SHA256; user decision 7)
# then the identity check. No judge: the reproduction of the D 24 lines against the fixed table
# and the G1 judgement are made at the judge commit T (5.2). Placement from
# compute-scheduler-expert (-MaskHex, -Workers).
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed7.ps1"

$Folder = Initialize-Ed7Step 'confirm' $Attempt @('impl_scope', 'l1ref', 'impl_t8', 'impl_cases', 'impl_probe') @('g1_keys')
$G1Rows = "$Folder\confirm_g1.jsonl"
$DRows = "$Folder\ed7_probe_d.jsonl"
$RunEstimatesS['confirm_g1'] = [int](171 * 143 / $Workers)
$RunEstimatesS['ed7_probe_d'] = [int](24 * 143 / [Math]::Min(24, $Workers))
# 143 CPU-s per run_v5 line: probe 1bd405c8, 320 lines, 45,649 CPU-s (assumption for these rows)
$Run = Start-Ed7Run -Label 'confirm_g1' -MaskHex $MaskHex -TaskType 'run_v5_ed7_confirm_g1' -Workers $Workers `
    -Outputs @($G1Rows, $DRows) -Arguments @("$Coupled/run_v5.py", 'ed7_keys', '--jobs-file', (Get-InputPath 'g1_keys'),
        '--out', $G1Rows, '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
$DWorkers = [Math]::Min(24, $Workers)
$Run = Start-Ed7Run -Label 'ed7_probe_d' -MaskHex $MaskHex -TaskType 'jp3_ed7_probe_d' -Workers $DWorkers `
    -Outputs @($DRows) -Arguments @("$Coupled/ed7_probe.py", '--part', 'd', '--out', $DRows,
        '--workers', "$DWorkers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck

Complete-Step
