#Requires -Version 7
# 436.9 J-P3 edition 5 erratum 8 (jp3_remedy_spec_v5_erratum8.md, sealed cd2de978): the checks
# of the tool commit steps that read files only. No dependency on the other run step files:
# common_ed5.ps1 dot-sources it, the unit tests (05_tests/unit/test_jp3_12b_erratum8.py) run it
# alone. Each Get-E8*Stop returns $null (go on) or @{ code = <exit>; reason = <text> }.
#
# Get-E8DiffStop <name-status lines>      8-9 (a): `git diff --name-status --no-renames
#     606f8713 <tool commit>` lines against the rule - A / M of jp3_12b_judge.py, of the 12b
#     judge tests 05_tests/unit/test_jp3_12b*.py and of run_steps_ed5/; A / M of 00_docs/ and
#     the root CLAUDE.md; A only elsewhere under 06_analysis/; anything else (D, another path,
#     the shared run_steps/, pre_las_preset_runner.py of 8-9 (b)) stops 3
# Get-E8DecisionStop <decision.json> <allowed statuses>   8-9 (d) / 3: a decision record whose
#     status is not allowed stops 2 (needs_b4 where only decided is allowed = the setting defect
#     of 8-9 3); a decided one also needs blocks, blocks_used (the same set) and allow_k of 8-2
#     (W-5); a missing or unreadable record is 3
# Get-E8DecisionChoice <runs root>        8-9 4: the decision record step6c reads - the one
#     12b_decide_e8_b4.done names, else the one 12b_decide_e8.done names; it must be decided.
#     Returns @{ step; path } or a stop
# Get-E8BaseStop <runs root>              8-9 (e): the stopped 12b_vbk0_base attempt a1 (one stop
#     marker, exit 2, no done marker) with its b1 / b2 files. Returns @{ folder } or a stop
# Get-E8ReadyRuleStop <12b judge file>    erratum 2 2-9.6 with erratum 8 8-10: ready_rule with
#     verdict pass and allow_k = the 8-2 value of blocks_used, else not a pass (stop 2)
# Get-E8EnvironmentStop <base env> <new env> <setting> <declared extra>   8-9 (c): a VBK / b4
#     VBK0 run environment against a b1 / b2 VBK0 one; only R79_ROD_FAULT_PLAN, R79_T4H_DIR and
#     R79_V5_SETTING may differ, another variable only when declared with its value (stop 2)
# Get-E8WorkersStop <base command> <workers>   8-9 (c): --workers 4 on both (stop 2)
# Get-E8IdentityStop <base identity> <new identity> <run commit>   8-9 (c): threads (five),
#     python, python_version, git.head, git.is_clean and rules_seals of every start / end entry
#     equal the b1 / b2 VBK0 run's (time and affinity_mask may differ; stop 2, unreadable 3)
# Get-E8FixedListStop <old list> <tool list> <root> <run steps prefix>   8-9 (a''): the tool list
#     names the old list with its sha256; every old line still holds but the run steps (their
#     lines must be in the tool list), every tool list line holds (stop 2, missing list 3)

$E8RunStepsPrefix = '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed5/'
$E8SharedRunStepsPrefix = '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps/'
$E8JudgeToolPath = '04_scripts/04_hydraulic/coupled/jp3_12b_judge.py'
$E8ImportlibRunnerPath = '05_tests/unit/pre_las_preset_runner.py'
$E8JudgeTestPattern = '^05_tests/unit/test_jp3_12b[A-Za-z0-9_]*\.py$'
$E8EnvironmentDifferences = @('R79_ROD_FAULT_PLAN', 'R79_T4H_DIR', 'R79_V5_SETTING')
$E8RequiredWorkers = 4

function Get-E8Property($Object, [string]$Name) {
    # a JSON property or $null (Set-StrictMode 3 throws on a missing one)
    if ($null -eq $Object) { return $null }
    $Property = $Object.PSObject.Properties[$Name]
    if ($Property) { return $Property.Value }
    return $null
}

