#Requires -Version 7
# 436.9 J-P3 edition 6: shared settings of the edition 6 run steps (jp3_remedy_spec_v6.md
# revision 14, 4 steps 5 .. 9, 6.1 .. 6.6; erratum 1 1d4f7539). The edition 4a helpers come from
# ..\run_steps\common.ps1 and ..\run_steps\record_helper.ps1, the stop gates of the T-JR-12a
# record report from ..\run_steps_ed5\record_gates_ed5.ps1 (all unchanged); this file sets the
# edition 6 run commit, folders, fixed inputs and the start checks.
#
# One commit (erratum 1 1-1): the run commit carries the controller of ac3c25a7 (03_src equal),
# the judge tools of the tool commits (65eba746, 8a4c8e68, b30f3b3f) and these run steps. The
# steps run FROM the run worktree (this file checks that its folder is inside it); outputs, the
# fixed inputs and the fixed list are the main checkout's.
#
# The run commit and the run worktree are read from prelaunch_j9\ed6_run_config.json of the main
# checkout (the main session writes it from ed6_run_config.template.json after the run commit:
# it cannot name its own commit). A placeholder left, a missing file or another HEAD stops 3.
#
# Run order (the main session launches every step; each needs the previous .done):
#   1. step_l1ref_ed6.ps1        the four L1 reference runs (12b VBL0 / VBL on l1_keys_12b.txt,
#                                12a VBL0 / VBL on l1_keys_d3c6c57e.json; plant_truth), before
#                                any 12a / 12b output (erratum 1 1-2), before the fixed list
#   2. prelaunch_ed6.ps1 -Part list   FIXED_INPUTS_RUN8.SHA256SUMS (--edition 6, the
#                                four L1 runs by --add), then the main session commits it
#   3. step6_confirm_ed6.ps1     confirmation (가) 216 and (나) 192 (spec 4 step 6, 6.3)
#   4. step7_j9main_ed6.ps1      j9_main 388 and the sensitivity rows 184 (4 step 7, 6.2)
#   5. step8a_dg3_ed6.ps1        T-JR-12a VBL against VBL0 (4 step 8, 6.5, erratum 1 1-3)
#   6. step8b_vbkl0_ed6.ps1 -Phase base, step8c_decide_ed6.ps1 (P-pred), when needs_b4:
#      step8b_vbkl0_ed6.ps1 -Phase b4 and step8c_decide_ed6.ps1 -WithB4, then step8d_vbkl_ed6.ps1
#      (T-JR-12b, 6.4, the order of 4 step 8)
# Every judge step goes on only on the judge tool's exit 0 (4 "멈춤": 1 failed / 2 / 3 stop and
# ask; a failure is never run again, Read-PreviousStops). No step prints a judged value: the
# tools write their reports, the console gets the step marker only.
#
# Dry run (no simulation, no judge, nothing in the main checkout): ED6_DRY_RUN_ROOT=<scratch
# folder> holds ed6_run_config.json and receives j9_runs\RUN8\ with the step records; Start-Run
# and Invoke-Tool record their commands only (dry_run_ed6.ps1).

. "$PSScriptRoot\..\run_steps\common.ps1"
. "$PSScriptRoot\..\run_steps\record_helper.ps1"
. "$PSScriptRoot\..\run_steps_ed5\record_gates_ed5.ps1"
$Ed6StepsDir = $PSScriptRoot

# --- dry run ---------------------------------------------------------------------------------
$Ed6DryRoot = [string]$env:ED6_DRY_RUN_ROOT
$IsEd6Dry = [bool]$Ed6DryRoot

# --- run commit and paths (the main session's config file) -----------------------------------
$Ed6Placeholder = '^<ED6_'
$Ed6ConfigFile = if ($IsEd6Dry) { "$Ed6DryRoot\ed6_run_config.json" } else { "$PrelaunchDir\ed6_run_config.json" }
$ControllerCommit = 'ac3c25a754013d1b673a150a4e2c877a02fb02be'
# spec v6 4 step 4a / erratum 1 1-1: the controller blobs (03_src) of the run commit are these

