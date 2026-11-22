#Requires -Version 7
# 436.9 J-P3 edition 4a: shared settings and helpers of the run steps (1) .. (7).
#
# Rules: addendum 4a-5 4 (run identity), 5.1 (exit codes), 5.2 (folders), 5.3 (attempts);
# prelaunch audit M-1 / M-2; placement = the compute-scheduler-expert table (2026-11-21).
# Every step script dot-sources this file. Nothing in this file starts a run by itself.
#
# Folders under $RunsRoot: STEP_aN\ (outputs of attempt N), its judge\ (judge reports), its
# logs\ (stdout, stderr, sampler json), STEP.done / STEP.stop (step markers, never
# overwritten), _identity_checks\ (baseline_check reports; its --out may not lie in its input).
# A step refuses an existing attempt folder, and any attempt once the step is done.
# Exit codes of a step script: 0 done, 1 / 2 / 3 = the judge tool's code (4a-5 5.1: stop),
# 3 also for a failed run or a broken precondition (commit, tree, fixed input).

Set-StrictMode -Version 3
$ErrorActionPreference = 'Stop'

# --- run commit and paths -------------------------------------------------------------------
$RunCommit = '78fd5d2d03e40ac7d9143429f602b58255c762fc'
# decision 2: one commit for steps (1) .. (7), the locked worktree z4369-jp3 (remedy 10)
$RunShort = $RunCommit.Substring(0, 8)
$Worktree = 'C:\workspace\outrigger_control\.claude\worktrees\z4369-jp3'
$MainRoot = 'C:\workspace\outrigger_control'
$Analysis = "$MainRoot\06_analysis"
$CauseDir = "$Analysis\02_control\j_p3_cause"
$PrelaunchDir = "$CauseDir\prelaunch_j9"
$RunsRoot = "$CauseDir\j9_runs\$RunShort"
$IdentityChecks = "$RunsRoot\_identity_checks"
$ResumeK1 = "$Analysis\03_hydraulic\coupled\v5\resume_k1"
$BaselineDir = "$CauseDir\baseline_221456d"
$Path1Dir = "$Analysis\02_control\verif_matrix\v5_resume_4368\judge_932f1fb\harness_path1"
$RunExe = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$DynamicsPython = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$DevPython = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$VerifTools = 'C:\Users\jinbeom\.claude\tools\verif'
$SchedTools = 'C:\Users\jinbeom\.claude\tools\cpu-scheduler'
$Coupled = '04_scripts/04_hydraulic/coupled'
$RunPrefix = @('-I', '-B')
# Direct dynamics-dev python.exe -I -B: the same call as baseline 221456d and the stored h10/H-6 runs
# (identity "python"; resume_k1_steps.py:40,93). MKL_THREADING_LAYER=TBB comes from the run environment below.
# (Decided 2026-11-21 by the main session: match the stored runs' interpreter call.)

# --- thread variables (identity of the stored h10 / H-6 runs and the baseline: all 1, TBB) --
$ThreadEnvironment = [ordered]@{
    MKL_NUM_THREADS      = '1'
    OMP_NUM_THREADS      = '1'
    NUMBA_NUM_THREADS    = '1'
    OPENBLAS_NUM_THREADS = '1'
    MKL_THREADING_LAYER  = 'TBB'
}

# --- r79 run condition (source: resume_k1_steps.py dg3_steps lines 390-397 of the stored H-6:
# R72_PATH per_leg (R79_ENV, line 101; H-6 meta r72_path per_leg), LAS_T3_DG3_LAS / K1 / P3 on,
# R79_T4H_DIR the run's own folder; R79_ROD_MODEL: dyn_map = the H-6 meta rod_model (VBH, the
# old plant), plant_truth for VBJ / VBJ0 (addendum 4a-2 B2, jp3_tjr_judge.py docstring;
# jp3_dryrun_evidence.r79_environment for the dry runs).
$R79Common = @{
    R72_PATH       = 'per_leg'
    LAS_T3_DG3_LAS = 'on'
    LAS_T3_DG3_K1  = 'on'
    LAS_T3_DG3_P3  = 'on'
}
$R79RodModel = @{ VB = 'dyn_map'; VBH = 'dyn_map'; VBJ = 'plant_truth'; VBJ0 = 'plant_truth'
    VBK = 'plant_truth'; VBK0 = 'plant_truth' }