function Get-E8Allowance([string[]]$BlocksUsed) {
    # erratum 8 8-2: k_allow of the used blocks; $null = no allowance (b3, repeats, others)
    $Unique = @($BlocksUsed | Sort-Object -Unique)
    if ($Unique.Count -ne @($BlocksUsed).Count) { return $null }
    switch ($Unique -join ',') {
        'b1,b2' { return 7 }
        'b1,b2,b4' { return 9 }
    }
    return $null
}

function Get-E8DiffProblem([string]$Status, [string]$Path) {
    # 8-9 (a) on one diff line; $null = allowed
    $Letter = $Status.Substring(0, 1)
    if ($Path -ceq $E8ImportlibRunnerPath) { return "$Status $Path (8-9 (b): never changed)" }
    if ($Path.StartsWith($E8SharedRunStepsPrefix)) { return "$Status $Path (the shared run steps stay as they are)" }
    if (@('A', 'M') -cnotcontains $Letter) { return "$Status $Path (only A / M are allowed)" }
    if ($Path -ceq $E8JudgeToolPath) { return $null }
    if ($Path -cmatch $E8JudgeTestPattern) { return $null }
    if ($Path.StartsWith($E8RunStepsPrefix)) { return $null }
    if ($Path.StartsWith('00_docs/') -or $Path -ceq 'CLAUDE.md') { return $null }
    if ($Path.StartsWith('06_analysis/')) {
        if ($Letter -ceq 'A') { return $null }
        return "$Status $Path (an existing 06_analysis file changed; add only)"
    }
    return "$Status $Path (outside the erratum 8 8-9 (a) paths)"
}

function Get-E8DiffStop([string[]]$NameStatus) {
    $Problems = @()
    foreach ($Line in @($NameStatus)) {
        if (-not $Line -or -not $Line.Trim()) { continue }
        $Parts = $Line -split "`t"
        if ($Parts.Count -ne 2) { $Problems += "unreadable diff line '$Line' (a rename? use --no-renames)"; continue }
        $Problem = Get-E8DiffProblem $Parts[0] $Parts[1]
        if ($Problem) { $Problems += $Problem }
    }
    if ($Problems.Count) {
        return @{ code = 3; reason = "erratum 8 8-9 (a): $($Problems.Count) diff lines outside the rule, first: $($Problems[0])" }
    }
    return $null
}

function Get-E8DecisionStop([string]$Path, [string[]]$Allowed) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return @{ code = 3; reason = "decision record $Path missing" } }
    try { $Record = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json }
    catch { return @{ code = 3; reason = "decision record $Path unreadable: $($_.Exception.Message)" } }
    $Status = [string](Get-E8Property $Record 'status')
    if ($Allowed -cnotcontains $Status) {
        if ($Status -ceq 'needs_b4') {
            return @{ code = 2; reason = "decision $Path is needs_b4 again: a setting defect (erratum 8 8-9 3)" }
        }
        return @{ code = 2; reason = "decision $Path status '$Status', not $($Allowed -join ' / ') (erratum 8 8-9 (d))" }
    }
    if ($Status -cne 'decided') { return $null }
    $Blocks = @(Get-E8Property $Record 'blocks')
    $BlocksUsed = @(Get-E8Property $Record 'blocks_used')
    $AllowK = Get-E8Property $Record 'allow_k'
    if ($Blocks.Count -eq 0 -or $BlocksUsed.Count -eq 0 -or $null -eq $AllowK) {
        return @{ code = 2; reason = "decided record $Path without blocks / blocks_used / allow_k (erratum 8 8-8.2)" }
    }
    $Expected = Get-E8Allowance $BlocksUsed
    $SameSet = (@($Blocks | Sort-Object -Unique) -join ',') -ceq (@($BlocksUsed | Sort-Object -Unique) -join ',')
    $IsInteger = ($AllowK -is [long]) -or ($AllowK -is [int])
    if (-not $SameSet -or $null -eq $Expected -or -not $IsInteger -or $AllowK -ne $Expected) {
        return @{ code = 2; reason = "decided record ${Path}: blocks [$($Blocks -join ',')], blocks_used [$($BlocksUsed -join ',')], allow_k $AllowK do not agree with erratum 8 8-2" }
    }
    return $null
}