function Read-Ed6Config {
    if (-not (Test-Path -LiteralPath $Ed6ConfigFile)) {
        Write-Host "STOP: $Ed6ConfigFile missing (copy ed6_run_config.template.json and fill it in)"
        exit 3
    }
    $Config = Get-Content -Raw -LiteralPath $Ed6ConfigFile | ConvertFrom-Json
    foreach ($Value in @($Config.run_commit, $Config.worktree)) {
        if ([string]$Value -match $Ed6Placeholder) { Write-Host "STOP: $Ed6ConfigFile still holds $Value"; exit 3 }
    }
    if ([string]$Config.run_commit -notmatch '^[0-9a-f]{40}$') { Write-Host 'STOP: run commit is not a full sha'; exit 3 }
    return $Config
}
$Ed6Config = Read-Ed6Config
$RunCommit = [string]$Ed6Config.run_commit
$Worktree = [string]$Ed6Config.worktree
if (-not $Ed6StepsDir.StartsWith("$Worktree\", [StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "STOP: run the steps from the run worktree ($Worktree), not $Ed6StepsDir (the run commit's scripts)"
    exit 3
}

$RunShort = $RunCommit.Substring(0, 8)
$RunsParent = if ($IsEd6Dry) { "$Ed6DryRoot\j9_runs" } else { "$CauseDir\j9_runs" }
$RunsRoot = "$RunsParent\$RunShort"
$IdentityChecks = "$RunsRoot\_identity_checks"
$Ed6Inputs = "$PrelaunchDir\ed6_inputs"
$X11Folder = "$Ed6Inputs\x11"
$X11Selection = "$X11Folder\selection.json"
$X11SelectionSha256 = '6687b2dcbd7ec77b0eb28bd8219780967dac4462c16e9e2b57e35e11801f1f70'  # spec 6.4
$KeysDir = "$CauseDir\ed6_design\keys"
$SensKeys = "$KeysDir\sens_keys_v2.json"
$ConfirmAKeys = "$KeysDir\confirm_a_keys_v2.json"
$GridKeys = "$KeysDir\confirm_b_grid192.json"
$L1Keys12b = "$PrelaunchDir\ed5_inputs\l1_keys_12b.txt"      # erratum 1 1-2 (9f815533...)
$L1Keys12a = "$PrelaunchDir\l1_keys_d3c6c57e.json"           # spec 6.5 (eea8ed0d...)
$FixedList = "$PrelaunchDir\FIXED_INPUTS_$RunShort.SHA256SUMS"
$EntriesFile = "$PSScriptRoot\fixed_inputs_entries_ed6.txt"
$V0Rows = Get-FixedPath 'MAIN_JSONL_SHA256'
$V0Sha = $FixedInputs['MAIN_JSONL_SHA256'][1]
$Ed6Judge = "$Coupled/jp3_ed6_judge.py"
$Ed6Judge12b = "$Coupled/jp3_12b_judge_ed6.py"
$Tjr = "$Coupled/jp3_tjr_judge.py"
$L1Labels = [ordered]@{ L1_VBL0 = @('VBL0', $L1Keys12b); L1_VBL = @('VBL', $L1Keys12b)
    L1a_VBL0 = @('VBL0', $L1Keys12a); L1a_VBL = @('VBL', $L1Keys12a) }
# the four L1 reference runs of step_l1ref_ed6.ps1: 12b (L1_*) and T-JR-12a (L1a_*)

# the edition 6 settings run with the plant of the rod-truth reading (spec 6.4 / 6.5)
foreach ($Setting in @('VBL', 'VBL0', 'VBKL', 'VBKL0')) { $R79RodModel[$Setting] = 'plant_truth' }
# the T-JR-12a VBL report is a record tool (its J-P3 H-7 is a judged marker, record_gates_ed5)
$RecordCodeTools += @('tool:t12_VBL')

function Read-PreviousStops([string]$StepName) {
    # the edition 5 override (common_ed5.ps1): a judged failure of an earlier attempt refuses
    # any new attempt (4a-5 5.4)
    if (-not (Test-Path -LiteralPath $RunsRoot)) { return }
    $Stops = @(Get-ChildItem -LiteralPath $RunsRoot -File | Where-Object { $_.Name -like "$StepName.stop*" })
    foreach ($Stop in $Stops) {
        $Previous = Get-Content -Raw -LiteralPath $Stop.FullName | ConvertFrom-Json
        $StepState.PreviousStops += [ordered]@{ path = $Stop.FullName; folder = $Previous.folder
            exit_code = $Previous.exit_code; reason = $Previous.reason }
        $Refused = Get-RefusedPreviousStop $Stop.FullName $RecordCodeTools
        if ($Refused) { Stop-Step 2 "refused: $Refused in $($Stop.Name); 4a-5 5.4: a failure is never run again" }
    }
}

function Assert-ControllerBlobs {
    # erratum 1 1-1: 03_src of the run commit is the controller commit's (else stop 3, P6-3)
    & git -C $Worktree diff --quiet $ControllerCommit $RunCommit -- 03_src
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 "03_src of $RunCommit differs from $ControllerCommit (or git failed)" }
    $StepState.Codes['controller_blobs'] = "03_src = $ControllerCommit"
}

function Assert-FixedList {
    # 6.6: FIXED_INPUTS_RUN8 is tracked, equal to HEAD of the main checkout, and every
    # line's file still has its sha256 (else not judgeable: exit 2); a dry run only notes it
    if ($IsEd6Dry) { $StepState.Codes['fixed_list'] = "dry run: $(Get-RepoPath $FixedList) not checked"; return }
    $Relative = Get-RepoPath $FixedList
    & git -C $MainRoot ls-files --error-unmatch -- $Relative *> $null
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative is not tracked by git (prelaunch_ed6.ps1 -Part list, then commit)" }
    & git -C $MainRoot diff --quiet HEAD -- $Relative
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative differs from HEAD (or git failed)" }
    foreach ($Line in (Get-Content -LiteralPath $FixedList)) {
        if (-not $Line.Trim()) { continue }
        $Sha, $Path = $Line -split ' \*', 2
        $File = Join-Path $MainRoot $Path
        if (-not (Test-Path -LiteralPath $File)) { Stop-Step 2 "fixed input $Path missing" }
        $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $File).Hash.ToLower()
        if ($Actual -ne $Sha) { Stop-Step 2 "fixed input $Path sha256 $Actual is not the listed $Sha" }
    }
    $StepState.Codes['fixed_list'] = $Relative
}

