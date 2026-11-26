#Requires -Version 7
# Step 4, implementation checks at the run commit C8 (spec v8 4 step 4, 11.1, 12). Each part is
# its own step with its .done marker; the lines are run here and judged at T8 (not judgeable
# before T8 and its audit):
#   -Part scope  P8-10 evidence, no run: git diff of the implementation commit and C8
#   -Part p80    P8-0: ed7_probe.py --arms a2 --part all (114 lines; T8 compares them with
#                j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl)
#   -Part p816   P8-16 (time point 2): ed8_probe --part p816 --arms B_impl,L2_impl (54 lines,
#                the P8-14 r79 plan; T8: p816_compare against the P8-14 raw/runs.jsonl)
#   -Part p85    P8-5: ed8_probe --part p816 --plants M,LSM4,Mslow --arms a8,a8_psw_off (46)
#   -Part p88    P8-8: ed8_probe --part p816 --plants M,LSM4,Mslow --arms a8,a8_h3_off (46)
#   -Part p815   P8-15: ed8_probe --part p816 --arms a8,a8_l2_off (54, the KM0 r79 rows too)
#   -Part t8     P8-1: run_v5 ed8_t8 (44, --p3-hash-source = the stored v5/main.jsonl)
#   -Part cases  P8-2: run_v5 ed8_cases (10)
# Order: scope, (step_l1ref_ed8.ps1), p80, p816, p85, p88, p815, t8, cases. P8-4 (the unit
# suite) is full_suite_ed8.ps1, P8-6 a test of that suite. Placement from compute-scheduler-expert.
param([int]$Attempt = 1,
    [Parameter(Mandatory)][ValidateSet('scope', 'p80', 'p816', 'p85', 'p88', 'p815', 't8', 'cases')][string]$Part,
    [string]$MaskHex = '', [int]$Workers = 0)
. "$PSScriptRoot\common_ed8.ps1"

$Order = @('p80', 'p816', 'p85', 'p88', 'p815', 't8', 'cases')
$Requires = if ($Part -eq 'scope') { @() } else {
    @('impl_scope', 'l1ref') + @($Order[0..([Array]::IndexOf($Order, $Part))] | Select-Object -SkipLast 1 |
            ForEach-Object { "impl_$_" })
}
if ($Part -ne 'scope' -and (-not $MaskHex -or $Workers -lt 1)) { Exit-Ed8 3 "-Part $Part needs -MaskHex and -Workers" }
$Inputs = switch ($Part) {
    'p80' { @('p80_repro') }
    { $_ -in @('p816', 'p815') } { @('p814_plan', 'p814_runs') }
    default { @() }
}
$Folder = Initialize-Ed8Step "impl_$Part" $Attempt $Requires $Inputs

function Write-GitText([string]$Name, [string[]]$GitArguments) {
    $Path = "$Folder\$Name"
    Assert-NewOutput @($Path)
    $Lines = @(& git -C $Worktree @GitArguments)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 "git $($GitArguments -join ' ') failed" }
    [IO.File]::WriteAllText($Path, ($Lines -join "`n") + "`n")
    $StepState.Codes["evidence:$Name"] = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
}

function Start-ProbePart([string]$Label, [string[]]$ProbeArguments, [int]$Lines) {
    # one ed8_probe run of part p816 (conda run, the P8-14 call)
    $Rows = "$Folder\$Label.jsonl"
    $RunEstimatesS[$Label] = [int]($Lines * 143 / $Workers)
    return Start-Ed8CondaRun -Label $Label -MaskHex $MaskHex -TaskType "jp3_ed8_$Label" -Workers $Workers `
        -Outputs @($Rows, "$Folder\${Label}_t4h") -Arguments (@("$Coupled/ed8_probe.py", '--out', $Rows,
            '--part', 'p816') + $ProbeArguments + @('--workers', "$Workers", '--mask', $MaskHex))
}

$Plan = Get-InputPath 'p814_plan'
switch ($Part) {
    'scope' {
        Write-GitText 'diff_name_only.txt' @('diff', '--name-only', $ImplCommit, $RunCommit)
        Write-GitText 'diff_stat.txt' @('diff', '--stat', $ImplCommit, $RunCommit)
        Write-GitText 'diff_run_v5.txt' @('diff', $ImplCommit, $RunCommit, '--', "$Coupled/run_v5.py")
    }
    'p80' {
        $Rows = "$Folder\ed7_probe_a2.jsonl"
        $RunEstimatesS['p80'] = [int](114 * 143 / $Workers)
        $Run = Start-Ed8Run -Label 'p80' -MaskHex $MaskHex -TaskType 'jp3_ed8_p80' -Workers $Workers `
            -Outputs @($Rows, "$Folder\ed7_probe_a2_t4h") -Arguments @("$Coupled/ed7_probe.py", '--out', $Rows,
                '--arms', 'a2', '--part', 'all', '--workers', "$Workers", '--mask', $MaskHex)
        Wait-Runs @($Run)
    }
    'p816' { Wait-Runs @(Start-ProbePart 'p816' @('--arms', 'B_impl,L2_impl', '--r79-plan', $Plan) 54) }
    'p85' { Wait-Runs @(Start-ProbePart 'p85' @('--plants', 'M,LSM4,Mslow', '--arms', 'a8,a8_psw_off') 46) }
    'p88' { Wait-Runs @(Start-ProbePart 'p88' @('--plants', 'M,LSM4,Mslow', '--arms', 'a8,a8_h3_off') 46) }
    'p815' { Wait-Runs @(Start-ProbePart 'p815' @('--arms', 'a8,a8_l2_off', '--r79-plan', $Plan) 54) }
    't8' {
        $Rows = "$Folder\ed8_t8.jsonl"
        $RunEstimatesS['ed8_t8'] = [int](44 * 143 / $Workers)
        $Run = Start-Ed8Run -Label 'ed8_t8' -MaskHex $MaskHex -TaskType 'run_v5_ed8_t8' -Workers $Workers `
            -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed8_t8', '--p3-hash-source', $V0Rows,
                '--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
        Wait-Runs @($Run)
    }
    'cases' {
        $Rows = "$Folder\ed8_cases.jsonl"
        $CaseWorkers = [Math]::Min(10, $Workers)
        $RunEstimatesS['ed8_cases'] = [int](10 * 143 / $CaseWorkers)
        $Run = Start-Ed8Run -Label 'ed8_cases' -MaskHex $MaskHex -TaskType 'run_v5_ed8_cases' -Workers $CaseWorkers `
            -Outputs @($Rows) -Arguments @("$Coupled/run_v5.py", 'ed8_cases', '--out', $Rows,
                '--workers', "$CaseWorkers", '--mask', $MaskHex)
        Wait-Runs @($Run)
    }
}
if ($Part -ne 'scope') { Invoke-IdentityCheck }

Complete-Step