function Get-E8DecisionChoice([string]$RunsRoot) {
    foreach ($Step in @('12b_decide_e8_b4', '12b_decide_e8')) {
        $Marker = Join-Path $RunsRoot "$Step.done"
        if (-not (Test-Path -LiteralPath $Marker)) { continue }
        try { $Done = Get-Content -Raw -LiteralPath $Marker | ConvertFrom-Json }
        catch { return @{ code = 3; reason = "$Marker unreadable" } }
        $MarkedFolder = [string](Get-E8Property $Done 'folder')
        if (-not $MarkedFolder) { return @{ code = 3; reason = "$Marker names no folder" } }
        $DecisionPath = Join-Path (Join-Path $RunsRoot (Split-Path -Leaf $MarkedFolder)) 'decision.json'
        $Stop = Get-E8DecisionStop $DecisionPath @('decided')
        if ($Stop) { return $Stop }
        return @{ step = $Step; path = $DecisionPath }
    }
    return @{ code = 2; reason = 'neither 12b_decide_e8_b4.done nor 12b_decide_e8.done (erratum 8 8-9 4)' }
}

function Get-E8BaseStop([string]$RunsRoot) {
    $Name = '12b_vbk0_base'
    if (Test-Path -LiteralPath (Join-Path $RunsRoot "$Name.done")) {
        return @{ code = 2; reason = "$Name.done exists: erratum 8 8-9 (e) takes the stopped attempt a1 only" }
    }
    $Stops = @(Get-ChildItem -LiteralPath $RunsRoot -File | Where-Object { $_.Name -like "$Name.stop*" })
    if ($Stops.Count -ne 1) { return @{ code = 2; reason = "$($Stops.Count) $Name stop markers, one expected (erratum 8 8-9 (e))" } }
    try { $Record = Get-Content -Raw -LiteralPath $Stops[0].FullName | ConvertFrom-Json }
    catch { return @{ code = 3; reason = "$($Stops[0].FullName) unreadable" } }
    $StoppedFolder = [string](Get-E8Property $Record 'folder')
    $ExitCode = Get-E8Property $Record 'exit_code'
    if ((Split-Path -Leaf $StoppedFolder) -cne "${Name}_a1" -or $ExitCode -ne 2) {
        return @{ code = 2; reason = "$Name stop marker names $StoppedFolder exit $ExitCode, not ${Name}_a1 exit 2 (8-9 (e))" }
    }
    $BaseFolder = Join-Path $RunsRoot "${Name}_a1"
    foreach ($Block in @('b1', 'b2')) {
        foreach ($Item in @("VBK0_$Block.json", "VBK0_${Block}_t4h", "VBK0_$Block.identity.json")) {
            if (-not (Test-Path -LiteralPath (Join-Path $BaseFolder $Item))) {
                return @{ code = 2; reason = "$BaseFolder\$Item missing (8-9 (e))" }
            }
        }
    }
    return @{ folder = $BaseFolder }
}

function Get-E8ReadyRuleStop([string]$JudgePath) {
    if (-not (Test-Path -LiteralPath $JudgePath -PathType Leaf)) { return @{ code = 3; reason = "12b judge file $JudgePath missing" } }
    try { $Judged = Get-Content -Raw -LiteralPath $JudgePath | ConvertFrom-Json }
    catch { return @{ code = 3; reason = "12b judge file $JudgePath unreadable" } }
    $Rule = Get-E8Property $Judged 'ready_rule'
    if ($null -eq $Rule) { return @{ code = 2; reason = '12b judge file without ready_rule: not a pass (erratum 2 2-9.6 with erratum 8 8-10)' } }
    foreach ($Name in @('verdict', 'allow_k', 'blocks_used')) {
        if ($null -eq (Get-E8Property $Rule $Name)) { return @{ code = 2; reason = "ready_rule.$Name missing: not a pass (2-9.6)" } }
    }
    if ([string]$Rule.verdict -cne 'pass') { return @{ code = 2; reason = "ready_rule.verdict $($Rule.verdict), not pass (2-9.6)" } }
    $Expected = Get-E8Allowance @($Rule.blocks_used)
    $AllowK = $Rule.allow_k
    $IsInteger = ($AllowK -is [long]) -or ($AllowK -is [int])
    if ($null -eq $Expected -or -not $IsInteger -or $AllowK -ne $Expected) {
        return @{ code = 2; reason = "ready_rule.allow_k $AllowK is not the 8-2 value of blocks_used [$(@($Rule.blocks_used) -join ',')] (2-9.6)" }
    }
    return $null
}

