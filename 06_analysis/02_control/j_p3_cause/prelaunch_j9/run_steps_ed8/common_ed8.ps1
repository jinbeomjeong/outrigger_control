#Requires -Version 7
# 436.9 J-P3 edition 8: shared settings of the edition 8 run steps (jp3_remedy_spec_v8_rules.md,
# sha256 35f9eba8...: 4 steps 4 .. 10, 11.1). The edition 4a helpers come from
# ..\run_steps\common.ps1 and ..\run_steps\record_helper.ps1 (unchanged), the core kind from
# ..\run_steps_ed7\core_kind_ed7.ps1. This file sets the edition 8 run commit C8, folders, inputs,
# the numba cache and the start checks.
#
# Run only (spec 11.1, 11.2): C8 holds no judge. The steps run the lines and record them; every
# judgement (P8-0 .. P8-16 of step 4 and steps 5 .. 10) is made at the judge commit T8 (the child
# of C8) after its audit. P8-10 (scope) is checked at every step start (Get-ScopeProblem).
#
# The run commit and the run worktree are read from prelaunch_j9\ed8_run_config.json of the main
# checkout (from ed8_run_config.template.json; a commit cannot name itself).
#
# Run order (the main session launches every step; each needs the .done of the ones before):
#   1. step4_impl_ed8.ps1 -Part scope     P8-10 evidence (diff of C8 against the implementation
#                                         commit), no run
#   2. step_l1ref_ed8.ps1                 L1 references (12b L1_VBN0 / L1_VBN, 12a L1a_VBN0 /
#                                         L1a_VBN), before any 12a / 12b output
#   3. step4_impl_ed8.ps1 -Part p80 | p816 | p85 | p88 | p815 | t8 | cases   (in this order)
#        p80   P8-0: ed7_probe.py --arms a2 --part all (114, against b46bdf8f repro_a2)
#        p816  P8-16 (C8 time point): ed8_probe --part p816 --arms B_impl,L2_impl (54)
#        p85   P8-5: ed8_probe --part p816 --plants M,LSM4,Mslow --arms a8,a8_psw_off (46)
#        p88   P8-8: the same with --arms a8,a8_h3_off (46)
#        p815  P8-15: ed8_probe --part p816 --arms a8,a8_l2_off (54, KM0 r79 rows included)
#        t8    P8-1: run_v5 ed8_t8 (44), cases  P8-2: run_v5 ed8_cases (10)
#   4. step5_heldout_v0_ed8.ps1 -Part v0 [| aa2 | aa3]   G' stage 5 V0 (678; aa2 / aa3 as 7.4)
#   5. step6_census_ed8.ps1               census: run_v5 ed8_keys census_keys_ed8.json (1043)
#   (step 7 = the S8-C seal: no run)
#   6. step8_heldout_ed8.ps1 -S8cRules ... -S8cSha256 ...   G': run_v5 ed8_keys heldout (339)
#   7. step9_dg3_ed8.ps1 -S8cRules ... -S8cSha256 ...       T-JR-12a VBN / VBN0 (H-6 135 keys)
#   8. step10a_plan_ed8.ps1, step10b_vbkn0_ed8.ps1, step10c_vbkn_ed8.ps1   T-JR-12b
# Every step records its identity at the start and the end (HEAD, is_clean, 03_src tree); every
# output path is new (the attempt folder and every output file are asserted absent).
#
# Interpreter: run_v5 / ed7_probe / r79 runs call dynamics-dev python.exe directly (the edition 7
# run steps); the ed8_probe parts (P8-5 / P8-8 / P8-15 / P8-16) run through
# `conda run --no-capture-output -n dynamics-dev python -I -B`, the call of their P8-14
# reference (rule (바)). Both are recorded per run.
#
# Dry run (no simulation, no tool, nothing in the main checkout): ED8_DRY_RUN_ROOT=DRY_ROOT (a scratch folder).

. "$PSScriptRoot\..\run_steps\common.ps1"
. "$PSScriptRoot\..\run_steps\record_helper.ps1"
. "$PSScriptRoot\..\run_steps_ed7\core_kind_ed7.ps1"
$Ed8StepsDir = $PSScriptRoot

# --- dry run ---------------------------------------------------------------------------------
$Ed8DryRoot = [string]$env:ED8_DRY_RUN_ROOT
$IsEd8Dry = [bool]$Ed8DryRoot

