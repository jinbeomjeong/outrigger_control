#Requires -Version 7
# Step (7) T-JR-13 .. T-JR-15 (4a-5 1 and erratum 1): t4h_replay --extend-start tracked_bound
# --extend-start-revision 5 of the stored h10 T4h (426) then the stored H-6 T4h (135), single,
# mask 0xFFFF -> jp3_tjr_judge.py records (--replay 2, --t4h-sums 2, --dg3 VBH / VBJ, --h6,
# --lock-rows Dg-3 VBJ + j9_cases). Needs steps 2, 4a (j9_cases) and 6 (Dg-3).
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'records' $Attempt @('dry', 'cases', 'dg3')
$CasesFolder = Get-StepFolder 'cases'
$Dg3Folder = Get-StepFolder 'dg3'
$Replays = [ordered]@{ h10 = "$ResumeK1\h10_reuse_rerun_t4h"; h6 = "$ResumeK1\h6_dg3_v4on_t4h" }

foreach ($Name in $Replays.Keys) {
    $Out = "$Folder\t4h_replay_$Name.json"
    $Run = Start-Run -Label "t4h_replay_$Name" -MaskHex '0xFFFF' -WrapOutput $Out -TaskType 'jp3_t4h_replay' -Workers 1 `
        -Arguments @("$Coupled/t4h_replay.py", $Out, $Replays[$Name], '--extend-start', 'tracked_bound',
            '--extend-start-revision', '5')
    Wait-Runs @($Run)
}
Invoke-IdentityCheck

Invoke-Judge 'records' @("$Coupled/jp3_tjr_judge.py", 'records',
    '--replay', "$Folder\t4h_replay_h10.json", "$Folder\t4h_replay_h6.json",
    '--t4h-sums', (Get-FixedPath 'H10_T4H_SUMS_SHA256'), (Get-FixedPath 'H6_T4H_SUMS_SHA256'),
    '--dg3', "$Dg3Folder\dg3_VBH.json", "$Dg3Folder\dg3_VBJ.json",
    '--h6', (Get-FixedPath 'H6_SHA256'),
    '--lock-rows', "$Dg3Folder\dg3_VBJ.json", "$CasesFolder\j9_cases.jsonl",
    '--out', "$Folder\judge\records.json") | Out-Null

Complete-Step
