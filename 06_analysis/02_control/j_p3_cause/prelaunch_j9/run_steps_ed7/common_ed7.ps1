#Requires -Version 7
# 436.9 J-P3 edition 7: shared settings of the edition 7 run steps (jp3_remedy_spec_v7.md
# revision 6, sha256 10902ffd...: 4 steps 5 .. 10, 5.1 (iv), 5.2). The edition 4a helpers come
# from ..\run_steps\common.ps1 and ..\run_steps\record_helper.ps1 (unchanged); core_kind_ed7.ps1
# replaces their Get-CoreKind (P / E / mixed). This file sets the edition 7 run commit, folders,
# inputs and the start checks.
#
# Run only (spec 4 step 5a, 5.2): the run commit C holds no judge. The steps run the lines and
# record them; every judgement (P7-1 / P7-2 / P7-3 / P7-9 and steps 6 .. 10, J7 and ③ rev 7
# included) is made later at the judge commit T (the child of C) and is not judgeable before T
# and its audit. P7-10 (scope) and P7-4 (unit suite) are the checks of C itself: every step
# asserts the scope at its start (Get-ScopeProblem), step5_impl_ed7.ps1 -Part scope keeps the
# evidence, full_suite_ed7.ps1 runs the suite. The run order is kept by the .done markers; when
# to wait for a judgement of T before the next step is the main session's decision (spec 4
# steps 6 .. 10: "순서와 멈춤은 판 6 4절과 같다").
#
# The run commit and the run worktree are read from prelaunch_j9\ed7_run_config.json of the main
# checkout (the main session writes it from ed7_run_config.template.json after the run commit:
# it cannot name its own commit). A placeholder left, a missing file or another HEAD stops 3.
#
# Run order (the main session launches every step; each needs the .done of the ones before):
#   1. step5_impl_ed7.ps1 -Part scope   P7-10 evidence (diff of C against b46bdf8f), no run
#   2. step_l1ref_ed7.ps1               the four L1 reference runs (12b L1_VBM0 / L1_VBM on
#                                       l1_keys_12b.txt, 12a L1a_VBM0 / L1a_VBM on
#                                       l1_keys_d3c6c57e.json), before any 12a / 12b output
#   3. step5_impl_ed7.ps1 -Part t8 | cases | probe   P7-1 T8 (44), P7-2 cases E / F (10),
#                                       P7-3 / P7-9 probe arm a2 (114), in this order
#   4. step6_confirm_ed7.ps1            G1 171 (ed7_keys confirm_g1_grid171.json) + D 24
#                                       (ed7_probe.py --part d) = 195 (spec 4 step 6, 6.3)
#   5. step7_j9main_ed7.ps1             ed7_j9_main 388 (6.2)
#   6. step8_sens_ed7.ps1               ed7_keys sens_keys_ed7.json 460 (6.2)
#   7. step9_dg3_ed7.ps1                T-JR-12a VBM / VBM0 on the 135 H-6 keys (6.4)
#   8. step10a_plan_ed7.ps1             the T-JR-12b plan (jp3_12b_plan.py --edition 7, scan
#                                       widened to the edition 6 / 7 outputs, Y7-7)
#   9. step10b_vbkm0_ed7.ps1 -Phase base   VBKM0 b1 / b2; then the P-pred decision of T (not
#      here); when it says needs_b4: step10b_vbkm0_ed7.ps1 -Phase b4 -Decision ... ; and when it
#      says decided: step10c_vbkm_ed7.ps1 -Decision ...  (the VBKM blocks of the decision)
# Every step records its identity at the start and at the end (HEAD, is_clean, 03_src tree id):
# a start not equal to the run commit stops 3, an end that differs stops 3 and the step's
# outputs are not used (no .done). Every output path of a step is new: the attempt folder
# STEP_aN may not exist and every output file is asserted absent before its run (spec 4 step 6,
# audit M-7: run_v5 / ed7_probe append to an existing file and skip its keys).
#
# Dry run (no simulation, no tool, nothing in the main checkout): ED7_DRY_RUN_ROOT=<scratch
# folder> holds ed7_run_config.json and receives j9_runs\RUN8\ with the step records;
# Start-Run and Invoke-Tool record their commands only (dry_run_ed7.ps1).

. "$PSScriptRoot\..\run_steps\common.ps1"
. "$PSScriptRoot\..\run_steps\record_helper.ps1"
. "$PSScriptRoot\core_kind_ed7.ps1"
$Ed7StepsDir = $PSScriptRoot

