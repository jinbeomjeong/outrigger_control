#Requires -Version 7
# 436.9 J-P3 edition 5: shared settings of the edition 5 run steps (jp3_remedy_spec_v5.md 8,
# erratum 1). The edition 4a helpers come from ..\run_steps\common.ps1 (unchanged, its 4a fixed
# list keeps it as it is) and ..\run_steps\record_helper.ps1 (batch id and estimates of the run
# records); this file then sets the edition 5 run commit, folders and fixed inputs.
#
# Before any step: the main session writes the run commit and the run worktree below (in the
# main checkout, as for edition 4a), makes the inputs (prelaunch_dry_select.ps1, then
# prelaunch_x11_plan.ps1 once, just before step0_cdry.ps1), commits them and writes the fixed
# list (prelaunch_fixed_inputs.ps1). A step refuses to start while a placeholder is left or the
# fixed list is not tracked and equal to its files.

. "$PSScriptRoot\..\run_steps\common.ps1"
. "$PSScriptRoot\..\run_steps\record_helper.ps1"

# --- run commit and paths (the main session fills them in) -----------------------------------
$RunCommit = '<ED5_RUN_COMMIT>'
$Worktree = '<ED5_RUN_WORKTREE>'
$Ed5Placeholder = '^<ED5_'

function Assert-Ed5Configured {
    foreach ($Value in @($RunCommit, $Worktree)) {
        if ($Value -match $Ed5Placeholder) {
            Write-Host "STOP: common_ed5.ps1 still holds the placeholder $Value (set the run commit and worktree)"
            exit 3
        }
    }
    if ($RunCommit -notmatch '^[0-9a-f]{40}$') { Write-Host "STOP: run commit $RunCommit is not a full sha"; exit 3 }
}
Assert-Ed5Configured

$RunShort = $RunCommit.Substring(0, 8)
$RunsRoot = "$CauseDir\j9_runs\$RunShort"
$IdentityChecks = "$RunsRoot\_identity_checks"
$P1OutputsList = "$PrelaunchDir\P1_OUTPUTS_$RunShort.SHA256SUMS"
$Ed5Inputs = "$PrelaunchDir\ed5_inputs"
# prelaunch outputs: the X-4 dry selection (erratum 1 9.1) and the X-11 plans (6.3.1)
$DrySelection = "$Ed5Inputs\dry_selection.json"
$X11Folder = "$Ed5Inputs\x11"
$X11Selection = "$X11Folder\selection.json"
$FixedList = "$PrelaunchDir\FIXED_INPUTS_$RunShort.SHA256SUMS"
$EntriesFile = "$PSScriptRoot\fixed_inputs_entries.txt"

# erratum 1 9.3 / P5-1: the edition 4a run commit whose outputs the edition 5 rows are compared
# with (the comparison tools read them; no value is shown)
$PreviousRunCommit = '78fd5d2d03e40ac7d9143429f602b58255c762fc'
$PreviousRunsRoot = "$CauseDir\j9_runs\$($PreviousRunCommit.Substring(0, 8))"

# the fixed key files of the three dry families (erratum 1 9.1; jp3_fixed_inputs checks the values)
$FixedInputs['DRY_KEYS_FILE_SHA256_G8'] = @("$Ed5Inputs\dry_selection_r79_key_g8.txt",
    'b7c7470a800ce1146d30caefa8050fbb1a73c18058af2b23af7dedf399619bd4')
$FixedInputs['DRY_KEYS_FILE_SHA256_REF'] = @("$Ed5Inputs\dry_selection_r79_key_ref.txt",
    '95ce6f27b44bb13b76fe8fb02d056f6dc5ae1de9be28b29d1529b8fbbd965299')