# --- the sealed spec and the implementation commit ---------------------------------------------
$SpecV8 = "$CauseDir\jp3_remedy_spec_v8_rules.md"
$SpecV8Sha256 = '35f9eba8f98f93ddb0fa850ff60844ebd7a443f819febcdf0906a5502c121520'
$ImplCommit = '41e107e98a5b0e45c3197dbfee46e8dd033eba35'
# spec 11.1: C8 is the one child of the implementation commit (P8-16 passed there)
$ControllerTree = 'ed797e8e6bb239cad6bd80a24fba3504ab4df92b'
# git rev-parse C8:03_src = the implementation commit's 03_src (C8 changes no 03_src file)

# P8-10 / 11.1: the paths C8 may change against the implementation commit (the sha table, the
# tests of its values - test_ed8_impl.py: its "empty table" case now sets the table empty itself)
$ScopeFiles = @('04_scripts/04_hydraulic/coupled/run_v5.py',
    '05_tests/unit/test_ed8_run_commit.py', '05_tests/unit/test_ed8_impl.py')
$ScopePrefix = '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed8/'
$RunV5Added = '+    "census_keys_ed8.json": "278b332f694405d5f9be432467e294b64492d5ffd638a76986e819460c88c535",'

# --- run commit and paths (the main session's config file) -----------------------------------
$Ed8Placeholder = '^<ED8_'
$Ed8ConfigFile = if ($IsEd8Dry) { "$Ed8DryRoot\ed8_run_config.json" } else { "$PrelaunchDir\ed8_run_config.json" }

function Exit-Ed8([int]$Code, [string]$Reason) {
    # a stop before any step folder exists (the process ends here with the code)
    Write-Host "STOP: $Reason"
    [Console]::Out.Flush()
    [Environment]::Exit($Code)
}

