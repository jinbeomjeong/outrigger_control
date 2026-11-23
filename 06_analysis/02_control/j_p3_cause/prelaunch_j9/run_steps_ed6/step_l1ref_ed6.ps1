#Requires -Version 7
# Prelaunch step l1ref (erratum 1 1-2, spec v6 6.4 / 6.5): the four L1 reference runs at the run
# commit, before the fixed list (their outputs go into it by --add) and before any 12a / 12b
# output (never made again afterwards):
#   L1_VBL0 / L1_VBL    12b grade references, the 167 keys of ed5_inputs\l1_keys_12b.txt
#   L1a_VBL0 / L1a_VBL  T-JR-12a references, the 102 keys of l1_keys_d3c6c57e.json
# R79_ROD_MODEL=plant_truth, 4 workers each on one P quarter. No judge tool (grade-judge and
# dg3-judge check these files later). Exit 0 done, 2 a later output exists, 3 a failed run or a
# broken precondition.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed6.ps1"

$Later = @(Get-ChildItem -LiteralPath $RunsRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like '12b_*' -or $_.Name -like 'dg3_*' })
if ($Later.Count) {
    Write-Host "STOP: $($Later[0].FullName) exists (erratum 1 1-2: the L1 references are not made again)"
    exit 2
}
$Folder = Initialize-Ed6Step 'l1ref' $Attempt @() -BeforeList
$Masks = @('0x000F', '0x00F0', '0x0F00', '0xF000')
$Estimates = @{ L1_VBL0 = 2250; L1_VBL = 2250; L1a_VBL0 = 1450; L1a_VBL = 1450 }
# wall [s] of the edition 5 L1 runs at 4 workers (l1ref_a1 2,198 / 2,233 s; dg3_a1 l1 1,324 / 1,423 s)

$Runs = @()
$Index = 0
foreach ($Label in $L1Labels.Keys) {
    $Setting, $Keys = $L1Labels[$Label]
    if (-not (Test-Path -LiteralPath $Keys)) { Stop-Step 3 "$Keys missing" }
    $Out = "$Folder\$Label.json"
    $RunEstimatesS[$Label] = $Estimates[$Label]
    $Runs += Start-Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out `
        -Environment (Get-R79Environment $Setting "$Folder\${Label}_t4h") -TaskType 'jp3_ed6_l1ref' -Workers 4 `
        -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out, '--levels', 'L1', '--keys-file', $Keys,
            '--workers', '4', '--affinity', $Masks[$Index])
    $Index++
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