function ConvertTo-E8Table($Value) {
    # a hashtable or a JSON object as name -> string value
    $Table = @{}
    if ($null -eq $Value) { return $Table }
    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($Key in $Value.Keys) { $Table[[string]$Key] = [string]$Value[$Key] }
    } else {
        foreach ($Property in $Value.PSObject.Properties) { $Table[$Property.Name] = [string]$Property.Value }
    }
    return $Table
}

function Get-E8EnvironmentStop($BaseEnvironment, $NewEnvironment, [string]$Setting, $DeclaredExtra) {
    $Base = ConvertTo-E8Table $BaseEnvironment
    $New = ConvertTo-E8Table $NewEnvironment
    $Declared = ConvertTo-E8Table $DeclaredExtra
    $Problems = @()
    if ($Base['R79_V5_SETTING'] -cne 'VBK0') { $Problems += "the base run setting is $($Base['R79_V5_SETTING']), not VBK0" }
    if ($New['R79_V5_SETTING'] -cne $Setting) { $Problems += "the run setting is $($New['R79_V5_SETTING']), not $Setting" }
    foreach ($Name in @(@($Base.Keys) + @($New.Keys) | Sort-Object -Unique)) {
        $InBase = $Base.ContainsKey($Name)
        $InNew = $New.ContainsKey($Name)
        if ($E8EnvironmentDifferences -contains $Name) {
            if (-not ($InBase -and $InNew)) { $Problems += "$Name on one side only" }
            continue
        }
        if (-not $InBase) {
            if ($Declared.ContainsKey($Name) -and $Declared[$Name] -ceq $New[$Name]) { continue }
            $Problems += "$Name=$($New[$Name]) is neither a b1 / b2 VBK0 variable nor declared with this value"
            continue
        }
        if (-not $InNew) { $Problems += "$Name missing (b1 / b2 VBK0: $($Base[$Name]))"; continue }
        if ($Base[$Name] -cne $New[$Name]) { $Problems += "$Name '$($New[$Name])' is not the b1 / b2 VBK0 '$($Base[$Name])'" }
    }
    if ($Problems.Count) { return @{ code = 2; reason = "erratum 8 8-9 (c) environment: $($Problems -join '; ')" } }
    return $null
}

function Get-E8WorkersStop([string]$BaseCommand, [int]$Workers) {
    if ($BaseCommand -notmatch '--workers (\d+)') { return @{ code = 3; reason = 'the base run command has no --workers' } }
    $BaseWorkers = [int]$Matches[1]
    if ($BaseWorkers -ne $E8RequiredWorkers -or $Workers -ne $E8RequiredWorkers) {
        return @{ code = 2; reason = "erratum 8 8-9 (c): --workers $Workers, base $BaseWorkers ($E8RequiredWorkers on both)" }
    }
    return $null
}

function Get-E8IdentityView($Entry) {
    # the 8-9 (c) fields of one identity entry, as compact JSON
    $Git = Get-E8Property $Entry 'git'
    $View = [ordered]@{ threads = (Get-E8Property $Entry 'threads'); python = (Get-E8Property $Entry 'python')
        python_version = (Get-E8Property $Entry 'python_version'); git_head = (Get-E8Property $Git 'head')
        git_is_clean = (Get-E8Property $Git 'is_clean'); rules_seals = (Get-E8Property $Entry 'rules_seals') }
    return ($View | ConvertTo-Json -Depth 12 -Compress)
}

