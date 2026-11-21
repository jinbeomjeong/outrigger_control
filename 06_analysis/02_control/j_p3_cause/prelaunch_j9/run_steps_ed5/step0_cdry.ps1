#Requires -Version 7
# Step (0) c dry check (spec v5 6.3.10, 8 2): the dry plan of X-11 (seeds 90 / 91, 160 pairs,
# outside the judged set) under VBK0 and VBK at once, 4 runs x 4 workers on the P threads ->
# jp3_12b_judge.py dry-c (c = share of opportunity pairs whose commands changed; a record).
# c >= 0.5 is the main session's stop and question (6.3.10); this step only writes c.
# Needs prelaunch_ed5.ps1 -Part x11 (run once, just before this step) and the fixed list.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'cdry' $Attempt @()
$Plan = "$X11Folder\c90_91_plan.json"
$Placement = [ordered]@{ 'VBK0_c90' = '0x000F'; 'VBK0_c91' = '0x00F0'; 'VBK_c90' = '0x0F00'; 'VBK_c91' = '0xF000' }
$RunEstimatesS['VBK0_c90'] = 900; $RunEstimatesS['VBK0_c91'] = 900
$RunEstimatesS['VBK_c90'] = 900; $RunEstimatesS['VBK_c91'] = 900

$Runs = @()
foreach ($Label in $Placement.Keys) {
    $Setting, $Run = $Label -split '_', 2
    $Out = "$Folder\$Label.json"
    $Runs += Start-Run -Label $Label -MaskHex $Placement[$Label] -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Label}_t4h" $Plan) -TaskType 'jp3_12b_cdry' -Workers 4 `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L2',
            '--keys-file', "$X11Folder\${Run}_keys.txt", '--workers', '4', '--affinity', $Placement[$Label])
}
Wait-Runs $Runs
Invoke-IdentityCheck

$Arguments = @("$Coupled/jp3_12b_judge.py", 'dry-c', '--selection', $X11Selection, '--selection-sha256', (Get-X11Sha),
    '--out', "$Folder\judge\dry_c.json")
foreach ($Arm in @('VBK0', 'VBK')) {
    $Lower = $Arm.ToLower()
    foreach ($Run in @('c90', 'c91')) {
        $Arguments += @("--$Lower", "$Run=$Folder\${Arm}_$Run.json", "--$Lower-t4h", "$Run=$Folder\${Arm}_${Run}_t4h")
    }
}
Invoke-Judge 'dry_c' $Arguments | Out-Null

Complete-Step
