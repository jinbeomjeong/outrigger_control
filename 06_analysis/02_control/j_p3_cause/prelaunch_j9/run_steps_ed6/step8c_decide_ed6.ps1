#Requires -Version 7
# Step 12b_decide (spec v6 6.4): jp3_12b_judge_ed6.py decide on the VBKL0 outputs - b1 / b2 of
# 12b_vbkl0, with -WithB4 also b4 of 12b_vbkl0_b4 (step 12b_decide_b4). The allowance k_allow is
# the P-pred value (n_par 20000 x n_rep 10, default_rng(20261125), b4 case B), never the edition 5
# fixed 7 / 9. No VBKL file is opened. Exit: decide's code - 0 with decided (go to
# step8d_vbkl_ed6.ps1) or needs_b4 (go to step8b_vbkl0_ed6.ps1 -Phase b4); 2 / 3 stop and ask.
param([int]$Attempt = 1, [switch]$WithB4)
. "$PSScriptRoot\common_ed6.ps1"

$Name = if ($WithB4) { '12b_decide_b4' } else { '12b_decide' }
$Requires = @('l1ref', 'confirm', 'j9main', 'dg3', '12b_vbkl0')
if ($WithB4) { $Requires += @('12b_decide', '12b_vbkl0_b4') }
$Folder = Initialize-Ed6Step $Name $Attempt $Requires
$Sources = [ordered]@{ b1 = (Get-StepFolder '12b_vbkl0'); b2 = (Get-StepFolder '12b_vbkl0') }
if ($WithB4) { $Sources['b4'] = Get-StepFolder '12b_vbkl0_b4' }
$Decision = "$Folder\decision.json"
$Arguments = @($Ed6Judge12b, 'decide', '--selection', $X11Selection, '--selection-sha256', (Get-ListedSha $X11Selection),
    '--out', $Decision)
foreach ($Block in $Sources.Keys) {
    $Arguments += @('--vbk0', "$Block=$($Sources[$Block])\VBKL0_$Block.json", '--vbk0-t4h', "$Block=$($Sources[$Block])\VBKL0_${Block}_t4h")
}
Invoke-Judge 'decide' $Arguments | Out-Null
if (-not $IsEd6Dry) {
    $Status = [string](Get-Content -Raw -LiteralPath $Decision | ConvertFrom-Json).status
    $Allowed = if ($WithB4) { @('decided') } else { @('decided', 'needs_b4') }
    if ($Allowed -notcontains $Status) { Stop-Step 2 "decision status $Status" }
    $StepState.Codes['decision_status'] = $Status
    $StepState.Codes['decision_sha256'] = (Get-FileHash -Algorithm SHA256 -LiteralPath $Decision).Hash.ToLower()
}
$StepState.Codes['decision_file'] = Get-RepoPath $Decision

Complete-Step