# edition 5 6.3.1: VBK = the VBJ plant (③ rev 6) and VBK0 = the VBJ0 plant, each with a rod
# fault plan (R79_ROD_FAULT_PLAN, X-10)
$R79Variables = @('R79_V5_SETTING', 'R79_T4H_DIR', 'R79_ROD_MODEL', 'R72_PATH',
    'LAS_T3_DG3_LAS', 'LAS_T3_DG3_K1', 'LAS_T3_DG3_P3', 'R79_AFFINITY', 'R79_CANDIDATE',
    'R79_TRACE', 'R79_LEVELS', 'R79_SEEDS', 'R79_SET', 'R79_FILTER', 'R79_ROD_FAULT_PLAN',
    'R79_ROD_FAULT_PLAN_SHA256')
# the r79 / r67 / r72 screen variables read by r79_sensor_screen.py (734, 863, 905, 964, 978,
# 1186-1208), r67_g1_screen.py and r72_g6_screen.py; Set-RunEnvironment also clears any other
# variable of these prefixes left in the shell (re-audit R-e)
$ScreenVariablePattern = '^(R79_|R72_|R67_|LAS_T3_)'

# --- fixed inputs (the values of jp3_fixed_inputs.py at the run commit; Assert-FixedInputs
# checks the files and that module) --------------------------------------------------------
$FixedInputs = [ordered]@{
    H10_SHA256                    = @("$ResumeK1\h10_reuse_rerun.jsonl",
        'ce526b1f71e635e6b80d538f36841ece01710af46f02acb4b3fa1355a5a4dcb3')
    MAIN_JSONL_SHA256             = @("$Analysis\03_hydraulic\coupled\v5\main.jsonl",
        '9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e')
    H6_SHA256                     = @("$ResumeK1\h6_dg3_v4on.json",
        'ea0ab94c81e58eeb83ab2b6a63494a56c16bcd4165a62de47eba5efd03f23c89')
    NOISE_VB_SHA256               = @("$ResumeK1\h8_noise_VB.json",
        '2219ab9782b22fbe07e6c1f90e8b49c6b3703b0575b5d7cfb7d72b4f067bec43')
    BASELINE_SUMS_SHA256          = @("$BaselineDir\SHA256SUMS",
        '197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361')
    GRID_SHA256                   = @("$ResumeK1\h9_grid\grid_r67_top.json",
        '7160f9f19b497ea264e9dd90c58c2da25540ded51e8510197205cf91f00bd827')
    DRY_KEYS_FILE_SHA256          = @("$CauseDir\j4a_remedy_b06e409e\dryrun_selection_r79_key.txt",
        '1a79e02fc33ae8844d0cd5672e9e5e745215c354e58e9a8095376939c4335e74')
    STORED_H6_R79_JUDGE_SHA256    = @("$Path1Dir\h6_r79_judge.json",
        'd95627ac83a0bfc165df763e898956fbdcbf7c299fb2d9face8915ef478ed57b')
    STORED_H6_JUDGE_SHA256        = @("$Path1Dir\h6_judge.json",
        'f8352c5d12d31aebcffe2a4bc5bdfa7919e605a3f3261da8455640df3bad0d0b')
    STORED_H6_L1_REFERENCE_SHA256 = @("$Path1Dir\h6_L1_reference.json",
        'a591c3a8c5b3ad5822877e7f69ce2acf75e4cc96fff139a52fef7b6439d56ce7')
    H10_T4H_SUMS_SHA256           = @("$PrelaunchDir\h10_reuse_rerun_t4h.SHA256SUMS",
        '3d0ed49a5044c7dd223940e782b6d280a833ffaeb9916347f8cc0622000cc3ac')
    H6_T4H_SUMS_SHA256            = @("$PrelaunchDir\h6_dg3_v4on_t4h.SHA256SUMS",
        'c426f5185adc04102dca229b9a4257db71e2cc8c5933f392a083086e186ce655')
}