# --- dry run ---------------------------------------------------------------------------------
$Ed7DryRoot = [string]$env:ED7_DRY_RUN_ROOT
$IsEd7Dry = [bool]$Ed7DryRoot

# --- the sealed spec and the implementation commit ---------------------------------------------
$SpecV7 = "$CauseDir\jp3_remedy_spec_v7.md"
$SpecV7Sha256 = '10902ffdb763aa092588b1be0dd13f55874826b489f9aa9f1351dd7f48c1da45'
$ImplCommit = 'b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9'
# spec 5.1: C is the one child of b46bdf8f
$ControllerTree = '0cffdbdfc64f6a3daa855f5c2f2fdaf1c7dbf04f'
# git rev-parse C:03_src = b46bdf8f's 03_src with the JP3_SPEC_EDITION_V7 lines (P7-10)

# P7-10 / 5.1 (i) .. (iv): the paths C may change against b46bdf8f
$ScopeFiles = @('03_src/outrigger_sim/control/extend_start_bound.py',
    '04_scripts/04_hydraulic/coupled/run_v5.py',
    '05_tests/unit/test_ed7_run_commit.py')
$ScopePrefix = '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed7/'
$SrcHunk = '@@ -197,5 +197,5 @@'
$SrcConstantLine = '+JP3_SPEC_EDITION_V7 = "10902ffd"'
# 5.1 (i), audit M-4: the 03_src diff is the constant line and its docstring (197 .. 201) only

# --- run commit and paths (the main session's config file) -----------------------------------
$Ed7Placeholder = '^<ED7_'
$Ed7ConfigFile = if ($IsEd7Dry) { "$Ed7DryRoot\ed7_run_config.json" } else { "$PrelaunchDir\ed7_run_config.json" }

function Exit-Ed7([int]$Code, [string]$Reason) {
    # a stop before any step folder exists: `exit` in this dot-sourced file (or in a function)
    # would return to the step script, so the process ends here with the code
    Write-Host "STOP: $Reason"
    [Console]::Out.Flush()
    [Environment]::Exit($Code)
}

