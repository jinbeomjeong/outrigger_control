#Requires -Version 7
# 436.9 J-P3 edition 5: shared settings of the edition 5 run steps (jp3_remedy_spec_v5.md 8,
# erratum 1). The edition 4a helpers come from ..\run_steps\common.ps1 (unchanged, its 4a fixed
# list keeps it as it is) and ..\run_steps\record_helper.ps1 (batch id and estimates of the run
# records); this file then sets the edition 5 run commit, folders and fixed inputs.
#
# Before any step the main session writes the run commit and the run worktree below (in the
# main checkout, as for edition 4a). Run order (erratum 2 audit warning 1):
#   1. prelaunch_ed5.ps1 -Part dry       X-4 dry selection
#   2. prelaunch_ed5.ps1 -Part l1keys    the 12b L1 key file (erratum 2 2-1)
#   3. step_l1ref.ps1                    the two L1 reference runs
#      step_p5fixed.ps1                  the P5-2 / P5-4 fixed values (case replays A .. F once,
#                                        spec v5 5 / 8 1; prelaunch audit B-2)
#   4. prelaunch_ed5.ps1 -Part x11       the X-11 plans, once
#      prelaunch_ed5.ps1 -Part ckdrop    the T-CK / DROPOUT keys and plans (2-9.5; after x11)
#      prelaunch_ed5.ps1 -Part v0sample  the j9_main V0 sample key list (2-9.1)
#   5. (main session commit: this file filled in, the parts 1 .. 4)
#   6. prelaunch_ed5.ps1 -Part list      FIXED_INPUTS_<run commit 8>.SHA256SUMS
#   7. (main session commit: the fixed list)
#   8. step0_cdry.ps1, then the steps 1 .. 7 (6b / 6c for 12b), step7b_ckdrop.ps1 (a record),
#      step8_j9main.ps1
# A step refuses to start while a placeholder is left or the fixed list is not tracked and
# equal to its files (Initialize-Ed5Step). Two exceptions: step_l1ref.ps1 and step_p5fixed.ps1
# run before the list exists (their outputs go into it), so they take the edition 4a start
# checks only (run commit, clean tree, the 4a fixed inputs; Initialize-Step).

. "$PSScriptRoot\..\run_steps\common.ps1"
. "$PSScriptRoot\..\run_steps\record_helper.ps1"
. "$PSScriptRoot\record_gates_ed5.ps1"

# --- run commit and paths (the main session fills them in) -----------------------------------
$RunCommit = '8003083db362cb01116882e84819d128629b2c54'
# the master merge of ed5-fix1 (prelaunch audit fixes B-1, B-2, W-1 .. W-3, erratum 4) in the
# locked worktree ed5-run2 (2026-11-22); the first run commit dba05b3f (worktree ed5-run) is
# superseded, its prelaunch outputs are in j9_runs/dba05b3f
$Worktree = 'C:\workspace\outrigger_control\.claude\worktrees\ed5-run2'
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

# exit 1 of these tools is a record, not a judged failure (Read-PreviousStops: a retry stays
# possible): the P-1 import closure (meets = the content comparison path, erratum 2 2-4) and
# the T-JR-12a bundles (6.2)
$RecordCodeTools += @('tool:p1_import_closure', 'tool:t12_VBH', 'tool:t12_VBJ')

function Read-PreviousStops([string]$StepName) {
    # edition 5 override of ..\run_steps\common.ps1 (that file stays as edition 4a listed it):
    # the earlier attempts' stop records go into this attempt's record; a judged failure of an
    # earlier attempt - a judge tool exit 1 outside $RecordCodeTools, or a judged-failure marker
    # 'judged:*' = 1 (prelaunch audit W-1: the T-JR-12a VBJ J-P3 H-7 inside a record tool) -
    # refuses any new attempt (4a-5 5.4: a failure is never run again)
    $Stops = @(Get-ChildItem -LiteralPath $RunsRoot -File | Where-Object { $_.Name -like "$StepName.stop*" })
    foreach ($Stop in $Stops) {
        $Previous = Get-Content -Raw -LiteralPath $Stop.FullName | ConvertFrom-Json
        $StepState.PreviousStops += [ordered]@{ path = $Stop.FullName; folder = $Previous.folder
            exit_code = $Previous.exit_code; reason = $Previous.reason }
        $Refused = Get-RefusedPreviousStop $Stop.FullName $RecordCodeTools
        if ($Refused) { Stop-Step 2 "refused: $Refused in $($Stop.Name); 4a-5 5.4: a failure is never run again" }
    }
}

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

