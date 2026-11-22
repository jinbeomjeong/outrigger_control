#Requires -Version 7
# Step (0) c dry check (spec v5 6.3.10, 8 2): the dry plans of X-11 (seeds 92 / 93 from erratum
# 6 6-3; ae9d0b2d ran 90 / 91), one plan
# and key file per seed, 160 pairs, outside the judged set) under VBK0 and VBK at once, 4 runs
# x 4 workers on the P threads ->
# jp3_12b_judge.py dry-c (c = share of opportunity pairs whose commands changed; a record).
# c >= 0.5 is the main session's stop and question (6.3.10); this step only writes c.
# Needs prelaunch_ed5.ps1 -Part x11 (run once, just before this step) and the fixed list.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'cdry' $Attempt @()
# prelaunch audit B-1 (a): each run takes its own seed's plan and key file (c92 / c93), so the
# runner's X-10 guard sees plan keys = job keys; erratum 4 4-2: the two plans together are the
# 160 pairs, 20 per cell (X-11's selection.json dry.union_check, recorded here; both plans are
# fixed list entries through the selection)
$Dry = (Get-Content -Raw -LiteralPath $X11Selection | ConvertFrom-Json).dry
$Union = $Dry.PSObject.Properties['union_check']
if (-not $Union -or $Union.Value.ok -ne $true) { Stop-Step 2 'selection.json dry.union_check missing or not ok (erratum 4 4-2)' }
$StepState.Codes['dry_union_check'] = "pairs $($Union.Value.pairs), cells $($Union.Value.cells), ok"
$DryRuns = @('c92', 'c93')  # jp3_12b_plan.DRY_SEEDS / jp3_12b_judge.DRY_RUNS
$Placement = [ordered]@{ 'VBK0_c92' = '0x000F'; 'VBK0_c93' = '0x00F0'; 'VBK_c92' = '0x0F00'; 'VBK_c93' = '0xF000' }
$RunEstimatesS['VBK0_c92'] = 900; $RunEstimatesS['VBK0_c93'] = 900
$RunEstimatesS['VBK_c92'] = 900; $RunEstimatesS['VBK_c93'] = 900

$Runs = @()
foreach ($Label in $Placement.Keys) {
    $Setting, $Run = $Label -split '_', 2
    $Out = "$Folder\$Label.json"
    $Runs += Start-Run -Label $Label -MaskHex $Placement[$Label] -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Label}_t4h" "$X11Folder\${Run}_plan.json") -TaskType 'jp3_12b_cdry' -Workers 4 `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2',
            '--keys-file', "$X11Folder\${Run}_keys.txt", '--workers', '4', '--affinity', $Placement[$Label])
}
Wait-Runs $Runs
Invoke-IdentityCheck

$Arguments = @("$Coupled/jp3_12b_judge.py", 'dry-c', '--selection', $X11Selection, '--selection-sha256', (Get-X11Sha),
    '--out', "$Folder\judge\dry_c.json")
foreach ($Arm in @('VBK0', 'VBK')) {
    $Lower = $Arm.ToLower()
    foreach ($Run in $DryRuns) {
        $Arguments += @("--$Lower", "$Run=$Folder\${Arm}_$Run.json", "--$Lower-t4h", "$Run=$Folder\${Arm}_${Run}_t4h")
    }
}
Invoke-Judge 'dry_c' $Arguments | Out-Null

Complete-Step