function Get-ListedSha([string]$File) {
    # a file's sha256 from the fixed list (dry run: the file's own sha256, or 'dry')
    if ($IsEd6Dry) {
        if (Test-Path -LiteralPath $File) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $File).Hash.ToLower() }
        return 'dry'
    }
    $Relative = Get-RepoPath $File
    foreach ($Line in (Get-Content -LiteralPath $FixedList)) {
        $Sha, $Path = $Line -split ' \*', 2
        if ($Path -eq $Relative) { return $Sha }
    }
    Stop-Step 2 "$Relative is not in $FixedList"
}

function Initialize-Ed6Step([string]$StepName, [int]$Attempt, [string[]]$Requires, [switch]$BeforeList) {
    # the edition 4a step start (run commit, clean tree, 4a fixed inputs, environment, a new
    # attempt folder), the controller blobs, then the edition 6 fixed list (not before it exists)
    $Folder = Initialize-Step $StepName $Attempt $Requires
    Assert-ControllerBlobs
    if (-not $BeforeList) { Assert-FixedList }
    $StepState.Codes['run_steps'] = "$Ed6StepsDir (run commit $RunCommit)"
    return $Folder
}

function Get-R79Environment([string]$Setting, [string]$T4hDir, [string]$Plan = '') {
    # the r79 runner environment of 12a / 12b and the L1 runs (a rod fault plan for VBKL / VBKL0)
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = $T4hDir; R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    if ($Plan) { $Environment['R79_ROD_FAULT_PLAN'] = $Plan }
    return $Environment
}

function Get-L1Run([string]$Label) { return "$(Get-StepFolder 'l1ref')\$Label.json" }

function Invoke-L1InputGuard([string[]]$Inputs) {
    # erratum 2 2-1 (G-1) of edition 5 carried over: no L1 reference run is a judged input; the
    # four L1 runs by their fixed list sha256
    $Arguments = @("$Coupled/jp3_l1_input_guard.py", '--out', "$($StepState.Folder)\judge\l1_input_guard.json")
    foreach ($Label in $L1Labels.Keys) { $Arguments += @('--l1-reference-sha256', (Get-ListedSha (Get-L1Run $Label))) }
    foreach ($InputFile in $Inputs) { $Arguments += @('--input', $InputFile) }
    Invoke-Judge 'l1_input_guard' $Arguments | Out-Null
}

function Assert-RecordReport([string]$ReportPath, [switch]$VbjJp3) {
    # common_ed5.ps1 carried over: after a record tool whose exit 1 goes on (the T-JR-12a VBL
    # bundle, 6.5) - its J-P3 H-7 (jp3_outcome) stops 1, no J-P3 judgement / a setting defect /
    # a not-judgeable reason / a failure outside the 13.9 record list stops 2, record failures
    # alone go on; a judged failure leaves its marker for Read-PreviousStops
    $Stop = Get-RecordToolStop $ReportPath -VbjJp3:$VbjJp3
    $StepState.Codes["record_gate:$(Split-Path -Leaf $ReportPath)"] = if ($Stop) { $Stop.reason } else { 'go on' }
    $Markers = Get-JudgedFailureMarkers $Stop -VbjJp3:$VbjJp3
    foreach ($Name in $Markers.Keys) { $StepState.Codes[$Name] = $Markers[$Name] }
    if ($Stop) { Stop-Step $Stop.code $Stop.reason }
}

# --- dry run overrides (no process, no judge; the commands go into the step record) -----------
if ($IsEd6Dry) {
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
    function Read-ReportField([string]$Path, [string]$Field) { return 'dry' }
    function Assert-RecordReport([string]$ReportPath, [switch]$VbjJp3) { $StepState.Codes["record_gate:$(Split-Path -Leaf $ReportPath)"] = 'dry' }
}
