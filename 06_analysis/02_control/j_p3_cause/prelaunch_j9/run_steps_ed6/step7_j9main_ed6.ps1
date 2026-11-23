#Requires -Version 7
# Step j9main (spec v6 4 step 7, 6.2): run_v5 batch ed6_j9_main (VBL 100 + LSL1 .. LSL4 x 72 =
# 388 lines) and ed6_keys on sens_keys_v2.json (184 lines, the four sensitivity settings), the
# identity check, the L1 input guard, then
#   jp3_ed6_judge.py j9main --edition 6   (readings (1) .. (3), J-P3 judged rows 200)
#   jp3_ed6_judge.py sens --keys sens_keys_v2.json   (probe-seen 32 units stop, cluster k = 2,
#                                                     J-P3 judged rows 104)
# Each judge: 0 goes on, 1 / 2 / 3 stop. Needs the confirm step. Placement from
# compute-scheduler-expert (-MaskHex, -Workers).
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed6.ps1"

$Folder = Initialize-Ed6Step 'j9main' $Attempt @('l1ref', 'confirm')
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $SensKeys).Hash.ToLower() -ne (Get-ListedSha $SensKeys)) {
    Stop-Step 2 "$SensKeys is not the fixed list's file"
}
$RunEstimatesS['j9_main'] = [int](388 * 143 / $Workers)
$RunEstimatesS['sens'] = [int](184 * 143 / $Workers)
$Run = Start-Run -Label 'j9_main' -MaskHex $MaskHex -TaskType 'run_v5_ed6_j9_main' -Workers $Workers `
    -Arguments @("$Coupled/run_v5.py", 'ed6_j9_main', '--out', "$Folder\j9_main.jsonl", '--workers', "$Workers",
        '--mask', $MaskHex)
Wait-Runs @($Run)
$Run = Start-Run -Label 'sens' -MaskHex $MaskHex -TaskType 'run_v5_ed6_sens' -Workers $Workers `
    -Arguments @("$Coupled/run_v5.py", 'ed6_keys', '--jobs-file', $SensKeys, '--out', "$Folder\sens.jsonl",
        '--workers', "$Workers", '--mask', $MaskHex)
Wait-Runs @($Run)
Invoke-IdentityCheck
Invoke-L1InputGuard @("$Folder\j9_main.jsonl", "$Folder\sens.jsonl", $V0Rows)
Invoke-Judge 'j9main_judge' @($Ed6Judge, 'j9main', '--edition', '6', '--rows', "$Folder\j9_main.jsonl",
    '--v0', $V0Rows, '--v0-sha256', $V0Sha, '--out', "$Folder\judge\j9main_judge.json") | Out-Null
Invoke-Judge 'sens_judge' @($Ed6Judge, 'sens', '--keys', $SensKeys, '--rows', "$Folder\sens.jsonl",
    '--v0', $V0Rows, '--v0-sha256', $V0Sha, '--out', "$Folder\judge\sens_judge.json") | Out-Null

Complete-Step
