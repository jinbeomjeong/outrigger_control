#Requires -Version 7
# Step (4a) case replay A .. E and X11 (spec v5 8 4.(4); erratum 1 1, 2): at once run_v5
# j9_cases (--workers 5), jp3_case_replay.py (C = VBG4, D = VBG6 on ③ rev 6; --workers 2) and
# jp3_x11_replay.py --arm both (LSJ4_X11 on ③ rev 5, the 4a P4-5a arm), mask 0xFFFF ->
# jp3_baseline_compare.py (P4-*) and jp3_case_judge.py x11 (P4-5a, rev 5 identity) -> P5-1
# against the 78fd5d2d rows (cases; case D VBG6 against the 4a VBG5 job; X11 whatever the
# fallbacks, erratum 1 1). Needs step 2. A judge != 0 stops (a 1 makes the step 1).
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'cases' $Attempt @('dry')
$Cases = "$Folder\j9_cases.jsonl"
$CaseCD = "$Folder\cd.jsonl"
$X11 = "$Folder\lsj4_x11.jsonl"

$Runs = @(
    (Start-Run -Label 'j9_cases' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_cases' -Workers 5 `
        -Arguments @("$Coupled/run_v5.py", 'j9_cases', '--out', $Cases, '--workers', '5', '--mask', '0xFFFF')),
    (Start-Run -Label 'case_cd' -MaskHex '0xFFFF' -WrapOutput $CaseCD -TaskType 'jp3_case_replay' -Workers 2 `
        -Arguments @("$Coupled/jp3_case_replay.py", '--out', $CaseCD, '--settings', 'VBG4,VBG6', '--workers', '2',
            '--mask', '0xFFFF')),
    (Start-Run -Label 'x11_both' -MaskHex '0xFFFF' -WrapOutput $X11 -TaskType 'jp3_x11_replay' -Workers 1 `
        -Arguments @("$Coupled/jp3_x11_replay.py", '--out', $X11, '--arm', 'both', '--mask', '0xFFFF'))
)
Wait-Runs $Runs
Invoke-IdentityCheck

$CompareCode = Invoke-Tool 'baseline_compare' @("$Coupled/jp3_baseline_compare.py", $BaselineDir,
    '--new', $Cases, $CaseCD, '--out', "$Folder\judge\baseline_compare.json")
$X11Code = Invoke-Tool 'x11' @("$Coupled/jp3_case_judge.py", 'x11', '--both', $X11, '--baseline', $BaselineDir,
    '--out', "$Folder\judge\x11.json")
$StepCode = Get-StepCode @($CompareCode, $X11Code)
if ($StepCode -ne 0) { Stop-Step $StepCode "baseline_compare exit $CompareCode, x11 exit $X11Code" }

$Previous = Get-PreviousStepFolder 'cases'
Invoke-P51 'j9_cases' "$Previous\j9_cases.jsonl" $Cases "$Previous\j9_cases_t4h" "$Folder\j9_cases_t4h"
Invoke-P51 'case_cd' "$Previous\cd.jsonl" $CaseCD "$Previous\cd_t4h" "$Folder\cd_t4h"
Invoke-P51 'x11' "$Previous\lsj4_x11.jsonl" $X11 "$Previous\lsj4_x11_t4h" "$Folder\lsj4_x11_t4h"

Complete-Step
