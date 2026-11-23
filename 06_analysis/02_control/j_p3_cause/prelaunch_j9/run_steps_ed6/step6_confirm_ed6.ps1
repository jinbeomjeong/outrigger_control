#Requires -Version 7
# Step confirm (spec v6 4 step 6, 6.3; unseen rows): run_v5 batch ed6_keys on the sealed key
# files confirm_a_keys_v2.json (216 lines, the four sensitivity settings) and
# confirm_b_grid192.json (192 lines, VBL), then the identity check and the judges
#   jp3_ed6_judge.py sens --keys confirm_a_keys_v2.json   (cluster rule k = 2, J7 exception)
#   jp3_ed6_judge.py grid --keys confirm_b_grid192.json   (opportunity 174 allowed 1, FAULT 0)
# Each judge: 0 goes on, 1 failed / 2 / 3 stop (a confirmation failure is never fixed in this
# edition, 6.3). The placement (-MaskHex, -Workers) comes from compute-scheduler-expert.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed6.ps1"

$Folder = Initialize-Ed6Step 'confirm' $Attempt @('l1ref')
foreach ($File in @($ConfirmAKeys, $GridKeys)) {
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $File).Hash.ToLower() -ne (Get-ListedSha $File)) {
        Stop-Step 2 "$File is not the fixed list's file"
    }
}
$Parts = [ordered]@{ confirm_a = $ConfirmAKeys; confirm_b = $GridKeys }
$RunEstimatesS['confirm_a'] = [int](216 * 143 / $Workers)
$RunEstimatesS['confirm_b'] = [int](192 * 143 / $Workers)
# 143 CPU-s per run_v5 line: probe 1bd405c8, 320 lines, 45,649 CPU-s (assumption for these rows)
foreach ($Part in $Parts.Keys) {
    $Run = Start-Run -Label $Part -MaskHex $MaskHex -TaskType "run_v5_ed6_$Part" -Workers $Workers `
        -Arguments @("$Coupled/run_v5.py", 'ed6_keys', '--jobs-file', $Parts[$Part], '--out', "$Folder\$Part.jsonl",
            '--workers', "$Workers", '--mask', $MaskHex)
    Wait-Runs @($Run)
}
Invoke-IdentityCheck
Invoke-L1InputGuard @("$Folder\confirm_a.jsonl", "$Folder\confirm_b.jsonl", $V0Rows)
Invoke-Judge 'confirm_a_judge' @($Ed6Judge, 'sens', '--keys', $ConfirmAKeys, '--rows', "$Folder\confirm_a.jsonl",
    '--v0', $V0Rows, '--v0-sha256', $V0Sha, '--out', "$Folder\judge\confirm_a_judge.json") | Out-Null
Invoke-Judge 'confirm_b_judge' @($Ed6Judge, 'grid', '--keys', $GridKeys, '--rows', "$Folder\confirm_b.jsonl",
    '--grid-root', $MainRoot, '--out', "$Folder\judge\confirm_b_judge.json") | Out-Null

Complete-Step
