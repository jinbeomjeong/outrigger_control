#Requires -Version 7
# Step (4a) case replay A .. E and X11 (spec 5.3, 13.1, 13.3; addenda 4a-1, 4a-2): at once
#   run_v5 j9_cases (15 runs, --workers 5), jp3_case_replay.py (C, D; --workers 2),
#   jp3_x11_replay.py --arm both (LSJ4_X11), all mask 0xFFFF (8 workers on 16 P threads)
# -> jp3_baseline_compare.py (P4-1 .. P4-4, P4-9) and jp3_case_judge.py x11 (P4-5a).
# Needs step 2 (4a-5 5.1). Both judges run; any != 0 stops (code 1 when either failed, else the
# larger code; re-audit N-2).
param([int]$Attempt = 1)
. "$PSScriptRoot\common.ps1"

$Folder = Initialize-Step 'cases' $Attempt @('dry')
$Cases = "$Folder\j9_cases.jsonl"
$CaseCD = "$Folder\cd.jsonl"
$X11 = "$Folder\lsj4_x11.jsonl"

$Runs = @(
    (Start-Run -Label 'j9_cases' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_cases' -Workers 5 `
        -Arguments @("$Coupled/run_v5.py", 'j9_cases', '--out', $Cases, '--workers', '5', '--mask', '0xFFFF')),
    (Start-Run -Label 'case_cd' -MaskHex '0xFFFF' -WrapOutput $CaseCD -TaskType 'jp3_case_replay' -Workers 2 `
        -Arguments @("$Coupled/jp3_case_replay.py", '--out', $CaseCD, '--workers', '2', '--mask', '0xFFFF')),
    (Start-Run -Label 'x11_both' -MaskHex '0xFFFF' -WrapOutput $X11 -TaskType 'jp3_x11_replay' -Workers 1 `
        -Arguments @("$Coupled/jp3_x11_replay.py", '--out', $X11, '--arm', 'both', '--mask', '0xFFFF'))
)
Wait-Runs $Runs
Invoke-IdentityCheck

$CompareCode = Invoke-Tool 'baseline_compare' @("$Coupled/jp3_baseline_compare.py", $BaselineDir,
    '--new', $Cases, $CaseCD, '--out', "$Folder\judge\baseline_compare.json")
$X11Code = Invoke-Tool 'x11' @("$Coupled/jp3_case_judge.py", 'x11', '--both', $X11, '--baseline', $BaselineDir,
    '--out', "$Folder\judge\x11.json")
$StepCode = Get-StepCode @($CompareCode, $X11Code)  # re-audit N-2: a 1 makes the step 1
if ($StepCode -ne 0) { Stop-Step $StepCode "baseline_compare exit $CompareCode, x11 exit $X11Code" }
Invoke-RerunMatch 'x11'  # 4a-6 G-4: the same LSJ4_X11 hash, FL read and x11 code as b51ed6e1

Complete-Step
