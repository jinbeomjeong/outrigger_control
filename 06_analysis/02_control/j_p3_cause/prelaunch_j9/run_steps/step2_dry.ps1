#Requires -Version 7
# Step (2) 4a-3 5.1 B2 dry check (4a-4 1 .. 3, erratum 1): select (stored files only) -> five
# runs at once (event VBJ / VBH / VBJ0, r79 VBJ / VBH), 1 worker each, mask 0xFFFF -> summarize.
# 4a-5 5.1: != 0 forbids steps 4 .. 7.
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'dry' $Attempt @()
$Selection = "$Folder\selection.json"
$KeysFile = Get-FixedPath 'DRY_KEYS_FILE_SHA256'
$Dry = "$Coupled/jp3_dryrun_evidence.py"

Invoke-Judge 'select' @($Dry, 'select', '--out', $Selection, '--scan-root', $Analysis,
    '--main-jsonl', (Get-FixedPath 'MAIN_JSONL_SHA256'), '--baseline', $BaselineDir,
    '--dg3', (Get-FixedPath 'H6_SHA256'), '--noise', (Get-FixedPath 'NOISE_VB_SHA256'),
    '--keys-file', $KeysFile) | Out-Null

$Runs = @()
foreach ($Setting in @('VBJ', 'VBH', 'VBJ0')) {
    $Out = "$Folder\event_$Setting.jsonl"
    $Runs += Start-Run -Label "event_$Setting" -MaskHex '0xFFFF' -WrapOutput $Out -TaskType 'jp3_dry_event' -Workers 1 `
        -Arguments @($Dry, 'run-event', '--selection', $Selection, '--setting', $Setting, '--out', $Out)
}
foreach ($Setting in @('VBJ', 'VBH')) {
    # the T-JR-12 runner and environment (4a-4 3; jp3_dryrun_evidence.r79_environment)
    $Out = "$Folder\r79_$Setting.json"
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = "$Folder\${Setting}_t4h"
        R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    $Runs += Start-Run -Label "r79_$Setting" -MaskHex '0xFFFF' -WrapOutput $Out -Environment $Environment `
        -TaskType 'jp3_dry_r79' -Workers 1 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', $KeysFile, '--workers', '1', '--affinity', '0xFFFF')
}
Wait-Runs $Runs
Invoke-IdentityCheck

Invoke-Judge 'summarize' @($Dry, 'summarize', '--selection', $Selection, '--out', "$Folder\judge\summary.json",
    '--event', "VBJ=$Folder\event_VBJ.jsonl", "VBH=$Folder\event_VBH.jsonl", "VBJ0=$Folder\event_VBJ0.jsonl",
    '--r79', "VBJ=$Folder\r79_VBJ.json", "VBH=$Folder\r79_VBH.json") | Out-Null
Invoke-RerunMatch 'dry'  # 4a-6 G-4, 4a-7 2: the same evidence values and code as fa997f4c

Complete-Step
