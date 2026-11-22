#Requires -Version 7
# Step (2) dry check of the three families (spec v5 8 4.(2); 4a-3 5.1, 4a-4, 4a-8 3; erratum 1
# 9): the prelaunch selection (fixed list; select ran at the run commit) -> nine runs at once
# (event VBJ / VBH / VBJ0, r79 VBJ / VBH x g6 / g8 / ref), 1 worker each, mask 0xFFFF ->
# summarize --edition 5 (9.2: the rev 6 jp3_* arrays and the events in every r79 T4h) -> 9.3:
# dry5 against 78fd5d2d dry_a1, and from attempt 2 dry5_retry against dry_a<k-1>.
# 4a-5 5.1: != 0 forbids steps 4 .. 7.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'dry' $Attempt @()
$Dry = "$Coupled/jp3_dryrun_evidence.py"
$FamilyKeysFiles = [ordered]@{ g6 = (Get-FixedPath 'DRY_KEYS_FILE_SHA256')
    g8 = (Get-FixedPath 'DRY_KEYS_FILE_SHA256_G8'); ref = (Get-FixedPath 'DRY_KEYS_FILE_SHA256_REF') }

$Runs = @()
foreach ($Setting in @('VBJ', 'VBH', 'VBJ0')) {
    $Out = "$Folder\event_$Setting.jsonl"
    $Runs += Start-Run -Label "event_$Setting" -MaskHex '0xFFFF' -WrapOutput $Out -TaskType 'jp3_dry_event' -Workers 1 `
        -Arguments @($Dry, 'run-event', '--selection', $DrySelection, '--setting', $Setting, '--out', $Out)
}
$R79Arguments = @()
$T4hArguments = @()
foreach ($Setting in @('VBJ', 'VBH')) {
    foreach ($Family in $FamilyKeysFiles.Keys) {
        $Suffix = if ($Family -eq 'g6') { '' } else { "_$Family" }
        $Out = "$Folder\r79_$Setting$Suffix.json"
        $T4h = "$Folder\${Setting}${Suffix}_t4h"
        $Runs += Start-Run -Label "r79_$Setting$Suffix" -MaskHex '0xFFFF' -WrapOutput $Out `
            -Environment (Get-R79Environment $Setting $T4h) -TaskType 'jp3_dry_r79' -Workers 1 `
            -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2',
                '--keys-file', $FamilyKeysFiles[$Family], '--workers', '1', '--affinity', '0xFFFF')
        $Name = if ($Family -eq 'g6') { $Setting } else { "${Setting}:$Family" }
        $R79Arguments += "$Name=$Out"
        $T4hArguments += "$Name=$T4h"
    }
}
Wait-Runs $Runs
Invoke-IdentityCheck

Invoke-Judge 'summarize' (@($Dry, 'summarize', '--selection', $DrySelection, '--edition', '5',
    '--out', "$Folder\judge\summary.json",
    '--event', "VBJ=$Folder\event_VBJ.jsonl", "VBH=$Folder\event_VBH.jsonl", "VBJ0=$Folder\event_VBJ0.jsonl",
    '--r79') + $R79Arguments + @('--r79-t4h') + $T4hArguments) | Out-Null
Invoke-DryMatch 'dry5' "$PreviousRunsRoot\dry_a1"
if ($Attempt -gt 1) { Invoke-DryMatch 'dry5_retry' "$RunsRoot\dry_a$($Attempt - 1)" }

Complete-Step
