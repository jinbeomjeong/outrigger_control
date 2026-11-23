#Requires -Version 7
# Step 5, implementation checks (spec v6 4 step 5; erratum 2 2-1, Y-14), after the fixed list and
# before confirm. Five parts, each its own step with its .done marker, in this order; a part
# starts only when the one before is done, and every judge goes on only on exit 0:
#   -Part v0d0   (i) P6-0: run_v5 j9_v0_sample on the fixed V0 sample key file (48 lines) ->
#                jp3_j9main_judge.py v0-sample against the stored v5/main.jsonl; the D0 runner on
#                variant D0-1 x the 8 D0 keys -> jp3_ed6_judge.py d0-1 against 390f88a9
#   -Part p51    (i)-2 P5-1-type invariance: run_v5 j9_cases (15) and j9_case_f (15),
#                jp3_case_replay.py C / D (2), jp3_x11_replay.py --arm both (1) -> hash-match of
#                each against the 606f8713 output of the same name (every line equal)
#   -Part t8     (ii) P6-1: run_v5 ed6_t8 (22 jobs x VBL, VBL0) -> jp3_ed6_judge.py t8
#   -Part cases  (iii) P6-2: run_v5 ed6_cases (cases E and F x VBL, LSL1 .. LSL4) ->
#                jp3_ed6_judge.py cases (J-P3 key 0, 10 judged rows, 6.1 identity)
#   -Part probe  (v) P6-3: ed6_probe.py --arms a1a2b3 (5 plants x 8 keys = 40) -> hash-match
#                against the b1off check lines ed6_probe_a1a2b3.jsonl (cbdb4d28...)
# The reference files are fixed list entries (erratum 2 2-1 5). Placement from
# compute-scheduler-expert (-MaskHex, -Workers).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('v0d0', 'p51', 't8', 'cases', 'probe')][string]$Part,
    [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
. "$PSScriptRoot\common_ed6.ps1"

$Order = @('v0d0', 'p51', 't8', 'cases', 'probe')
$Requires = @('l1ref') + @($Order[0..([Array]::IndexOf($Order, $Part))] | Select-Object -SkipLast 1 |
        ForEach-Object { "impl_$_" })
$Folder = Initialize-Ed6Step "impl_$Part" $Attempt $Requires
$Ed5Runs = "$CauseDir\j9_runs\606f8713"
$D0Stored = "$CauseDir\j9_runs\390f88a9\d0_plant_split_a1\d0_plant_split.jsonl"
$ProbeStored = "$CauseDir\ed6_design\probe_1bd405c8\b1off_check\ed6_probe_a1a2b3.jsonl"
$V0SampleKeys = "$PrelaunchDir\ed5_inputs\j9main_v0_sample_keys.json"

function Assert-Listed([string[]]$Files) {
    # every reference file is the fixed list's (erratum 2 2-1 5)
    foreach ($File in $Files) {
        if (-not (Test-Path -LiteralPath $File)) { Stop-Step 2 "$File missing" }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $File).Hash.ToLower() -ne (Get-ListedSha $File)) {
            Stop-Step 2 "$File is not the fixed list's file"
        }
    }
}

function Invoke-HashMatch([string]$Label, [string]$Reference, [string]$Rows, [string]$SubCommand = 'hash-match') {
    Invoke-Judge $Label @($Ed6Judge, $SubCommand, '--reference', $Reference, '--rows', $Rows,
        '--out', "$Folder\judge\$Label.json") | Out-Null
}

