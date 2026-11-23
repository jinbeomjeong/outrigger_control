#Requires -Version 7
# Step (6b) T-JR-12b VBK0 (spec v5 6.3, 8 4.(6)) in the erratum 8 form (jp3_remedy_spec_v5_erratum8.md
# 8-9 "12b 진행" 1 / 3 and (f), sealed cd2de978; the script of the tool commit, the simulation at the
# run commit in ed5-run5). The decisions are separate steps now (step6b_decide_e8.ps1,
# step6b_decide_e8_b4.ps1); this script runs one VBK0 block and no judge command.
#   -Phase base   ran once at the run commit (12b_vbk0_base_a1, stopped 2 by the A/A floor of the
#                 old decide; taken again by 8-9 (d) / (e), never run again, 8-1.3): exit 2
#   -Phase b3     no allowance (8-2, 8-8.1: b3 is never run): exit 2
#   -Phase b4     step 12b_vbk0_b4, only after 12b_decide_e8 said needs_b4: the b4 (seed 43) VBK0
#                 run, 4 workers on one P quarter, with the run condition of the b1 / b2 VBK0 runs
#                 of 12b_vbk0_base_a1 (8-9 (c): environment and --workers before the run, the
#                 identity record after it). Output 12b_vbk0_b4_a<k>\VBK0_b4.json, VBK0_b4_t4h\.
# Exit: 0 done (go to step6b_decide_e8_b4.ps1); 2 base / b3, the decision is not needs_b4 or a
# run condition differs; 3 a run failed or a broken precondition.
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b3', 'b4')][string]$Phase)
if ($Phase -ne 'b4') {
    # nothing starts and nothing is written (no step marker)
    Write-Host "STOP: step6b_vbk0.ps1 -Phase ${Phase} is replaced by erratum 8 8-9 (base: never run again; b3: no allowance); only -Phase b4 runs"
    exit 2
}
. "$PSScriptRoot\common_ed5.ps1"

$Block = $Phase
$Folder = Initialize-E8Step "12b_vbk0_$Block" $Attempt @('dry', 'l1ref', '12b_decide_e8')
$FirstDecision = "$(Get-StepFolder '12b_decide_e8')\decision.json"
$Stop = Get-E8DecisionStop $FirstDecision @('needs_b4')
if ($Stop) { Stop-Step $Stop.code $Stop.reason }
$BaseFolder = Get-E8BaseVbk0Folder

$Label = "VBK0_$Block"
$Out = "$Folder\$Label.json"
$Environment = Get-R79Environment 'VBK0' "$Folder\${Label}_t4h" "$X11Folder\${Block}_plan.json"
Assert-E8RunCondition $BaseFolder 'VBK0' $Environment $E8RequiredWorkers
$RunEstimatesS[$Label] = 1900
$Run = Start-Run -Label $Label -MaskHex $E8RunMasks[0] -WrapOutput $Out -Environment $Environment `
    -TaskType 'jp3_12b_vbk0' -Workers $E8RequiredWorkers -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
        '--levels', 'L2', '--keys-file', "$X11Folder\${Block}_keys.txt", '--workers', "$E8RequiredWorkers",
        '--affinity', $E8RunMasks[0])
Wait-Runs @($Run)
Invoke-IdentityCheck
Assert-E8RunIdentity $BaseFolder "$Folder\$Label.identity.json"

Complete-Step
