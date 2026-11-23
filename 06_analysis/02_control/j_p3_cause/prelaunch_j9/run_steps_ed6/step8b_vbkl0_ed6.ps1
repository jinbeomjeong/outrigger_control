#Requires -Version 7
# Step 12b_vbkl0 (spec v6 6.4, 4 step 8 order): the VBKL0 arm of T-JR-12b with the rod fault
# plans of ed6_inputs\x11 (seeds 50 .. 53, selection 6687b2dc...).
#   -Phase base   b1 and b2 at once (4 workers each on one P quarter), no judge
#   -Phase b4     only after 12b_decide said needs_b4: the b4 VBKL0 run
#   (b3 is never run: N_opp < 0.9 N is not judgeable, spec 6.4 / erratum 8 2.5)
# No VBKL file exists before the decision (the P-pred allowance is set on VBKL0 b1 / b2 only).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b4')][string]$Phase)
. "$PSScriptRoot\common_ed6.ps1"

$Masks = @('0x000F', '0x00F0')
if ($Phase -eq 'base') {
    $Folder = Initialize-Ed6Step '12b_vbkl0' $Attempt @('l1ref', 'confirm', 'j9main', 'dg3')
    $Blocks = @('b1', 'b2')
} else {
    $Folder = Initialize-Ed6Step '12b_vbkl0_b4' $Attempt @('l1ref', 'confirm', 'j9main', 'dg3', '12b_vbkl0', '12b_decide')
    $Decision = "$(Get-StepFolder '12b_decide')\decision.json"
    $Status = if ($IsEd6Dry) { 'needs_b4' } else { [string](Get-Content -Raw -LiteralPath $Decision | ConvertFrom-Json).status }
    if ($Status -ne 'needs_b4') { Stop-Step 2 "12b_decide status $Status (b4 runs only on needs_b4)" }
    $Blocks = @('b4')
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $X11Selection).Hash.ToLower() -ne (Get-ListedSha $X11Selection)) {
    Stop-Step 2 "$X11Selection is not the fixed list's file"
}
$Runs = @()
for ($Index = 0; $Index -lt $Blocks.Count; $Index++) {
    $Block = $Blocks[$Index]
    $Label = "VBKL0_$Block"
    $Out = "$Folder\$Label.json"
    $RunEstimatesS[$Label] = 3600  # edition 5 VBK0 blocks: 3,550 s at 4 workers
    $Runs += Start-Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out `
        -Environment (Get-R79Environment 'VBKL0' "$Folder\${Label}_t4h" "$X11Folder\${Block}_plan.json") `
        -TaskType 'jp3_ed6_12b_vbkl0' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$X11Folder\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
}
Wait-Runs $Runs
Invoke-IdentityCheck

Complete-Step