function Get-FixedPath([string]$Name) { return $FixedInputs[$Name][0] }

# --- step state -----------------------------------------------------------------------------
$StepState = @{ Name = $null; Folder = $null; Commands = [System.Collections.Generic.List[object]]::new()
    Started = $null; Codes = [ordered]@{}; PreviousStops = @(); ClearedVariables = @() }
$RecordCodeTools = @('tool:base_judge_compare')
# 4a-5 5.1 / erratum 1 R-2: base-judge-compare exit 1 is a record, not a judged failure

function Write-JsonFile([string]$Path, $Value) {
    if (Test-Path -LiteralPath $Path) { throw "$Path exists (never overwritten)" }
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function Stop-Step([int]$Code, [string]$Reason) {
    # 4a-5 5.1: a non-zero code stops the step; the marker keeps the reason and the commands.
    $Record = [ordered]@{ step = $StepState.Name; folder = $StepState.Folder; exit_code = $Code
        reason = $Reason; commit = $RunCommit; started = $StepState.Started
        stopped = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'); codes = $StepState.Codes
        previous_attempts = $StepState.PreviousStops; cleared_variables = $StepState.ClearedVariables
        commands = $StepState.Commands }
    if ($null -ne $StepState.Folder) {
        $RecordPath = "$($StepState.Folder)\step_record.json"
        if (-not (Test-Path -LiteralPath $RecordPath)) { Write-JsonFile $RecordPath $Record }
    }
    $StopPath = "$RunsRoot\$($StepState.Name).stop"
    if (Test-Path -LiteralPath $StopPath) { $StopPath = "$RunsRoot\$($StepState.Name).stop.$(Get-Date -Format 'yyyyMMddHHmmss')" }
    Write-JsonFile $StopPath $Record
    Write-Host "STOP $($StepState.Name) exit $Code - $Reason"
    exit $Code
}

function Assert-RunCommit {
    # 4a-5 4: the worktree HEAD is the run commit and its tracked tree is clean; a git failure
    # is never read as clean.
    $Head = (& git -C $Worktree rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git rev-parse failed (no identity)' }
    if ($Head.Trim() -ne $RunCommit) { Stop-Step 3 "worktree HEAD $Head is not the run commit $RunCommit" }
    $Status = (& git -C $Worktree status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git status failed (no identity)' }
    if ($Status) { Stop-Step 3 "worktree not clean: $($Status -join '; ')" }
}

function Assert-FixedInputs {
    foreach ($Name in $FixedInputs.Keys) {
        $Path, $Expected = $FixedInputs[$Name]
        if (-not (Test-Path -LiteralPath $Path)) { Stop-Step 3 "fixed input $Name missing: $Path" }
        $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
        if ($Actual -ne $Expected) { Stop-Step 3 "fixed input $Name sha256 $Actual is not $Expected" }
    }
    # the same values in jp3_fixed_inputs.py of the run commit
    $Code = 'import sys; sys.path.insert(0, sys.argv[1]); import jp3_fixed_inputs as f; ' +
        '[print(n, getattr(f, n)) for n in sys.argv[2:]]'
    $Lines = @(& $DevPython -I -B -c $Code "$Worktree\04_scripts\04_hydraulic\coupled" @($FixedInputs.Keys))
    if ($LASTEXITCODE -ne 0 -or $Lines.Count -ne $FixedInputs.Count) { Stop-Step 3 'jp3_fixed_inputs import failed' }
    foreach ($Line in $Lines) {
        $Name, $Value = $Line -split ' ', 2
        if ($FixedInputs[$Name][1] -ne $Value) { Stop-Step 3 "jp3_fixed_inputs.$Name $Value differs from this file" }
    }
}

function Set-RunEnvironment {
    foreach ($Name in $ThreadEnvironment.Keys) { Set-Item -Path "Env:$Name" -Value $ThreadEnvironment[$Name] }
    $env:PYTHONDONTWRITEBYTECODE = '1'
    foreach ($Name in $R79Variables) { Remove-Item -Path "Env:$Name" -ErrorAction SilentlyContinue }
    $Left = @(Get-ChildItem Env: | Where-Object { $_.Name -match $ScreenVariablePattern })
    foreach ($Item in $Left) { Remove-Item -Path "Env:$($Item.Name)" }
    $StepState.ClearedVariables = @($Left | ForEach-Object { $_.Name })
}

function Set-OwnAffinity([string]$MaskHex) {
    # children inherit the affinity of this process at their creation
    (Get-Process -Id $PID).ProcessorAffinity = [IntPtr][Convert]::ToInt64($MaskHex, 16)
}

function Get-CoreKind([string]$MaskHex) {
    # i7-14700: logical 0-15 = P cores (8 x 2), 16-27 = E cores
    $Value = [Convert]::ToInt64($MaskHex, 16)
    if (($Value -band 0xFFFF) -eq 0) { return 'E' }
    return 'P'
}

function Get-StepFolder([string]$StepName) {
    # the folder of a done step (from its .done marker)
    $DonePath = "$RunsRoot\$StepName.done"
    if (-not (Test-Path -LiteralPath $DonePath)) { Stop-Step 3 "step $StepName is not done ($DonePath)" }
    return (Get-Content -Raw -LiteralPath $DonePath | ConvertFrom-Json).folder
}

function Read-PreviousStops([string]$StepName) {
    # re-audit N-2 (4a-5 5.2 fourth item, 5.4): the earlier attempts' stop records go into this
    # attempt's record; an earlier judge tool exit 1 (a failure: results seen) refuses any new
    # attempt (base-judge-compare 1 is a record and does not count)
    $Stops = @(Get-ChildItem -LiteralPath $RunsRoot -File | Where-Object { $_.Name -like "$StepName.stop*" })
    foreach ($Stop in $Stops) {
        $Previous = Get-Content -Raw -LiteralPath $Stop.FullName | ConvertFrom-Json
        $StepState.PreviousStops += [ordered]@{ path = $Stop.FullName; folder = $Previous.folder
            exit_code = $Previous.exit_code; reason = $Previous.reason }
        if ($null -eq $Previous.codes) { continue }
        $Failed = @($Previous.codes.PSObject.Properties | Where-Object {
                $_.Name -like 'tool:*' -and $RecordCodeTools -notcontains $_.Name -and $_.Value -eq 1 })
        if ($Failed.Count) {
            Stop-Step 2 "refused: an earlier attempt failed ($($Failed[0].Name) exit 1 in $($Stop.Name)); 4a-5 5.4: a failure is never run again"
        }
    }
}

function Get-StepCode([int[]]$Codes) {
    # re-audit N-2: one judge failure (1) makes the step code 1 whatever the others are
    if ($Codes -contains 1) { return 1 }
    return ($Codes | Measure-Object -Maximum).Maximum
}

function Initialize-Step([string]$StepName, [int]$Attempt, [string[]]$Requires) {
    $StepState.Name = $StepName
    $StepState.Started = Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'
    New-Item -ItemType Directory -Force -Path $RunsRoot, $IdentityChecks | Out-Null
    if (Test-Path -LiteralPath "$RunsRoot\$StepName.done") { Stop-Step 2 "step $StepName is done already (4a-5 5.4: results seen)" }
    Read-PreviousStops $StepName
    $Folder = "$RunsRoot\${StepName}_a$Attempt"
    if (Test-Path -LiteralPath $Folder) { Stop-Step 2 "$Folder exists (4a-5 5.2: a new attempt is a new folder)" }
    foreach ($Required in $Requires) { Get-StepFolder $Required | Out-Null }
    Set-Location -LiteralPath $Worktree
    Assert-RunCommit
    Assert-FixedInputs
    Set-RunEnvironment
    New-Item -ItemType Directory -Path $Folder, "$Folder\judge", "$Folder\logs" | Out-Null
    $StepState.Folder = $Folder
    return $Folder
}

function Assert-PlainArguments([string[]]$Arguments) {
    # Start-Process joins its argument list with spaces: no argument may hold one
    foreach ($Argument in $Arguments) {
        if ($Argument -match '\s') { Stop-Step 3 "argument with a space: '$Argument'" }
    }
}

function Start-Run {
    # One run in the dynamics-dev environment (direct python.exe), detached; its sampler beside it.
    # WrapOutput: jp3_run_identity.py wrap writes the output's STEM.identity.json (start / end).
    param([string]$Label, [string]$MaskHex, [string[]]$Arguments, [hashtable]$Environment = @{},
        [string]$WrapOutput = '', [string]$TaskType, [int]$Workers)
    $Folder = $StepState.Folder
    $Python = $Arguments
    if ($WrapOutput) {
        $Python = @("$Coupled/jp3_run_identity.py", 'wrap', $WrapOutput, '--', $DynamicsPython, '-I', '-B') + $Arguments
    }
    $All = $RunPrefix + $Python
    Assert-PlainArguments $All
    foreach ($Name in $Environment.Keys) { Set-Item -Path "Env:$Name" -Value $Environment[$Name] }
    Set-OwnAffinity $MaskHex
    $Process = Start-Process -FilePath $RunExe -ArgumentList $All -WorkingDirectory $Worktree `
        -RedirectStandardOutput "$Folder\logs\$Label.log" -RedirectStandardError "$Folder\logs\$Label.err" `
        -PassThru -WindowStyle Hidden
    $null = $Process.Handle  # keeps the exit code readable after the process ended
    foreach ($Name in $Environment.Keys) { Remove-Item -Path "Env:$Name" -ErrorAction SilentlyContinue }
    $Sampler = Start-Process -FilePath $DevPython -ArgumentList @('-I', '-B', "$SchedTools\sample.py",
        '--pid', "$($Process.Id)", '--out', "$Folder\logs\$Label.sample.json") -PassThru -WindowStyle Hidden
    $StepState.Commands.Add([ordered]@{ label = $Label; mask = $MaskHex; environment = $Environment
        command = "$RunExe $($All -join ' ')"; pid = $Process.Id })
    return [pscustomobject]@{ Label = $Label; Process = $Process; Sampler = $Sampler
        MaskHex = $MaskHex; TaskType = $TaskType; Workers = $Workers }
}

function Wait-Runs([object[]]$Runs) {
    # every run to its end; a run that failed stops the step (4a-5 5.3: a new attempt folder)
    foreach ($Run in $Runs) { $Run.Process.WaitForExit() }
    foreach ($Run in $Runs) { $Run.Sampler.WaitForExit(120000) | Out-Null }
    Write-RunRecords $Runs
    $Failed = @($Runs | Where-Object { $_.Process.ExitCode -ne 0 })
    foreach ($Run in $Runs) { $StepState.Codes["run:$($Run.Label)"] = $Run.Process.ExitCode }
    if ($Failed.Count) {
        Stop-Step 3 "runs failed: $(($Failed | ForEach-Object { "$($_.Label)=$($_.Process.ExitCode)" }) -join ', ')"
    }
}

function Write-RunRecords([object[]]$Runs) {
    # cpu-scheduler history (record.py --from-sample), one line per run
    foreach ($Run in $Runs) {
        $Sample = "$($StepState.Folder)\logs\$($Run.Label).sample.json"
        if (-not (Test-Path -LiteralPath $Sample)) { Write-Host "no sampler file for $($Run.Label)"; continue }
        & $DevPython -I -B "$SchedTools\record.py" --task-id "j9-$RunShort-$($Run.Label)" `
            --task-type $Run.TaskType --core (Get-CoreKind $Run.MaskHex) --from-sample $Sample `
            --mask $Run.MaskHex --workers $Run.Workers --note "436.9 J4a step $($StepState.Name)" |
            Out-File -LiteralPath "$($StepState.Folder)\logs\$($Run.Label).record.json" -Encoding utf8NoBOM
    }
}

function Invoke-Tool([string]$Label, [string[]]$Arguments) {
    # a judge or record tool in dynamics-dev, synchronous; returns its exit code
    $All = $RunPrefix + $Arguments
    Assert-PlainArguments $All
    $StepState.Commands.Add([ordered]@{ label = $Label; command = "$RunExe $($All -join ' ')" })
    & $RunExe @All *> "$($StepState.Folder)\logs\$Label.log"
    $Code = $LASTEXITCODE
    $StepState.Codes["tool:$Label"] = $Code
    return $Code
}

function Invoke-Judge([string]$Label, [string[]]$Arguments, [int[]]$ContinueCodes = @(0)) {
    # 4a-5 5.1: 0 goes on; 1 / 2 / 3 stop (base-judge-compare 1 is a record: ContinueCodes)
    $Code = Invoke-Tool $Label $Arguments
    if ($ContinueCodes -notcontains $Code) { Stop-Step $Code "$Label exit $Code" }
    return $Code
}

function Invoke-IdentityCheck {
    # 4a-5 4: before any judge tool, every identity record of the step folder names the run
    # commit with a full head, a clean tree and no git failure mark (exit 0), else not judgeable
    $Folder = $StepState.Folder
    $Out = "$IdentityChecks\$(Split-Path -Leaf $Folder).md"
    $All = @('-I', '-B', "$VerifTools\baseline_check.py", 'identity', '--repo', $Worktree, $Folder,
        '--expect-commit', $RunCommit, '--mtime', '--out', $Out)
    $StepState.Commands.Add([ordered]@{ label = 'identity_check'; command = "$DevPython $($All -join ' ')" })
    & $DevPython @All *> "$Folder\logs\identity_check.log"
    $Code = $LASTEXITCODE
    $StepState.Codes['identity_check'] = $Code
    if ($Code -ne 0) { Stop-Step 2 "baseline_check identity exit $Code ($Out)" }
}

function Read-ReportField([string]$Path, [string]$Field) {
    # a sha field of a tool report (not a judgement value)
    $Value = (Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json).$Field
    if (-not $Value) { Stop-Step 3 "$Path has no $Field" }
    return [string]$Value
}

# --- P-1 output list (re-audit N-5, 4a-5 3.4: the L1 extract sha from the fixed list) ------
$P1OutputsList = "$PrelaunchDir\P1_OUTPUTS_$RunShort.SHA256SUMS"
$P1OutputNames = @('h6_base_judge.json', 'h6_base_judge_L1_reference.json')

function Get-RepoPath([string]$Path) {
    # the path relative to the main checkout, '/' separators (the FIXED_INPUTS form)
    return $Path.Substring($MainRoot.Length + 1).Replace('\', '/')
}

function Write-P1Outputs([string]$Folder) {
    # step 1: the sha256 list of the P-1 judge file and L1 extract (the main session commits it)
    if (Test-Path -LiteralPath $P1OutputsList) { Stop-Step 2 "$P1OutputsList exists (never overwritten)" }
    $Lines = foreach ($Name in $P1OutputNames) {
        $Path = "$Folder\$Name"
        "$((Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()) *$(Get-RepoPath $Path)"
    }
    [IO.File]::WriteAllText($P1OutputsList, ($Lines -join "`n") + "`n")
    $StepState.Codes['p1_outputs_list'] = Get-RepoPath $P1OutputsList
}

function Assert-P1Outputs([string]$P1Folder) {
    # step 6: the list is committed (tracked, no change against HEAD), its two lines are the P-1
    # files as they are and the bj.json values; else not judgeable (exit 2)
    $Relative = Get-RepoPath $P1OutputsList
    & git -C $MainRoot ls-files --error-unmatch -- $Relative *> $null
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative is not tracked by git (commit it after step 1)" }
    & git -C $MainRoot diff --quiet HEAD -- $Relative
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative differs from HEAD (or git failed)" }
    $Listed = @{}
    foreach ($Line in (Get-Content -LiteralPath $P1OutputsList)) {
        if (-not $Line.Trim()) { continue }
        $ListedSha, $ListedPath = $Line -split ' \*', 2
        $Listed[$ListedPath] = $ListedSha
    }
    $Report = "$P1Folder\judge\bj.json"
    $Expected = @{ 'h6_base_judge.json' = (Read-ReportField $Report 'judge_sha256')
        'h6_base_judge_L1_reference.json' = (Read-ReportField $Report 'l1_reference_sha256') }
    foreach ($Name in $P1OutputNames) {
        $Path = "$P1Folder\$Name"
        $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
        $Sha = $Listed[(Get-RepoPath $Path)]
        if ($Sha -ne $Expected[$Name] -or $Sha -ne $Actual) {
            Stop-Step 2 "P-1 output $($Name) - list $Sha, bj.json $($Expected[$Name]), file $Actual differ"
        }
    }
}

# --- rerun match (addenda 4a-6 G-4, 4a-7 2) -------------------------------------------------
$PreviousRunCommit = 'fa997f4cb2dba9820118c6d38e469ebb137110e2'
$PreviousRunsRoot = "$CauseDir\j9_runs\$($PreviousRunCommit.Substring(0, 8))"
# 4a-7 2.1: the attempt whose steps (1) .. (4b) were seen (preserved in master); b51ed6e1 is not
# read again (same by transitivity)
$MatchAllowedPaths = @('04_scripts/04_hydraulic/coupled/jp3_tjr_judge.py',
    '04_scripts/04_hydraulic/coupled/jp3_rerun_match.py',
    '04_scripts/04_hydraulic/coupled/jp3_baseline_compare.py',
    '04_scripts/04_hydraulic/coupled/jp3_case_judge.py')
$MatchAllowedPrefix = '05_tests/'
# 4a-7 2.2: the run commit changes judge tools only - the t8 judge (5 H-1), the match tool
# (5 H-3) and the J-P3 judged-line evidence of erratum 1 9 (baseline_compare, case-f, t12) -
# and the tests; any other path (03_src, the harness, the runners) stops before step (1)

function Assert-SimulationPathsUnchanged {
    # 4a-7 2.2: git diff --stat of the previous attempt's commit and the run commit into the run
    # record; a changed path outside the t8 judge tool, the match tool and the tests stops (3)
    $Log = "$($StepState.Folder)\logs\git_diff_stat_$($PreviousRunCommit.Substring(0, 8)).txt"
    $Stat = @(& git -C $Worktree diff --stat $PreviousRunCommit $RunCommit)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git diff --stat failed (no identity)' }
    [IO.File]::WriteAllText($Log, ($Stat -join "`n") + "`n")
    $Names = @(& git -C $Worktree diff --name-only $PreviousRunCommit $RunCommit)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git diff --name-only failed (no identity)' }
    $StepState.Codes['git_diff_stat'] = Get-RepoPath $Log
    $Outside = @($Names | Where-Object { $MatchAllowedPaths -notcontains $_ -and -not $_.StartsWith($MatchAllowedPrefix) })
    if ($Outside.Count) {
        Stop-Step 3 "4a-7 2.2: $($Outside.Count) changed paths outside the t8 judge tool, the match tool and the tests ($($Outside[0]) ...); ask the user"
    }
}

function Invoke-RerunMatch([string]$Item) {
    # after the step's judge tool: the reproducible values of this attempt against fa997f4c
    # (jp3_rerun_match.py: names only in its report); 1 differs / 2 missing / 3 error stop
    $Folder = $StepState.Folder
    $CodesFile = "$Folder\logs\codes_for_rerun_match.json"
    $StepState.Codes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $CodesFile -Encoding utf8NoBOM
    Invoke-Judge "rerun_match_$Item" @("$Coupled/jp3_rerun_match.py", '--old', $PreviousRunsRoot,
        '--new', $RunsRoot, '--items', $Item, '--new-folder', $Folder, '--new-codes', $CodesFile,
        '--out', "$Folder\judge\rerun_match_$Item.json") | Out-Null
}

function Complete-Step {
    Assert-RunCommit
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
