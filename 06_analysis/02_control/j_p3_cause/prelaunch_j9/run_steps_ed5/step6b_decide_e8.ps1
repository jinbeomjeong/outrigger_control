#Requires -Version 7
# Step 12b_decide_e8 (erratum 8 8-9 "12b 진행" 2; scripts and judge of the tool commit, 8-9 (f)):
# jp3_12b_judge.py decide (8-8.1) in the tool checkout on the b1 / b2 VBK0 outputs of
# 12b_vbk0_base_a1 - the run commit's step that stopped 2 (8-9 (e): taken only through the 8-9
# (d) check, which the tool does with the 8-1.3 expected run file sha256 and T4h digests of
# common_ed5.ps1). No simulation; no VBK file. Output 12b_decide_e8_a<k>\decision.json (_a<k>
# only for a retry of this step, 4a-5 5.2). Exit: decide's code - 0 with the status decided
# (go to step6c_vbk.ps1) or needs_b4 (go to step6b_vbk0.ps1 -Phase b4); 2 not judgeable (a differing
# or missing VBK0 input, b3 needed, ...: stop and ask); 3 a tool error or a broken precondition.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-E8Step '12b_decide_e8' $Attempt @('dry', 'l1ref')
$BaseFolder = Get-E8BaseVbk0Folder
$Decision = "$Folder\decision.json"
Invoke-E8Decide $Decision @{ b1 = $BaseFolder; b2 = $BaseFolder }
Assert-E8Decision $Decision @('decided', 'needs_b4')

Complete-Step
