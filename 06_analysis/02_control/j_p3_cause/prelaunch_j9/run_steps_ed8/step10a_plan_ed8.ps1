#Requires -Version 7
# Step 12b_plan (spec v8 8): the T-JR-12b selection and plans by jp3_12b_plan.py --edition 8 into
# the step folder's x11\ (seeds 50 .. 53 with the +10 rule, arms VBKN0 / VBKN). --scan-required:
# the edition 6 / 7 outputs, the P8-14 and P8-16 pre-run outputs and this run's edition 8 outputs
# (spec 8 scan range). The tool prunes the blind prefixes before it lists anything. A planning
# tool, not a judge: exit 0 written, 2 not usable, 3 error.
param([int]$Attempt = 1, [string]$S8cRules = '', [string]$S8cSha256 = '')
. "$PSScriptRoot\common_ed8.ps1"

$Folder = Initialize-Ed8Step '12b_plan' $Attempt @('impl_scope', 'l1ref', 'census', 'heldout', 'dg3') `
    @('c92_keys', 'c93_keys')
Assert-S8cSeal $S8cRules $S8cSha256
$PlanDir = "$Folder\x11"
Assert-NewOutput @($PlanDir)
$Arguments = @("$Coupled/jp3_12b_plan.py", '--noise', $NoiseVb, '--scan-root', $Analysis,
    '--scan-extra', "$Worktree\05_tests", '--scan-extra', "$MainRoot\05_tests", '--out-dir', $PlanDir,
    '--edition', '8', '--scan-keys-file', (Get-InputPath 'c92_keys'), '--scan-keys-file', (Get-InputPath 'c93_keys'))
foreach ($Root in $ScanRequiredRoots) { $Arguments += @('--scan-required', $Root) }
$Code = Invoke-Tool 'plan' $Arguments
if ($Code -ne 0) { Stop-Step $Code "jp3_12b_plan.py exit $Code" }
$Selection = "$PlanDir\selection.json"
$StepState.Codes['selection_file'] = $Selection
$StepState.Codes['selection_sha256'] = if ($IsEd8Dry) { 'dry' } else { (Get-FileHash -Algorithm SHA256 -LiteralPath $Selection).Hash.ToLower() }

Complete-Step