function Get-E8IdentityStop([string]$BasePath, [string]$NewPath, [string]$ExpectedHead) {
    foreach ($Item in @($BasePath, $NewPath)) {
        if (-not (Test-Path -LiteralPath $Item -PathType Leaf)) { return @{ code = 3; reason = "identity record $Item missing" } }
    }
    try {
        $BaseRecord = Get-Content -Raw -LiteralPath $BasePath | ConvertFrom-Json
        $NewRecord = Get-Content -Raw -LiteralPath $NewPath | ConvertFrom-Json
    } catch { return @{ code = 3; reason = "identity record unreadable: $($_.Exception.Message)" } }
    $BaseStarts = @(Get-E8Property $BaseRecord 'start')
    if ($BaseStarts.Count -eq 0) { return @{ code = 2; reason = "base identity $BasePath without a start entry" } }
    $Reference = $BaseStarts[0]
    $ReferenceGit = Get-E8Property $Reference 'git'
    if ([string](Get-E8Property $ReferenceGit 'head') -cne $ExpectedHead -or (Get-E8Property $ReferenceGit 'is_clean') -ne $true) {
        return @{ code = 2; reason = "base identity $BasePath is not the run commit $ExpectedHead with a clean tree" }
    }
    $Expected = Get-E8IdentityView $Reference
    $Starts = @(Get-E8Property $NewRecord 'start')
    $Ends = @(Get-E8Property $NewRecord 'end')
    if ($Starts.Count -eq 0 -or $Ends.Count -eq 0) { return @{ code = 2; reason = "identity record $NewPath without start / end entries" } }
    foreach ($Entry in $Starts + $Ends) {
        if ((Get-E8IdentityView $Entry) -cne $Expected) {
            return @{ code = 2; reason = "erratum 8 8-9 (c): $(Split-Path -Leaf $NewPath) differs from $(Split-Path -Leaf $BasePath) in threads / python / git / rules_seals" }
        }
    }
    return $null
}

function Read-E8FixedList([string]$ListPath) {
    $Entries = [ordered]@{}
    foreach ($Line in (Get-Content -LiteralPath $ListPath)) {
        if (-not $Line.Trim()) { continue }
        $Sha, $Listed = $Line -split ' \*', 2
        $Entries[$Listed] = $Sha
    }
    return $Entries
}

function Get-E8FileShaStop([string]$Root, [string]$Listed, [string]$Sha) {
    $File = Join-Path $Root $Listed
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { return @{ code = 2; reason = "fixed input $Listed missing" } }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $File).Hash.ToLower()
    if ($Actual -cne $Sha) { return @{ code = 2; reason = "fixed input $Listed sha256 $Actual is not the listed $Sha" } }
    return $null
}

function Get-E8FixedListStop([string]$OldList, [string]$ToolList, [string]$Root, [string]$RunStepsPrefix) {
    foreach ($List in @($OldList, $ToolList)) {
        if (-not (Test-Path -LiteralPath $List -PathType Leaf)) { return @{ code = 3; reason = "fixed list $List missing" } }
    }
    $Old = Read-E8FixedList $OldList
    $Tool = Read-E8FixedList $ToolList
    $OldRelative = $OldList.Substring($Root.Length + 1).Replace('\', '/')
    if (-not $Tool.Contains($OldRelative)) {
        return @{ code = 2; reason = "the tool list does not name $OldRelative (erratum 8 8-9 (a''): the two lists are linked)" }
    }
    $Stop = Get-E8FileShaStop $Root $OldRelative $Tool[$OldRelative]
    if ($Stop) { return $Stop }
    foreach ($Listed in $Old.Keys) {
        if ($Listed.StartsWith($RunStepsPrefix)) {
            # the run steps of the tool commit replace the run commit's (8-9 (a)); the tool list holds them
            if (-not $Tool.Contains($Listed)) { return @{ code = 2; reason = "run step $Listed of the old list is not in the tool list" } }
            continue
        }
        $Stop = Get-E8FileShaStop $Root $Listed $Old[$Listed]
        if ($Stop) { return $Stop }
    }
    foreach ($Listed in $Tool.Keys) {
        $Stop = Get-E8FileShaStop $Root $Listed $Tool[$Listed]
        if ($Stop) { return $Stop }
    }
    return $null
}