function Get-Ed7ConfigProblem($Config) {
    # why the config file cannot name the run ($null: it can)
    if ($null -eq $Config) { return "$Ed7ConfigFile missing (copy ed7_run_config.template.json and fill it in)" }
    foreach ($Value in @($Config.run_commit, $Config.worktree)) {
        if ([string]$Value -match $Ed7Placeholder) { return "$Ed7ConfigFile still holds $Value" }
    }
    if ([string]$Config.run_commit -notmatch '^[0-9a-f]{40}$') { return 'run commit is not a full sha' }
    return $null
}
$Ed7Config = if (Test-Path -LiteralPath $Ed7ConfigFile) { Get-Content -Raw -LiteralPath $Ed7ConfigFile | ConvertFrom-Json } else { $null }
$Ed7ConfigProblem = Get-Ed7ConfigProblem $Ed7Config
if ($Ed7ConfigProblem) { Exit-Ed7 3 $Ed7ConfigProblem }
$RunCommit = [string]$Ed7Config.run_commit
$Worktree = [string]$Ed7Config.worktree
if (-not $Ed7StepsDir.StartsWith("$Worktree\", [StringComparison]::OrdinalIgnoreCase)) {
    Exit-Ed7 3 "run the steps from the run worktree ($Worktree), not $Ed7StepsDir (the run commit's scripts)"
}

$RunShort = $RunCommit.Substring(0, 8)
$RunsParent = if ($IsEd7Dry) { "$Ed7DryRoot\j9_runs" } else { "$CauseDir\j9_runs" }
$RunsRoot = "$RunsParent\$RunShort"
$IdentityChecks = "$RunsRoot\_identity_checks"

# --- inputs (main checkout) with their sha256 -------------------------------------------------
$KeysSealDir = "$CauseDir\ed7_design\keys_seal_b46bdf8f"
$Ed7Inputs = [ordered]@{
    spec_v7     = @($SpecV7, $SpecV7Sha256)
    g1_keys     = @("$KeysSealDir\confirm_g1_grid171.json",
        '684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec')   # spec 5.1, 6.3
    sens_keys   = @("$KeysSealDir\sens_keys_ed7.json",
        'be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b')   # spec 5.1, 6.2
    l1_keys_12b = @("$PrelaunchDir\ed5_inputs\l1_keys_12b.txt",
        '9f815533c0deb44925134465fe90e0f508c1819ae2c4c34bf4f3b651b6a63ca5')   # 12b L1 keys (ed6)
    l1_keys_12a = @("$PrelaunchDir\l1_keys_d3c6c57e.json",
        'eea8ed0d5f3aa79ecb5cf1cb892fa82f7d4bac780f8b3b17dbd069200765c6af')   # 12a L1 keys (ed6)
    c92_keys    = @("$PrelaunchDir\ed5_inputs\x11\c92_keys.txt", $null)       # 12b plan scan
    c93_keys    = @("$PrelaunchDir\ed5_inputs\x11\c93_keys.txt", $null)
}
# $null sha: the file must exist (the edition 6 plan read the same two key lists)
$V0Rows = Get-FixedPath 'MAIN_JSONL_SHA256'      # common.ps1 fixed input (P7-1 --p3-hash-source)
$H6Keys = Get-FixedPath 'H6_SHA256'              # common.ps1 fixed input (12a keys)
$NoiseVb = Get-FixedPath 'NOISE_VB_SHA256'       # common.ps1 fixed input (12b plan --noise)
$L1Labels = [ordered]@{ L1_VBM0 = @('VBM0', 'l1_keys_12b'); L1_VBM = @('VBM', 'l1_keys_12b')
    L1a_VBM0 = @('VBM0', 'l1_keys_12a'); L1a_VBM = @('VBM', 'l1_keys_12a') }
# the four L1 reference runs of step_l1ref_ed7.ps1: 12b (L1_*) and T-JR-12a (L1a_*), spec 6.4
$ScanRequiredRoots = @("$CauseDir\j9_runs\79495405", "$CauseDir\j9_runs\6bfb2560",
    "$CauseDir\j9_runs\b46bdf8f", $RunsRoot)
# spec 6.4 / Y7-7: the edition 6 run outputs (records B / C / D in 79495405\records_after_stop),
# the probe 6bfb2560, the pre-seal reproduction b46bdf8f and the edition 7 outputs of this run

# the edition 7 settings run by r79 with the plant of the rod-truth reading (spec 6.4)
foreach ($Setting in @('VBM', 'VBM0', 'VBKM', 'VBKM0')) { $R79RodModel[$Setting] = 'plant_truth' }

function Get-InputProblem([string]$Name) {
    # why an input is not the sealed one ($null: it is); a dry run reads the same files
    $Path, $Expected = $Ed7Inputs[$Name]
    if (-not (Test-Path -LiteralPath $Path)) { return "input $Name missing: $Path" }
    if ($null -eq $Expected) { return $null }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
    if ($Actual -ne $Expected) { return "input $Name sha256 $Actual is not $Expected" }
    return $null
}

function Get-InputPath([string]$Name) { return $Ed7Inputs[$Name][0] }

function Get-RunIdentity {
    # HEAD, is_clean and the 03_src tree id of the run worktree (a git failure gives $null
    # fields, never "clean")
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
    # why an identity is not the run's ($null: it is)
    if ($Identity.head -ne $RunCommit) { return "HEAD $($Identity.head) is not $RunCommit" }
    if ($Identity.is_clean -ne $true) { return 'the run worktree is not clean (or git failed)' }
    if ($Identity.src_tree -ne $ControllerTree) { return "03_src tree $($Identity.src_tree) is not $ControllerTree" }
    return $null
}

function Get-ScopeProblem {
    # P7-10: C is the child of b46bdf8f and changes the 5.1 (i) .. (iv) paths only; its 03_src
    # diff is the JP3_SPEC_EDITION_V7 block (one hunk, lines 197 .. 201). $null: in scope.
    $Parent = (& git -C $Worktree rev-parse "$RunCommit^")
    if ($LASTEXITCODE -ne 0) { return 'git rev-parse of the run commit parent failed' }
    if ($Parent.Trim() -ne $ImplCommit) { return "the run commit parent $Parent is not $ImplCommit" }
    $Names = @(& git -C $Worktree diff --name-only $ImplCommit $RunCommit)
    if ($LASTEXITCODE -ne 0) { return 'git diff --name-only failed' }
    $Outside = @($Names | Where-Object { $ScopeFiles -notcontains $_ -and -not $_.StartsWith($ScopePrefix) })
    if ($Outside.Count) { return "P7-10: $($Outside.Count) changed paths outside 5.1 (i) .. (iv) ($($Outside[0]) ...)" }
    $SrcDiff = @(& git -C $Worktree diff -U0 $ImplCommit $RunCommit -- 03_src)
    if ($LASTEXITCODE -ne 0) { return 'git diff of 03_src failed' }
    $Hunks = @($SrcDiff | Where-Object { $_.StartsWith('@@') } | ForEach-Object { ($_ -split ' @@')[0] + ' @@' })
    if ($Hunks.Count -ne 1 -or $Hunks[0] -ne $SrcHunk -or $SrcDiff -notcontains $SrcConstantLine) {
        return "P7-10: the 03_src diff is not the JP3_SPEC_EDITION_V7 block ($($Hunks -join ', '))"
    }
    return $null
}

function Complete-Step {
    # common.ps1 Complete-Step with the end identity against the start one; a change stops 3
    # and the step's outputs are not used (no .done marker)
    $End = Get-RunIdentity
    $StepState.Codes['identity_end'] = $End
    $Problem = Get-IdentityProblem $End
    if ($Problem) { Stop-Step 3 "identity at the end: $Problem (outputs not used)" }
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

function Initialize-Ed7Step([string]$StepName, [int]$Attempt, [string[]]$Requires, [string[]]$Inputs = @()) {
    # the edition 4a step start (run commit, clean tree, 4a fixed inputs, environment, a new
    # attempt folder), then the P7-10 scope, the start identity and the step's inputs
    $Folder = Initialize-Step $StepName $Attempt $Requires
    $Scope = Get-ScopeProblem
    if ($Scope) { Stop-Step 3 $Scope }
    $StepState.Codes['scope'] = "P7-10: $ImplCommit -> $RunCommit in scope"
    $Start = Get-RunIdentity
    $StepState.Codes['identity_start'] = $Start
    $Problem = Get-IdentityProblem $Start
    if ($Problem) { Stop-Step 3 "identity at the start: $Problem" }
    foreach ($Name in @('spec_v7') + $Inputs) {
        $InputProblem = Get-InputProblem $Name
        if ($InputProblem) { Stop-Step 3 $InputProblem }
        $StepState.Codes["input:$Name"] = Get-RepoPath (Get-InputPath $Name)
    }
    $StepState.Codes['run_steps'] = "$Ed7StepsDir (run commit $RunCommit)"
    return $Folder
}

function Assert-NewOutput([string[]]$Paths) {
    # spec 4 step 6 (audit M-7): an output file or folder that exists refuses the run
    foreach ($Path in $Paths) {
        if (Test-Path -LiteralPath $Path) { Stop-Step 2 "$Path exists (M-7: every output path is new)" }
    }
}

function Start-Ed7Run {
    # Start-Run after the mask check and the new-output check; the core kind (P / E / mixed) of
    # the mask goes into the step record
    param([string]$Label, [string]$MaskHex, [string[]]$Arguments, [hashtable]$Environment = @{},
        [string]$WrapOutput = '', [string]$TaskType, [int]$Workers, [string[]]$Outputs)
    $MaskProblem = Get-CoreMaskProblem $MaskHex
    if ($MaskProblem) { Stop-Step 3 $MaskProblem }
    Assert-NewOutput $Outputs
    $StepState.Codes["core:$Label"] = Get-CoreKind $MaskHex
    return Start-Run -Label $Label -MaskHex $MaskHex -Arguments $Arguments -Environment $Environment `
        -WrapOutput $WrapOutput -TaskType $TaskType -Workers $Workers
}

function Get-R79Environment([string]$Setting, [string]$T4hDir, [string]$Plan = '') {
    # the r79 runner environment of 12a / 12b and the L1 runs (a rod fault plan for VBKM / VBKM0)
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = $T4hDir; R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    if ($Plan) { $Environment['R79_ROD_FAULT_PLAN'] = $Plan }
    return $Environment
}

function Get-DoneCode([string]$StepName, [string]$Name) {
    # a code of a done step's record (its .done marker)
    $DonePath = "$RunsRoot\$StepName.done"
    if (-not (Test-Path -LiteralPath $DonePath)) { Stop-Step 3 "step $StepName is not done ($DonePath)" }
    return [string](Get-Content -Raw -LiteralPath $DonePath | ConvertFrom-Json).codes.$Name
}

function Read-Decision([string]$Path, [string]$Sha256, [string[]]$Statuses) {
    # the 12b P-pred decision of the judge commit T (status and blocks; spec 6.4): its sha256 as
    # given and a status of $Statuses, else not usable (2). A dry run reads the dry file the same way.
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

# --- dry run overrides (no process, no tool; the commands go into the step record) -------------
if ($IsEd7Dry) {
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
