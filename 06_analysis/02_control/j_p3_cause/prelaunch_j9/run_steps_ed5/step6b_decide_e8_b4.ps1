#Requires -Version 7
# Step 12b_decide_e8_b4 (erratum 8 8-9 "12b 진행" 3; scripts and judge of the tool commit, 8-9
# (f)): after 12b_decide_e8 (status needs_b4) and 12b_vbk0_b4, jp3_12b_judge.py decide in the
# tool checkout on b1 / b2 (12b_vbk0_base_a1, 8-9 (e)) and b4 (12b_vbk0_b4) with the 8-1.3
# expectations of b1 / b2 (8-9 (d); b4 has no fixed value and is recorded only). No
# simulation. Output 12b_decide_e8_b4_a<k>\decision.json. Exit: 0 decided (go to
# step6c_vbk.ps1); 2 not judgeable (e.g. k < 45 after b4) or needs_b4 again (a setting defect,
# 8-9 3); 3 a tool error or a broken precondition.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-E8Step '12b_decide_e8_b4' $Attempt @('dry', 'l1ref', '12b_decide_e8', '12b_vbk0_b4')
$FirstDecision = "$(Get-StepFolder '12b_decide_e8')\decision.json"
$Stop = Get-E8DecisionStop $FirstDecision @('needs_b4')
if ($Stop) { Stop-Step $Stop.code $Stop.reason }
$BaseFolder = Get-E8BaseVbk0Folder
$B4Folder = Get-StepFolder '12b_vbk0_b4'
$Decision = "$Folder\decision.json"
Invoke-E8Decide $Decision @{ b1 = $BaseFolder; b2 = $BaseFolder; b4 = $B4Folder }
Assert-E8Decision $Decision @('decided')

Complete-Step
