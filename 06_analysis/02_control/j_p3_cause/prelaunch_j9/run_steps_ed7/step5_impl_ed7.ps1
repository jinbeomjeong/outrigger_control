#Requires -Version 7
# Step 5, implementation checks at the run commit C (spec v7 4 step 5, 5.1). Four parts, each its
# own step with its .done marker; the lines are run here, judged at the judge commit T (4 step
# 5a: P7-1 / P7-2 / P7-3 / P7-9 are not judgeable before T and its audit):
#   -Part scope  P7-10 evidence, no run: git diff of b46bdf8f and C (--stat, --name-only, the
#                03_src and run_v5.py diffs) into the step folder; the check itself is
#                Get-ScopeProblem at every step start (common_ed7.ps1)
#   -Part t8     P7-1: run_v5 ed7_t8 (22 jobs x VBM, VBM0 = 44 lines, --p3-hash-source = the
#                stored v5/main.jsonl)
#   -Part cases  P7-2: run_v5 ed7_cases (cases E and F x VBM, LSM1 .. LSM4 = 10 lines)
#   -Part probe  P7-3 / P7-9: ed7_probe.py --arms a2 --part all (15 keys x 6 plants + D 12 keys x
#                VBM, VBMslow = 114 lines; the fixed table's 40 units and D 24 lines among them)
# Order: scope, (step_l1ref_ed7.ps1), t8, cases, probe. P7-0 / P7-6 are judged by the unit suite
# (P7-4, full_suite_ed7.ps1). Placement from compute-scheduler-expert (-MaskHex, -Workers).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('scope', 't8', 'cases', 'probe')][string]$Part,
    [string]$MaskHex = '', [int]$Workers = 0)
. "$PSScriptRoot\common_ed7.ps1"

$Requires = switch ($Part) {
    'scope' { @() }
    't8' { @('impl_scope', 'l1ref') }
    'cases' { @('impl_scope', 'l1ref', 'impl_t8') }
    'probe' { @('impl_scope', 'l1ref', 'impl_t8', 'impl_cases') }
}
if ($Part -ne 'scope' -and (-not $MaskHex -or $Workers -lt 1)) { Exit-Ed7 3 "-Part $Part needs -MaskHex and -Workers" }
$Folder = Initialize-Ed7Step "impl_$Part" $Attempt $Requires

function Write-GitText([string]$Name, [string[]]$GitArguments) {
    # one git output into the step folder (never overwritten)
    $Path = "$Folder\$Name"
    Assert-NewOutput @($Path)
    $Lines = @(& git -C $Worktree @GitArguments)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 "git $($GitArguments -join ' ') failed" }
    [IO.File]::WriteAllText($Path, ($Lines -join "`n") + "`n")
    $StepState.Codes["evidence:$Name"] = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
}

switch ($Part) {
    'scope' {
        Write-GitText 'diff_name_only.txt' @('diff', '--name-only', $ImplCommit, $RunCommit)
        Write-GitText 'diff_stat.txt' @('diff', '--stat', $ImplCommit, $RunCommit)
        Write-GitText 'diff_03_src.txt' @('diff', $ImplCommit, $RunCommit, '--', '03_src')
        Write-GitText 'diff_run_v5.txt' @('diff', $ImplCommit, $RunCommit, '--', "$Coupled/run_v5.py")
    }
    't8' {
        $Rows = "$Folder\ed7_t8.jsonl"
        $RunEstimatesS['ed7_t8'] = [int](44 * 143 / $Workers)
        $Run = Start-Ed7Run -Label 'ed7_t8' -MaskHex $MaskHex -TaskType 'run_v5_ed7_t8' -Workers $Workers `
            -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed7_t8', '--p3-hash-source', $V0Rows,
                '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
        Wait-Runs @($Run)
    }
    'cases' {
        $Rows = "$Folder\ed7_cases.jsonl"
        $CaseWorkers = [Math]::Min(10, $Workers)
        $RunEstimatesS['ed7_cases'] = [int](10 * 143 / $CaseWorkers)
        $Run = Start-Ed7Run -Label 'ed7_cases' -MaskHex $MaskHex -TaskType 'run_v5_ed7_cases' -Workers $CaseWorkers `
            -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed7_cases', '--out', $Rows,
                '--workers', "$CaseWorkers", '--mask', $MaskHex)
        Wait-Runs @($Run)
    }
    'probe' {
        $Rows = "$Folder\ed7_probe_a2.jsonl"
        $RunEstimatesS['probe'] = [int](114 * 143 / $Workers)
        # ed7_probe.py writes its own identity record and progress file (no -WrapOutput)
        $Run = Start-Ed7Run -Label 'probe' -MaskHex $MaskHex -TaskType 'jp3_ed7_probe' -Workers $Workers `
            -Outputs @($Rows) -Arguments @("$Coupled/ed7_probe.py", '--out', $Rows, '--arms', 'a2',
                '--part', 'all', '--workers', "$Workers", '--mask', $MaskHex)
        Wait-Runs @($Run)
    }
}
if ($Part -ne 'scope') { Invoke-IdentityCheck }

Complete-Step