function Get-Ed8ConfigProblem($Config) {
    if ($null -eq $Config) { return "$Ed8ConfigFile missing (copy ed8_run_config.template.json and fill it in)" }
    foreach ($Value in @($Config.run_commit, $Config.worktree)) {
        if ([string]$Value -match $Ed8Placeholder) { return "$Ed8ConfigFile still holds $Value" }
    }
    if ([string]$Config.run_commit -notmatch '^[0-9a-f]{40}$') { return 'run commit is not a full sha' }
    return $null
}
$Ed8Config = if (Test-Path -LiteralPath $Ed8ConfigFile) { Get-Content -Raw -LiteralPath $Ed8ConfigFile | ConvertFrom-Json } else { $null }
$Ed8ConfigProblem = Get-Ed8ConfigProblem $Ed8Config
if ($Ed8ConfigProblem) { Exit-Ed8 3 $Ed8ConfigProblem }
$RunCommit = [string]$Ed8Config.run_commit
$Worktree = [string]$Ed8Config.worktree
if (-not $Ed8StepsDir.StartsWith("$Worktree\", [StringComparison]::OrdinalIgnoreCase)) {
    Exit-Ed8 3 "run the steps from the run worktree ($Worktree), not $Ed8StepsDir"
}

$RunShort = $RunCommit.Substring(0, 8)
$RunsParent = if ($IsEd8Dry) { "$Ed8DryRoot\j9_runs" } else { "$CauseDir\j9_runs" }
$RunsRoot = "$RunsParent\$RunShort"
$IdentityChecks = "$RunsRoot\_identity_checks"

# --- the numba cache outside the worktree and the outputs (C8 draft fragment) -----------------
$NumbaCacheRoot = if ($IsEd8Dry) { "$Ed8DryRoot\numba_cache" } else { 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache' }
$NumbaCacheDir = "$NumbaCacheRoot\$RunShort"

function Get-NumbaCacheProblem {
    # the cache folder must lie outside the run worktree and outside the runs root
    $Cache = [IO.Path]::GetFullPath($NumbaCacheDir).TrimEnd('\') + '\'
    foreach ($Forbidden in @($Worktree, $RunsParent)) {
        $Root = [IO.Path]::GetFullPath($Forbidden).TrimEnd('\') + '\'
        if ($Cache.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) { return "NUMBA_CACHE_DIR $Cache lies inside $Root" }
    }
    return $null
}

function Get-WorktreeNumbaFiles {
    # .nbi / .nbc files inside the run worktree's 04_scripts (expected: none); the unary comma
    # keeps an empty array an array (a bare "return @()" arrives as $null)
    return , @(Get-ChildItem -LiteralPath "$Worktree\04_scripts" -Recurse -File -Include '*.nbi', '*.nbc' `
            -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
}

# --- inputs (main checkout) with their sha256 -------------------------------------------------
$KeysSealDir = "$CauseDir\ed8_design\keys_seal_$($ImplCommit.Substring(0, 8))"
$P814Raw = "$CauseDir\ed8_design\control_level_deadlock\probe_8a2a52ce\raw"
$Ed8Inputs = [ordered]@{
    spec_v8      = @($SpecV8, $SpecV8Sha256)
    census_keys  = @("$KeysSealDir\census_keys_ed8.json",
        '278b332f694405d5f9be432467e294b64492d5ffd638a76986e819460c88c535')   # spec 5.1, P8-10
    heldout_keys = @("$KeysSealDir\heldout_g_ed8.json",
        'a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5')   # spec 7.2
    p814_plan    = @("$P814Raw\plans\P814-B-VBKM0.json",
        '99e506534669f4779dd4f44c31b90836b4f5f23a955bae374c83afc82597a463')   # spec 12 P8-16
    p814_runs    = @("$P814Raw\runs.jsonl",
        '89efe66fc521f6d58c8c90304a9258747eef45d422ef43666a53f5ddd7fa9418')   # P8-16 reference
    p80_repro    = @("$CauseDir\j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl",
        'd60306db8073b3ffba285f58e54d8fd9779867d47c4e79e9878d02974f082430')   # P8-0 (114 lines)
    l1_keys_12b  = @("$PrelaunchDir\ed5_inputs\l1_keys_12b.txt",
        '9f815533c0deb44925134465fe90e0f508c1819ae2c4c34bf4f3b651b6a63ca5')
    l1_keys_12a  = @("$PrelaunchDir\l1_keys_d3c6c57e.json",
        'eea8ed0d5f3aa79ecb5cf1cb892fa82f7d4bac780f8b3b17dbd069200765c6af')
    c92_keys     = @("$PrelaunchDir\ed5_inputs\x11\c92_keys.txt", $null)
    c93_keys     = @("$PrelaunchDir\ed5_inputs\x11\c93_keys.txt", $null)
}
$V0Rows = Get-FixedPath 'MAIN_JSONL_SHA256'
$H6Keys = Get-FixedPath 'H6_SHA256'
$NoiseVb = Get-FixedPath 'NOISE_VB_SHA256'
$L1Labels = [ordered]@{ L1_VBN0 = @('VBN0', 'l1_keys_12b'); L1_VBN = @('VBN', 'l1_keys_12b')
    L1a_VBN0 = @('VBN0', 'l1_keys_12a'); L1a_VBN = @('VBN', 'l1_keys_12a') }
$ScanRequiredRoots = @("$CauseDir\j9_runs\79495405", "$CauseDir\j9_runs\6bfb2560",
    "$CauseDir\j9_runs\b46bdf8f", "$CauseDir\j9_runs\8a2a52ce",
    "$CauseDir\ed8_design\control_level_deadlock\probe_8a2a52ce",
    "$CauseDir\ed8_design\p816_prerun_$($ImplCommit.Substring(0, 8))", $RunsRoot)
# spec 8: the edition 6 outputs (records B / C / D under 79495405), the probe 6bfb2560, the
# b46bdf8f reproduction, all edition 7 outputs (8a2a52ce, l1ref r79 keys included), the P8-14
# outputs, the P8-16 pre-run and this run's edition 8 outputs (step 4 P8-16 r79 lines, census, G')

foreach ($Setting in @('VBN', 'VBN0', 'VBKN', 'VBKN0')) { $R79RodModel[$Setting] = 'plant_truth' }
$CondaExe = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
$CondaPrefix = @('run', '--no-capture-output', '-n', 'dynamics-dev', 'python', '-I', '-B')

function Get-InputProblem([string]$Name) {
    $Path, $Expected = $Ed8Inputs[$Name]
    if (-not (Test-Path -LiteralPath $Path)) { return "input $Name missing: $Path" }
    if ($null -eq $Expected) { return $null }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
    if ($Actual -ne $Expected) { return "input $Name sha256 $Actual is not $Expected" }
    return $null
}

function Get-InputPath([string]$Name) { return $Ed8Inputs[$Name][0] }

function Get-RunIdentity {
    # HEAD, is_clean and the 03_src tree of the run worktree (a git failure gives $null fields)
    $Head = (& git -C $Worktree rev-parse HEAD)
    $HeadOk = $LASTEXITCODE -eq 0
    $Status = (& git -C $Worktree status --porcelain --untracked-files=no)
    $StatusOk = $LASTEXITCODE -eq 0
    $Tree = (& git -C $Worktree rev-parse 'HEAD:03_src')
    $TreeOk = $LASTEXITCODE -eq 0
    return [ordered]@{ head = if ($HeadOk) { [string]$Head.Trim() } else { $null }
        is_clean = if ($StatusOk) { -not $Status } else { $null }
        src_tree = if ($TreeOk) { [string]$Tree.Trim() } else { $null }
        time = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') }
}

function Get-IdentityProblem($Identity) {
    if ($Identity.head -ne $RunCommit) { return "HEAD $($Identity.head) is not $RunCommit" }
    if ($Identity.is_clean -ne $true) { return 'the run worktree is not clean (or git failed)' }
    if ($Identity.src_tree -ne $ControllerTree) { return "03_src tree $($Identity.src_tree) is not $ControllerTree" }
    return $null
}

function Get-ScopeProblem {
    # P8-10: C8 is the child of the implementation commit and changes only the sha table of
    # run_v5.py, its test and the run steps; no 03_src change. $null: in scope.
    $Parent = (& git -C $Worktree rev-parse "$RunCommit^")
    if ($LASTEXITCODE -ne 0) { return 'git rev-parse of the run commit parent failed' }
    if ($Parent.Trim() -ne $ImplCommit) { return "the run commit parent $Parent is not $ImplCommit" }
    $Names = @(& git -C $Worktree diff --name-only $ImplCommit $RunCommit)
    if ($LASTEXITCODE -ne 0) { return 'git diff --name-only failed' }
    $Outside = @($Names | Where-Object { $ScopeFiles -notcontains $_ -and -not $_.StartsWith($ScopePrefix) })
    if ($Outside.Count) { return "P8-10: $($Outside.Count) changed paths outside 11.1 ($($Outside[0]) ...)" }
    $SrcDiff = @(& git -C $Worktree diff --name-only $ImplCommit $RunCommit -- 03_src)
    if ($LASTEXITCODE -ne 0) { return 'git diff of 03_src failed' }
    if ($SrcDiff.Count) { return "P8-10: C8 changes 03_src ($($SrcDiff[0]))" }
    $RunV5Diff = @(& git -C $Worktree diff -U0 $ImplCommit $RunCommit -- '04_scripts/04_hydraulic/coupled/run_v5.py')
    if ($LASTEXITCODE -ne 0) { return 'git diff of run_v5.py failed' }
    if ($RunV5Diff -notcontains $RunV5Added) { return 'P8-10: run_v5.py diff without the census sha line' }
    return $null
}

function Complete-Step {
    # common.ps1 Complete-Step with the end identity and the numba check; a change stops 3 (the
    # step's outputs are not used: no .done marker)
    $End = Get-RunIdentity
    $StepState.Codes['identity_end'] = $End
    $Problem = Get-IdentityProblem $End
    if ($Problem) { Stop-Step 3 "identity at the end: $Problem (outputs not used)" }
    $Numba = Get-WorktreeNumbaFiles
    if ($Numba.Count) { Stop-Step 3 "numba cache files appeared in the worktree ($($Numba[0]))" }
    $Record = [ordered]@{ step = $StepState.Name; folder = $StepState.Folder; exit_code = 0
        commit = $RunCommit; started = $StepState.Started
        done = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'); codes = $StepState.Codes
        previous_attempts = $StepState.PreviousStops; cleared_variables = $StepState.ClearedVariables
        commands = $StepState.Commands }
    Write-JsonFile "$($StepState.Folder)\step_record.json" $Record
    Write-JsonFile "$RunsRoot\$($StepState.Name).done" $Record
    Write-Host "DONE $($StepState.Name) -> $($StepState.Folder)"
    exit 0
}

function Initialize-Ed8Step([string]$StepName, [int]$Attempt, [string[]]$Requires, [string[]]$Inputs = @()) {
    # the edition 4a step start, then the P8-10 scope, the start identity, the numba cache
    # checks and the step's inputs
    $Folder = Initialize-Step $StepName $Attempt $Requires
    $Scope = Get-ScopeProblem
    if ($Scope) { Stop-Step 3 $Scope }
    $StepState.Codes['scope'] = "P8-10: $ImplCommit -> $RunCommit in scope"
    $Start = Get-RunIdentity
    $StepState.Codes['identity_start'] = $Start
    $Problem = Get-IdentityProblem $Start
    if ($Problem) { Stop-Step 3 "identity at the start: $Problem" }
    $Problem = Get-NumbaCacheProblem
    if ($Problem) { Stop-Step 3 $Problem }
    $Before = Get-WorktreeNumbaFiles
    if ($Before.Count) { Stop-Step 3 "numba cache files in the worktree ($($Before[0]))" }
    New-Item -ItemType Directory -Force -Path $NumbaCacheDir | Out-Null
    $StepState.Codes['numba_cache_dir'] = $NumbaCacheDir
    # a switch that yields @() gives $null: only the named inputs count
    foreach ($Name in @(@('spec_v8') + @($Inputs) | Where-Object { $_ })) {
        $InputProblem = Get-InputProblem $Name
        if ($InputProblem) { Stop-Step 3 $InputProblem }
        $StepState.Codes["input:$Name"] = Get-RepoPath (Get-InputPath $Name)
    }
    $StepState.Codes['run_steps'] = "$Ed8StepsDir (run commit $RunCommit)"
    return $Folder
}

function Assert-NewOutput([string[]]$Paths) {
    # every output path is new (an existing file or folder refuses the run, exit 2)
    foreach ($Path in $Paths) {
        if (Test-Path -LiteralPath $Path) { Stop-Step 2 "$Path exists (every output path is new)" }
    }
}

function Start-Ed8Run {
    # Start-Run (direct dynamics-dev python.exe) after the mask and new-output checks, with
    # NUMBA_CACHE_DIR outside the worktree
    param([string]$Label, [string]$MaskHex, [string[]]$Arguments, [hashtable]$Environment = @{},
        [string]$WrapOutput = '', [string]$TaskType, [int]$Workers, [string[]]$Outputs)
    $MaskProblem = Get-CoreMaskProblem $MaskHex
    if ($MaskProblem) { Stop-Step 3 $MaskProblem }
    Assert-NewOutput $Outputs
    $StepState.Codes["core:$Label"] = Get-CoreKind $MaskHex
    $StepState.Codes["invocation:$Label"] = 'python.exe -I -B'
    $Environment = @{ NUMBA_CACHE_DIR = $NumbaCacheDir } + $Environment
    return Start-Run -Label $Label -MaskHex $MaskHex -Arguments $Arguments -Environment $Environment `
        -WrapOutput $WrapOutput -TaskType $TaskType -Workers $Workers
}

function Start-Ed8CondaRun {
    # one ed8_probe run through conda run (the P8-14 call, rule (바)), detached, with its sampler
    param([string]$Label, [string]$MaskHex, [string[]]$Arguments, [string]$TaskType, [int]$Workers,
        [string[]]$Outputs)
    $MaskProblem = Get-CoreMaskProblem $MaskHex
    if ($MaskProblem) { Stop-Step 3 $MaskProblem }
    Assert-NewOutput $Outputs
    $StepState.Codes["core:$Label"] = Get-CoreKind $MaskHex
    $StepState.Codes["invocation:$Label"] = 'conda run --no-capture-output -n dynamics-dev python -I -B'
    $All = $CondaPrefix + $Arguments
    Assert-PlainArguments $All
    if ($IsEd8Dry) {
        $StepState.Commands.Add([ordered]@{ label = $Label; mask = $MaskHex
            environment = @{ NUMBA_CACHE_DIR = $NumbaCacheDir }; workers = $Workers
            command = "$CondaExe $($All -join ' ')"; dry_run = $true })
        return [pscustomobject]@{ Label = $Label; MaskHex = $MaskHex; TaskType = $TaskType; Workers = $Workers }
    }
    $Folder = $StepState.Folder
    $env:NUMBA_CACHE_DIR = $NumbaCacheDir
    Set-OwnAffinity $MaskHex
    $Process = Start-Process -FilePath $CondaExe -ArgumentList $All -WorkingDirectory $Worktree `
        -RedirectStandardOutput "$Folder\logs\$Label.log" -RedirectStandardError "$Folder\logs\$Label.err" `
        -PassThru -WindowStyle Hidden
    $null = $Process.Handle
    Remove-Item Env:NUMBA_CACHE_DIR -ErrorAction SilentlyContinue
    $Sampler = Start-Process -FilePath $DevPython -ArgumentList @('-I', '-B', "$SchedTools\sample.py",
        '--pid', "$($Process.Id)", '--out', "$Folder\logs\$Label.sample.json") -PassThru -WindowStyle Hidden
    $StepState.Commands.Add([ordered]@{ label = $Label; mask = $MaskHex
        environment = @{ NUMBA_CACHE_DIR = $NumbaCacheDir }; command = "$CondaExe $($All -join ' ')"
        pid = $Process.Id })
    return [pscustomobject]@{ Label = $Label; Process = $Process; Sampler = $Sampler
        MaskHex = $MaskHex; TaskType = $TaskType; Workers = $Workers }
}

function Get-R79Environment([string]$Setting, [string]$T4hDir, [string]$Plan = '') {
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = $T4hDir; R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    if ($Plan) { $Environment['R79_ROD_FAULT_PLAN'] = $Plan }
    return $Environment
}

function Get-DoneCode([string]$StepName, [string]$Name) {
    $DonePath = "$RunsRoot\$StepName.done"
    if (-not (Test-Path -LiteralPath $DonePath)) { Stop-Step 3 "step $StepName is not done ($DonePath)" }
    return [string](Get-Content -Raw -LiteralPath $DonePath | ConvertFrom-Json).codes.$Name
}

function Read-Decision([string]$Path, [string]$Sha256, [string[]]$Statuses) {
    # the 12b P-pred decision of T8 (status and blocks): its sha256 as given and a status of
    # $Statuses, else not usable (2)
    if (-not (Test-Path -LiteralPath $Path)) { Stop-Step 2 "decision $Path missing" }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
    if ($Actual -ne $Sha256.ToLower()) { Stop-Step 2 "decision $Path sha256 $Actual is not $Sha256" }
    $Document = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
    if ($Statuses -notcontains [string]$Document.status) { Stop-Step 2 "decision status $($Document.status) (needs $($Statuses -join ' / '))" }
    $StepState.Codes['decision_file'] = $Path
    $StepState.Codes['decision_sha256'] = $Actual
    $StepState.Codes['decision_status'] = [string]$Document.status
    return $Document
}

function Assert-S8cSeal([string]$Rules, [string]$Sha256) {
    # spec 4: steps 8 .. 10 come after the S8-C seal; the sealed S8-C document and its sha256
    # are given (a missing file or another sha256 refuses, 2)
    if (-not $Rules -or -not $Sha256) { Stop-Step 2 'steps 8 .. 10 need -S8cRules and -S8cSha256 (the S8-C seal)' }
    if (-not (Test-Path -LiteralPath $Rules)) { Stop-Step 2 "S8-C document $Rules missing" }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Rules).Hash.ToLower()
    if ($Actual -ne $Sha256.ToLower()) { Stop-Step 2 "S8-C document sha256 $Actual is not $Sha256" }
    $StepState.Codes['s8c_rules'] = $Rules
    $StepState.Codes['s8c_sha256'] = $Actual
}

# --- dry run overrides (no process, no tool; the commands go into the step record) -------------
if ($IsEd8Dry) {
    function Start-Run {
        param([string]$Label, [string]$MaskHex, [string[]]$Arguments, [hashtable]$Environment = @{},
            [string]$WrapOutput = '', [string]$TaskType, [int]$Workers)
        $Python = $Arguments
        if ($WrapOutput) { $Python = @("$Coupled/jp3_run_identity.py", 'wrap', $WrapOutput, '--', $DynamicsPython, '-I', '-B') + $Arguments }
        $All = $RunPrefix + $Python
        Assert-PlainArguments $All
        $StepState.Commands.Add([ordered]@{ label = $Label; mask = $MaskHex; environment = $Environment
            workers = $Workers; command = "$RunExe $($All -join ' ')"; dry_run = $true })
        return [pscustomobject]@{ Label = $Label; MaskHex = $MaskHex; TaskType = $TaskType; Workers = $Workers }
    }
    function Wait-Runs([object[]]$Runs) { foreach ($Run in $Runs) { $StepState.Codes["run:$($Run.Label)"] = 'dry' } }
    function Invoke-Tool([string]$Label, [string[]]$Arguments) {
        $All = $RunPrefix + $Arguments
        Assert-PlainArguments $All
        $StepState.Commands.Add([ordered]@{ label = $Label; command = "$RunExe $($All -join ' ')"; dry_run = $true })
        $StepState.Codes["tool:$Label"] = 'dry'
        return 0
    }
    function Invoke-IdentityCheck { $StepState.Codes['identity_check'] = 'dry' }
}