function Assert-FixedList {
    # 6.6: FIXED_INPUTS_<run commit 8> is tracked, equal to HEAD of the main checkout, and every
    # line's file still has its sha256 (else not judgeable: exit 2)
    $Relative = Get-RepoPath $FixedList
    & git -C $MainRoot ls-files --error-unmatch -- $Relative *> $null
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative is not tracked by git (prelaunch_fixed_inputs.ps1, then commit)" }
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

function Initialize-Ed5Step([string]$StepName, [int]$Attempt, [string[]]$Requires) {
    # the edition 4a step start (commit, tree, fixed inputs, environment, a new attempt folder),
    # then the edition 5 fixed list
    $Folder = Initialize-Step $StepName $Attempt $Requires
    Assert-FixedList
    return $Folder
}

function Get-PreviousStepFolder([string]$StepName) {
    # the 78fd5d2d folder of a step: its .done marker, else its newest .stop (dg3 stopped there)
    $Markers = @("$PreviousRunsRoot\$StepName.done") + @(Get-ChildItem -LiteralPath $PreviousRunsRoot -File |
            Where-Object { $_.Name -like "$StepName.stop*" } | Sort-Object LastWriteTime -Descending |
            ForEach-Object { $_.FullName })
    foreach ($Marker in $Markers) {
        if (Test-Path -LiteralPath $Marker) {
            $Name = Split-Path -Leaf (Get-Content -Raw -LiteralPath $Marker | ConvertFrom-Json).folder
            return "$PreviousRunsRoot\$Name"
        }
    }
    Stop-Step 3 "no $StepName marker under $PreviousRunsRoot"
}

function Invoke-P51([string]$Label, [string]$OldRows, [string]$NewRows, [string]$OldT4h = '', [string]$NewT4h = '') {
    # P5-1: the command hashes of this step's rows against the same rows of 78fd5d2d (a pair
    # without a fallback on either side, VBJ0 / VB / VBK0 and the X11 arm whatever the
    # fallbacks; VBG6 pairs with the 4a VBG5); 1 differs / 2 / 3 stop
    $Arguments = @("$Coupled/jp3_p51_compare.py", '--old', $OldRows, '--new', $NewRows,
        '--out', "$($StepState.Folder)\judge\p51_$Label.json")
    if ($OldT4h) { $Arguments += @('--old-t4h', $OldT4h) }
    if ($NewT4h) { $Arguments += @('--new-t4h', $NewT4h) }
    Invoke-Judge "p51_$Label" $Arguments | Out-Null
}

function Invoke-DryMatch([string]$Item, [string]$OldFolder) {
    # erratum 1 9.3: dry5 against 78fd5d2d dry_a1, dry5_retry against this commit's dry_a<k-1>
    $Folder = $StepState.Folder
    $CodesFile = "$Folder\logs\codes_for_rerun_match_$Item.json"
    $StepState.Codes | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $CodesFile -Encoding utf8NoBOM
    Invoke-Judge "rerun_match_$Item" @("$Coupled/jp3_rerun_match.py", '--old', (Split-Path -Parent $OldFolder),
        '--old-folder', $OldFolder, '--new', $RunsRoot, '--items', $Item, '--new-folder', $Folder,
        '--new-codes', $CodesFile, '--out', "$Folder\judge\rerun_match_$Item.json") | Out-Null
}

function Get-R79Environment([string]$Setting, [string]$T4hDir, [string]$Plan = '') {
    # the T-JR-12 runner environment; a rod fault plan for VBK / VBK0 (X-10, 6.3.1)
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = $T4hDir; R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    if ($Plan) { $Environment['R79_ROD_FAULT_PLAN'] = $Plan }
    return $Environment
}

function Get-X11Sha {
    # the X-11 selection sha256 from the fixed list (the 12b judge checks the file against it)
    $Relative = Get-RepoPath $X11Selection
    foreach ($Line in (Get-Content -LiteralPath $FixedList)) {
        $Sha, $Path = $Line -split ' \*', 2
        if ($Path -eq $Relative) { return $Sha }
    }
    Stop-Step 2 "$Relative is not in $FixedList"
}
