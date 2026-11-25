#Requires -Version 7
# Step 12b_plan (spec v7 6.4, Y7-7): the T-JR-12b selection and plans by jp3_12b_plan.py
# --edition 7 into the step folder's x11\ (seeds 50 .. 53 with the +10 collision rule, arms
# VBKM0 / VBKM). The scan is the edition 6 one (06_analysis, the run worktree's and the main
# checkout's 05_tests, the c92 / c93 key lists) widened by --scan-required: the edition 6 run
# outputs with records B / C / D, the probe 6bfb2560, the pre-seal reproduction b46bdf8f and this
# run's edition 7 outputs (that is why the plan comes after step dg3). The tool prunes the
# edition 7 blind prefixes before it lists anything and names none of them (user decision
# 2026-11-24). A planning tool, not a judge: exit 0 written, 2 not usable, 3 error (its code).
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed7.ps1"

$Folder = Initialize-Ed7Step '12b_plan' $Attempt @('impl_scope', 'l1ref', 'impl_probe', 'confirm', 'j9main', 'sens', 'dg3') `
    @('c92_keys', 'c93_keys')
$PlanDir = "$Folder\x11"
Assert-NewOutput @($PlanDir)
$Arguments = @("$Coupled/jp3_12b_plan.py", '--noise', $NoiseVb, '--scan-root', $Analysis,
    '--scan-extra', "$Worktree\05_tests", '--scan-extra', "$MainRoot\05_tests", '--out-dir', $PlanDir,
    '--edition', '7', '--scan-keys-file', (Get-InputPath 'c92_keys'), '--scan-keys-file', (Get-InputPath 'c93_keys'))
foreach ($Root in $ScanRequiredRoots) { $Arguments += @('--scan-required', $Root) }
$Code = Invoke-Tool 'plan' $Arguments
if ($Code -ne 0) { Stop-Step $Code "jp3_12b_plan.py exit $Code" }
$Selection = "$PlanDir\selection.json"
$StepState.Codes['selection_file'] = $Selection
$StepState.Codes['selection_sha256'] = if ($IsEd7Dry) { 'dry' } else { (Get-FileHash -Algorithm SHA256 -LiteralPath $Selection).Hash.ToLower() }

Complete-Step
