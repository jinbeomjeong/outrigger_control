#Requires -Version 7
# Prelaunch step: the P5-2 / P5-4 fixed values (spec v5 5 "구현 뒤, 실행 전에 같은 코드 경로로
# 계산해 봉인 기록에 고정한다", 8 1; erratum 1 1A; prelaunch audit B-2), at the run commit,
# before the fixed list (its two records go into it) and before the c dry check.
#   1. the case replays A .. F once, the same runs as steps (4a) / (4b) without X11: run_v5
#      j9_cases (--workers 5) and jp3_case_replay.py VBG4,VBG6 (--workers 2) at once, then
#      run_v5 j9_case_f (--workers 8); mask 0xFFFF
#   2. jp3_p5_fixed_values.py p52 on the three rows files -> judge\p52.json (P5-2 record: per
#      row the rev 6 counts, the rows files' sha256, the judged key total of the P4-on rev 6
#      rows - E's VBJ / LSJ1 .. 4, F's E branch - and, as records only, the judged key sums of
#      the rev 4 rows (A, C) and the P4-off rev 6 rows (B, D, F-B); erratum 4 4-1); a problem,
#      no rev 6 row or no P4-on rev 6 row stops 2, a P4-on judged key > 0 stops 1
#      (Get-P5FixedStop)
#   3. jp3_p5_fixed_values.py p54 on the stored VBH T4h (78fd5d2d dg3_a1\VBH_t4h, the edition 4a
#      VBH run, VB plant + ③ rev 5; erratum 4 4-1; a fixed list entry) -> judge\p54.json (P5-4
#      record with the 135 files' sha256)
# The step record names the run commit (erratum 4 4-1: computed at the run commit) and the
# erratum 4 4-1 disclosure sentence; -Part list -P5FixedCommit takes another commit's records
# only with a disjoint import closure report.
# Steps (4a) / (4b) compare their rows with p52.json (p52-compare: a rev 6 count differing
# from the fixed one stops). Run order: -Part dry, -Part l1keys, step_l1ref.ps1, this step,
# -Part x11, -Part ckdrop, -Part v0sample, (commit), -Part list, (commit), step0_cdry.ps1.
# Never made again once a case replay, c dry or 12b output exists.
param([int]$Attempt = 1)
. "$PSScriptRoot\common_ed5.ps1"

$Later = @(Get-ChildItem -LiteralPath $RunsRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'cases_a*' -or $_.Name -like 'casef_a*' -or $_.Name -like 'cdry_a*' -or $_.Name -like '12b_*' })
if ($Later.Count) {
    Write-Host "STOP: $($Later[0].FullName) exists (the P5-2 fixed values come before any result)"
    exit 2
}
# the fixed list does not exist yet: the edition 4a step start (commit, tree, 4a fixed inputs)
$Folder = Initialize-Step 'p5fixed' $Attempt @()
$Cases = "$Folder\j9_cases.jsonl"
$CaseCD = "$Folder\cd.jsonl"
$CaseF = "$Folder\j9_case_f.jsonl"
$RunEstimatesS['j9_cases'] = 300; $RunEstimatesS['case_cd'] = 120; $RunEstimatesS['j9_case_f'] = 240

$Runs = @(
    (Start-Run -Label 'j9_cases' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_cases' -Workers 5 `
        -Arguments @("$Coupled/run_v5.py", 'j9_cases', '--out', $Cases, '--workers', '5', '--mask', '0xFFFF')),
    (Start-Run -Label 'case_cd' -MaskHex '0xFFFF' -WrapOutput $CaseCD -TaskType 'jp3_case_replay' -Workers 2 `
        -Arguments @("$Coupled/jp3_case_replay.py", '--out', $CaseCD, '--settings', 'VBG4,VBG6', '--workers', '2',
            '--mask', '0xFFFF'))
)
Wait-Runs $Runs
$Run = Start-Run -Label 'j9_case_f' -MaskHex '0xFFFF' -TaskType 'run_v5_j9_case_f' -Workers 8 `
    -Arguments @("$Coupled/run_v5.py", 'j9_case_f', '--out', $CaseF, '--workers', '8', '--mask', '0xFFFF')
Wait-Runs @($Run)
Invoke-IdentityCheck

# erratum 4 4-1: the fixed values are computed at the run commit (Initialize-Step checked the
# worktree HEAD = $RunCommit and a clean tree); the step record names it and the disclosure
$StepState.Codes['p5fixed_commit'] = $RunCommit
$StepState.Codes['p5fixed_disclosure'] = $P5FixedDisclosure
$P52 = "$Folder\judge\p52.json"
Invoke-Judge 'p52' @("$Coupled/jp3_p5_fixed_values.py", 'p52', '--rows', $Cases, $CaseCD, $CaseF, '--out', $P52) | Out-Null
$P52Stop = Get-P5FixedStop $P52
if ($P52Stop) { Stop-Step $P52Stop.code $P52Stop.reason }
$VbhT4h = "$(Get-PreviousStepFolder 'dg3')\VBH_t4h"
Invoke-Judge 'p54' @("$Coupled/jp3_p5_fixed_values.py", 'p54', '--t4h', $VbhT4h, '--out', "$Folder\judge\p54.json") | Out-Null

Complete-Step