function Write-DiffStat {
    # erratum 2 2-4: git diff --stat 78fd5d2d..run commit into the run record (a record, no stop;
    # a git failure is not read as "no change")
    $Log = "$($StepState.Folder)\logs\git_diff_stat_$($PreviousRunCommit.Substring(0, 8)).txt"
    $Stat = @(& git -C $Worktree diff --stat $PreviousRunCommit $RunCommit)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git diff --stat failed (no record)' }
    [IO.File]::WriteAllText($Log, ($Stat -join "`n") + "`n")
    $StepState.Codes['git_diff_stat'] = Get-RepoPath $Log
}

function Invoke-RecordTool([string]$Label, [string[]]$Arguments) {
    # erratum 2 2-1 (re-audit warnings 2 / 3): a record item (l1_overlap, l1_hash_record) never
    # stops the step - exit 2 / 3 go on and leave "<label>_record_status.json" with computed
    # false and the reason; exit 0 leaves computed true
    $Code = Invoke-Judge $Label $Arguments -ContinueCodes @(0, 2, 3)
    $Status = if ($Code -eq 0) { [ordered]@{ label = $Label; computed = $true; exit_code = 0 } } else {
        [ordered]@{ label = $Label; computed = $false; exit_code = $Code; reason = "$Label exit $Code (a record, erratum 2 2-1)" }
    }
    Write-JsonFile "$($StepState.Folder)\judge\${Label}_record_status.json" $Status
    return $Code
}

function Get-R79Environment([string]$Setting, [string]$T4hDir, [string]$Plan = '') {
    # the T-JR-12 runner environment; a rod fault plan for VBK / VBK0 (X-10, 6.3.1)
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = $T4hDir; R79_ROD_MODEL = $R79RodModel[$Setting] } + $R79Common
    if ($Plan) { $Environment['R79_ROD_FAULT_PLAN'] = $Plan }
    return $Environment
}

function Assert-RecordReport([string]$ReportPath, [switch]$VbjJp3) {
    # after a record tool whose exit 1 goes on (T-JR-12a VBH / VBJ, base-judge-compare): the
    # erratum 3 (sealed 7bab9217) 3-1 order of record_gates_ed5.ps1 Get-RecordToolStop - VBJ J-P3 H-7 stops 1,
    # no VBJ J-P3 judgement / a setting defect / a not-judgeable reason / a failure outside
    # the record list stops 2, record failures alone go on
    $Stop = Get-RecordToolStop $ReportPath -VbjJp3:$VbjJp3
    $StepState.Codes["record_gate:$(Split-Path -Leaf $ReportPath)"] = if ($Stop) { $Stop.reason } else { 'go on' }
    # prelaunch audit W-1: a judged failure (the VBJ J-P3 H-7) leaves its marker for
    # Read-PreviousStops, which refuses a new attempt
    $Markers = Get-JudgedFailureMarkers $Stop -VbjJp3:$VbjJp3
    foreach ($Name in $Markers.Keys) { $StepState.Codes[$Name] = $Markers[$Name] }
    if ($Stop) { Stop-Step $Stop.code $Stop.reason }
}

function Invoke-IdentityCheckPart([string]$Part) {
    # Invoke-IdentityCheck for a part of a step run before its judge (re-audit warning 4: the
    # j9_main V0 sample): its own report and log (never the step's final identity check
    # files), code identity_check_<part>; exit != 0 is not judgeable (exit 2)
    $Folder = $StepState.Folder
    $Out = "$IdentityChecks\$(Split-Path -Leaf $Folder)_$Part.md"
    if (Test-Path -LiteralPath $Out) { Stop-Step 2 "$Out exists (an identity report is never overwritten)" }
    $All = @('-I', '-B', "$VerifTools\baseline_check.py", 'identity', '--repo', $Worktree, $Folder,
        '--expect-commit', $RunCommit, '--mtime', '--out', $Out)
    $StepState.Commands.Add([ordered]@{ label = "identity_check_$Part"; command = "$DevPython $($All -join ' ')" })
    & $DevPython @All *> "$Folder\logs\identity_check_$Part.log"
    $Code = $LASTEXITCODE
    $StepState.Codes["identity_check_$Part"] = $Code
    if ($Code -ne 0) { Stop-Step 2 "baseline_check identity ($Part) exit $Code ($Out)" }
}

function Get-ListedSha([string]$File) {
    # a file's sha256 from the fixed list (the judge tools check the file against it)
    $Relative = Get-RepoPath $File
    foreach ($Line in (Get-Content -LiteralPath $FixedList)) {
        $Sha, $Path = $Line -split ' \*', 2
        if ($Path -eq $Relative) { return $Sha }
    }
    Stop-Step 2 "$Relative is not in $FixedList"
}