switch ($Part) {
    'v0d0' {
        Assert-Listed @($V0SampleKeys, $D0Stored)
        $Sample = "$Folder\v0_sample.jsonl"
        $D0 = "$Folder\d0_1.jsonl"
        $RunEstimatesS['v0_sample'] = 120; $RunEstimatesS['d0_1'] = 300
        $Runs = @(
            (Start-Run -Label 'v0_sample' -MaskHex $MaskHex -TaskType 'run_v5_j9_v0_sample' -Workers $Workers `
                -Arguments @("$Coupled/run_v5.py", 'j9_v0_sample', '--jobs-file', $V0SampleKeys, '--out', $Sample,
                    '--workers', "$Workers", '--mask', $MaskHex)))
        Wait-Runs $Runs
        $Runs = @(
            (Start-Run -Label 'd0_1' -MaskHex $MaskHex -TaskType 'jp3_d0_1' -Workers 8 `
                -Arguments @("$Coupled/d0_plant_split.py", '--out', $D0, '--variants', 'D0-1', '--workers', '8',
                    '--mask', $MaskHex)))
        Wait-Runs $Runs
        Invoke-IdentityCheck
        Invoke-Judge 'v0_sample' @("$Coupled/jp3_j9main_judge.py", 'v0-sample', '--sample-keys', $V0SampleKeys,
            '--sample', $Sample, '--v0', $V0Rows, '--v0-sha256', $V0Sha, '--out', "$Folder\judge\v0_sample.json") | Out-Null
        Invoke-HashMatch 'd0_1' $D0Stored $D0 'd0-1'
    }
    'p51' {
        $References = [ordered]@{ j9_cases = "$Ed5Runs\cases_a1\j9_cases.jsonl"; case_cd = "$Ed5Runs\cases_a1\cd.jsonl"
            x11 = "$Ed5Runs\cases_a1\lsj4_x11.jsonl"; j9_case_f = "$Ed5Runs\casef_a1\j9_case_f.jsonl" }
        Assert-Listed @($References.Values)
        $Out = [ordered]@{ j9_cases = "$Folder\j9_cases.jsonl"; case_cd = "$Folder\cd.jsonl"
            x11 = "$Folder\lsj4_x11.jsonl"; j9_case_f = "$Folder\j9_case_f.jsonl" }
        $Runs = @(
            (Start-Run -Label 'j9_cases' -MaskHex $MaskHex -TaskType 'run_v5_j9_cases' -Workers 5 `
                -Arguments @("$Coupled/run_v5.py", 'j9_cases', '--out', $Out.j9_cases, '--workers', '5', '--mask', $MaskHex)),
            (Start-Run -Label 'j9_case_f' -MaskHex $MaskHex -TaskType 'run_v5_j9_case_f' -Workers 8 `
                -Arguments @("$Coupled/run_v5.py", 'j9_case_f', '--out', $Out.j9_case_f, '--workers', '8', '--mask', $MaskHex)),
            (Start-Run -Label 'case_cd' -MaskHex $MaskHex -WrapOutput $Out.case_cd -TaskType 'jp3_case_replay' -Workers 2 `
                -Arguments @("$Coupled/jp3_case_replay.py", '--out', $Out.case_cd, '--settings', 'VBG4,VBG6', '--workers', '2',
                    '--mask', $MaskHex)),
            (Start-Run -Label 'x11_both' -MaskHex $MaskHex -WrapOutput $Out.x11 -TaskType 'jp3_x11_replay' -Workers 1 `
                -Arguments @("$Coupled/jp3_x11_replay.py", '--out', $Out.x11, '--arm', 'both', '--mask', $MaskHex)))
        Wait-Runs $Runs
        Invoke-IdentityCheck
        foreach ($Name in $References.Keys) { Invoke-HashMatch "p51_$Name" $References[$Name] $Out[$Name] }
    }
    't8' {
        $Rows = "$Folder\ed6_t8.jsonl"
        $Run = Start-Run -Label 'ed6_t8' -MaskHex $MaskHex -TaskType 'run_v5_ed6_t8' -Workers $Workers `
            -Arguments @("$Coupled/run_v5.py", 'ed6_t8', '--p3-hash-source', $V0Rows, '--out', $Rows,
                '--workers', "$Workers", '--mask', $MaskHex)
        Wait-Runs @($Run)
        Invoke-IdentityCheck
        Invoke-Judge 't8' @($Ed6Judge, 't8', '--rows', $Rows, '--main-jsonl', $V0Rows,
            '--out', "$Folder\judge\t8.json") | Out-Null
    }
    'cases' {
        $Rows = "$Folder\ed6_cases.jsonl"
        $Run = Start-Run -Label 'ed6_cases' -MaskHex $MaskHex -TaskType 'run_v5_ed6_cases' -Workers 10 `
            -Arguments @("$Coupled/run_v5.py", 'ed6_cases', '--out', $Rows, '--workers', '10', '--mask', $MaskHex)
        Wait-Runs @($Run)
        Invoke-IdentityCheck
        Invoke-Judge 'cases' @($Ed6Judge, 'cases', '--rows', $Rows, '--out', "$Folder\judge\cases.json") | Out-Null
    }
    'probe' {
        Assert-Listed @($ProbeStored)
        $Rows = "$Folder\ed6_probe_a1a2b3.jsonl"
        $RunEstimatesS['probe'] = [int](40 * 143 / $Workers)
        # ed6_probe.py writes its own identity record (no -WrapOutput)
        $Run = Start-Run -Label 'probe' -MaskHex $MaskHex -TaskType 'jp3_ed6_probe' -Workers $Workers `
            -Arguments @("$Coupled/ed6_probe.py", '--out', $Rows, '--arms', 'a1a2b3', '--workers', "$Workers",
                '--mask', $MaskHex)
        Wait-Runs @($Run)
        Invoke-IdentityCheck
        Invoke-HashMatch 'probe' $ProbeStored $Rows
    }
}

Complete-Step