function Get-X11Sha { return Get-ListedSha $X11Selection }

# erratum 2 2-1: the L1 grade reference of 12b (key file from the case source, two L1 runs at
# the run commit, both in the fixed list)
$L1KeysFile = "$Ed5Inputs\l1_keys_12b.txt"
# erratum 2 2-7.1: the fixed V0 sample key list of j9_main (a fixed list entry; its selection
# rule is the main session's / control's, see the run step report)
$V0SampleKeysFile = "$Ed5Inputs\j9main_v0_sample_keys.json"
$V0SampleCommandFile = "$Ed5Inputs\j9main_v0_sample_keys.command.txt"
# erratum 2 2-9.5: the T-CK / DROPOUT keys and plans (jp3_ckdrop_plan.py, fixed list entries)
$CkdropFolder = "$Ed5Inputs\ckdrop"
$L1Settings = @('VBJ0', 'VBJ')
function Get-L1Run([string]$Setting) { return "$(Get-StepFolder 'l1ref')\L1_$Setting.json" }
# prelaunch audit B-2: the P5-2 / P5-4 fixed records of step_p5fixed.ps1 (fixed list entries)
$P5FixedNames = @('p52.json', 'p54.json')
# erratum 4 4-1: the disclosure sentence of the fixed computation (step record, judgement head)
$P5FixedDisclosure = 'P5-2 고정 계산에서 사례 재생 줄의 판정 키를 실행 전에 보았다(원판 5절 설계). 단계 (4)는 같은 코드로 다시 돌려 고정값과 같아야 한다.'
# erratum 4 4-1: the simulation path of the fixed values (case replay and replay runners; the
# static import closure of these entries decides whether another commit's records may serve)
$P5FixedEntries = @("$Coupled/run_v5.py", "$Coupled/jp3_case_replay.py", "$Coupled/jp3_p5_fixed_values.py")
function Get-P5FixedFile([string]$Name) { return "$(Get-StepFolder 'p5fixed')\judge\$Name" }

function Invoke-P52Compare([string]$Label, [string[]]$Rows) {
    # prelaunch audit B-2 (P5-2 "고정 수와 차 > 0"): the case replay rows of this step against
    # the fixed P5-2 record (its sha256 from the fixed list); returns the tool code (1 failed,
    # 2 not judgeable, 3 error)
    $Fixed = Get-P5FixedFile 'p52.json'
    $Arguments = @("$Coupled/jp3_p5_fixed_values.py", 'p52-compare', '--fixed', $Fixed,
        '--fixed-sha256', (Get-ListedSha $Fixed), '--rows') + $Rows +
        @('--out', "$($StepState.Folder)\judge\$Label.json")
    return Invoke-Tool $Label $Arguments
}

function Assert-NoL1Inputs([string[]]$Inputs) {
    # erratum 2 2-1 / 2-7.1 / G-1: call before a j9_main judge command. The L1 reference sha256
    # set: the two 12b l1ref runs by their FIXED_INPUTS sha256, the two T-JR-12a L1 runs of the
    # attempt dg3.done names by their files (dg3.done or a file missing: not judgeable, exit
    # 2). An input file of one of these sha256 stops as a setting defect (exit 2).
    $DonePath = "$RunsRoot\dg3.done"
    if (-not (Test-Path -LiteralPath $DonePath)) { Stop-Step 2 "dg3.done missing (erratum 2 G-1: no T-JR-12a L1 reference)" }
    $Dg3Folder = "$RunsRoot\$(Split-Path -Leaf (Get-Content -Raw -LiteralPath $DonePath | ConvertFrom-Json).folder)"
    $Arguments = @("$Coupled/jp3_l1_input_guard.py", '--out', "$($StepState.Folder)\judge\l1_input_guard.json")
    foreach ($Setting in $L1Settings) {
        $Dg3L1 = "$Dg3Folder\l1_$Setting.json"
        if (-not (Test-Path -LiteralPath $Dg3L1)) { Stop-Step 2 "$Dg3L1 missing (erratum 2 G-1)" }
        $Arguments += @('--l1-reference-sha256', (Get-ListedSha (Get-L1Run $Setting)), '--l1-reference', $Dg3L1)
    }
    foreach ($InputFile in $Inputs) { $Arguments += @('--input', $InputFile) }
    Invoke-Judge 'l1_input_guard' $Arguments | Out-Null
}
