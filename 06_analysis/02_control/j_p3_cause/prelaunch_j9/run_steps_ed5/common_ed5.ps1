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
#   8. step0_cdry.ps1, then the steps 1 .. 6 and 6b base at the run commit (done / stopped)
# A step refuses to start while a placeholder is left or the fixed list is not tracked and
# equal to its files (Initialize-Ed5Step). Two exceptions: step_l1ref.ps1 and step_p5fixed.ps1
# run before the list exists (their outputs go into it), so they take the edition 4a start
# checks only (run commit, clean tree, the 4a fixed inputs; Initialize-Step).
#
# Erratum 8 (jp3_remedy_spec_v5_erratum8.md, sealed cd2de978; two commits, 8-9): the steps after
# 6b run with the run step scripts and the judge tool of the tool commit, the simulations still
# at the run commit in ed5-run5. Order (8-9 "12b 진행"):
#   9. (main session: the tool commit merged, $ToolCommit below filled in and committed)
#  10. prelaunch_ed5.ps1 -Part list_e8   FIXED_INPUTS_<tool commit 8>.SHA256SUMS (the entries of
#      fixed_inputs_entries_e8.txt; it lists FIXED_INPUTS_<run commit 8> too), then commit it
#  11. step6b_decide_e8.ps1 (12b_decide_e8), if needs_b4: step6b_vbk0.ps1 -Phase b4 (12b_vbk0_b4) and
#      step6b_decide_e8_b4.ps1 (12b_decide_e8_b4); step6c_vbk.ps1 (12b_vbk), step7_records.ps1,
#      step7b_ckdrop.ps1, step8_j9main.ps1
# Each of them starts with Initialize-E8Step: the run commit checks of Initialize-Step, then
# the tool checkout (HEAD = $ToolCommit, clean; 8-9 (a')), the run steps here = the tool
# commit's but the $ToolCommit line (8-9 (f)), git diff --name-status of the run commit against
# the tool commit and against HEAD of this checkout (the list commit) by the rule of 8-9 (a),
# the two fixed lists (8-9 (a''): FIXED_INPUTS_<run commit 8> first, its run step lines replaced
# by the tool list's; then FIXED_INPUTS_<tool commit 8>) and the static import closure of the
# VBK / VBK0 runners (las_t3_dg3.py, jp3_run_identity.py) against the tool commit's changes
# (8-9, disjoint or stop 3). Judge commands run in the tool checkout (Invoke-ToolJudge).

. "$PSScriptRoot\..\run_steps\common.ps1"
. "$PSScriptRoot\..\run_steps\record_helper.ps1"
. "$PSScriptRoot\record_gates_ed5.ps1"
. "$PSScriptRoot\e8_gates_ed5.ps1"
$Ed5StepsDir = $PSScriptRoot

# --- run commit and paths (the main session fills them in) -----------------------------------
$RunCommit = '606f87131a7f13468f1db37cf6c811c442a6caf0'
# made inside the locked worktree ed5-run5 on the 876d8a49 archive 81871a68 (user decision (ga),
# 2026-11-23: the run commit's one changed file, ed5_design/run_commit_note.txt, was written in
# the run worktree before the commit, so the identity --mtime check sees it older than the
# commit); superseded run commits: dba05b3f (worktree ed5-run, prelaunch audit), 8003083d
# (worktree ed5-run2, p5fixed stopped 2: the rev 4 judged key), ae9d0b2d (worktree ed5-run3,
# step (4a) cases stopped 2: VBG5 without its VBG6 pair, erratum 6), 876d8a49 (worktree
# ed5-run4, l1ref stopped 2: identity --mtime warnings on the files the commit added, the
# worktree made after the commit); their prelaunch outputs are in j9_runs/<commit 8>
$Worktree = 'C:\workspace\outrigger_control\.claude\worktrees\ed5-run5'
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
# erratum 8 8-9: the import closure exit 1 (meets) stops 3 as a broken precondition, never as a
# judged failure
$RecordCodeTools += @('tool:e8_tool_closure')

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

function Invoke-RecordTool([string]$Label, [string[]]$Arguments, [switch]$InToolCheckout) {
    # erratum 2 2-1 (re-audit warnings 2 / 3): a record item (l1_overlap, l1_hash_record) never
    # stops the step - exit 2 / 3 go on and leave "<label>_record_status.json" with computed
    # false and the reason; exit 0 leaves computed true. -InToolCheckout: the tool commit's
    # tool (erratum 8 8-9 (f), step7b_ckdrop.ps1)
    $Code = if ($InToolCheckout) { Invoke-ToolJudge $Label $Arguments -ContinueCodes @(0, 2, 3) }
    else { Invoke-Judge $Label $Arguments -ContinueCodes @(0, 2, 3) }
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
$P5FixedDisclosure = 'P5-2 고정 계산에서 사례 재생 줄의 판정 키와 사례별 합격 값을 실행 전에 보았다(원판 5절 설계). 단계 (4)는 같은 코드로 다시 돌려 고정값과 같아야 한다.'
# control's reading of erratum 4 4-1 (2026-11-22; step record of step_p5fixed.ps1)
$P5JudgedKeyReading = '정오 4 4-1의 ''판정 키''는 줄의 ③ 판에 따른 J-P3 판정 키다(판 4a 6.1·4a-2 R6). rev 4 = `ext_moving.breach_reads`, rev 5·6 = jp3a/b/c.'
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
    # 2). An input file of one of these sha256 stops as a setting defect (exit 2). The guard is
    # a judge command of step 8, so it runs in the tool checkout (erratum 8 8-9 (f)).
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
    Invoke-ToolJudge 'l1_input_guard' $Arguments | Out-Null
}

# --- erratum 8: the tool commit (8-9) ----------------------------------------------------------
# The main session writes the tool commit (the commit of jp3_12b_judge.py with erratum 8 8-8,
# its tests and these run steps) after it is made; the tool checkout is the locked worktree at
# that commit. Judge commands run there; simulations stay at $RunCommit in $Worktree.
$ToolCommit = '<ED5_TOOL_COMMIT>'
$ToolWorktree = 'C:\workspace\outrigger_control\.claude\worktrees\ed5-tool8'
$E8RunStepsDir = "$PrelaunchDir\run_steps_ed5"
$E8EntriesFile = "$PSScriptRoot\fixed_inputs_entries_e8.txt"
# erratum 8 8-1.3: the fixed b1 / b2 VBK0 outputs of 12b_vbk0_base_a1 (run file sha256 and the
# T4h digest of jp3_12b_judge.input_record); decide checks them (8-9 (d))
$E8Vbk0Expected = [ordered]@{
    b1 = @{ run_sha256 = '87e76b0bcc4d32cadd10592cac8314452a9408b6fde4765b77388061caf23c4e'
        t4h_digest = '561438f1da1335cf76e48fd5a1eaafeab3caf778161139ec6998abbad32d031d' }
    b2 = @{ run_sha256 = '205079fec5c7ea8c6460dd172b3e44129dd355242e675378a5f0147441cd0a8a'
        t4h_digest = 'b0c4a79be083e14515692b5a996d775e4fb799c8a252af1f7e741f04c4a616a8' }
}
# erratum 8 8-9 (c), user confirmation 2026-11-23: the environment variables the VBK runs need
# beyond the b1 / b2 VBK0 ones (name = value). None: Get-R79Environment gives VBK the same
# variables as VBK0 (R79_ROD_MODEL plant_truth for both, re-audit R-16) but the setting name,
# the plan and the T4h folder, which 8-9 (c) allows to differ.
$E8VbkExtraEnvironment = @{}
$E8RunMasks = @('0x000F', '0x00F0', '0x0F00', '0xF000')  # one P quarter per block (as 6b / 6c)

function Assert-ToolConfigured {
    # the tool commit filled in (a full sha, not the run commit); no step starts before
    if ($ToolCommit -match $Ed5Placeholder -or $ToolCommit -notmatch '^[0-9a-f]{40}$') {
        Write-Host "STOP: common_ed5.ps1 tool commit $ToolCommit is not filled in (erratum 8 8-9: the main session writes it after the tool commit)"
        exit 3
    }
    if ($ToolCommit -eq $RunCommit) { Write-Host 'STOP: the tool commit is the run commit'; exit 3 }
    if ($Ed5StepsDir -ne $E8RunStepsDir) {
        Write-Host "STOP: run the steps from $E8RunStepsDir (the fixed lists name the main checkout's files), not $Ed5StepsDir"
        exit 3
    }
}

function Get-ToolList { return "$PrelaunchDir\FIXED_INPUTS_$($ToolCommit.Substring(0, 8)).SHA256SUMS" }

function Assert-ToolCheckout {
    # 8-9 (a'): the tool checkout's HEAD is the tool commit and its tracked tree is clean (a git
    # failure is never read as clean)
    $Head = (& git -C $ToolWorktree rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git rev-parse of the tool checkout failed (no identity)' }
    if ($Head.Trim() -ne $ToolCommit) { Stop-Step 3 "tool checkout HEAD $Head is not the tool commit $ToolCommit" }
    $Status = (& git -C $ToolWorktree status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 'git status of the tool checkout failed (no identity)' }
    if ($Status) { Stop-Step 3 "tool checkout not clean: $($Status -join '; ')" }
}

function Get-GitLines([string[]]$Arguments) {
    # git output lines decoded as UTF-8 (paths outside ASCII); a git failure stops 3
    $Previous = [Console]::OutputEncoding
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    try { $Lines = @(& git -C $MainRoot -c core.quotepath=false @Arguments) }
    finally { [Console]::OutputEncoding = $Previous }
    if ($LASTEXITCODE -ne 0) { Stop-Step 3 "git $($Arguments -join ' ') failed (no identity)" }
    return , $Lines
}

function Assert-ToolScripts {
    # 8-9 (f): the run steps run here are the tool commit's; only the $ToolCommit line of this
    # file may differ (the main session fills it in after the tool commit)
    $Relative = Get-RepoPath $E8RunStepsDir
    $Changed = Get-GitLines @('diff', '--no-renames', '--name-status', $ToolCommit, '--', $Relative)
    $CommonLine = "M`t$Relative/common_ed5.ps1"
    foreach ($Line in $Changed) {
        if ($Line -cne $CommonLine) { Stop-Step 3 "run step '$Line' differs from the tool commit (erratum 8 8-9 (f))" }
    }
    if ($Changed -ccontains $CommonLine) {
        $Diff = Get-GitLines @('diff', '-U0', $ToolCommit, '--', "$Relative/common_ed5.ps1")
        $Edits = @($Diff | Where-Object { $_ -match '^[+-]' -and $_ -notmatch '^(\+\+\+|---) ' })
        $ToolLines = @($Edits | Where-Object { $_ -match "^[+-]\`$ToolCommit = '[^']*'$" })
        if ($Edits.Count -ne 2 -or $ToolLines.Count -ne 2) {
            Stop-Step 3 'common_ed5.ps1 differs from the tool commit beyond the $ToolCommit line (erratum 8 8-9 (f))'
        }
    }
    $StepState.Codes['e8_run_steps'] = "the tool commit's ($ToolCommit) but the `$ToolCommit line"
}

function Assert-ToolDiff {
    # 8-9 (a): git diff --name-status of the run commit against the tool commit and against HEAD
    # of this checkout (the list commit) into the step logs, each by the rule of
    # e8_gates_ed5.ps1 Get-E8DiffStop (a line outside it stops 3)
    $MainHead = (Get-GitLines @('rev-parse', 'HEAD'))[0].Trim()
    foreach ($Target in @(@('tool_commit', $ToolCommit), @('main_head', $MainHead))) {
        $Lines = Get-GitLines @('diff', '--no-renames', '--name-status', $RunCommit, $Target[1])
        $Log = "$($StepState.Folder)\logs\e8_diff_$($Target[0]).txt"
        [IO.File]::WriteAllText($Log, "# git diff --no-renames --name-status $RunCommit $($Target[1])`n" + ($Lines -join "`n") + "`n")
        $StepState.Codes["e8_diff:$($Target[0])"] = "$($Target[1]) $(Get-RepoPath $Log)"
        $Stop = Get-E8DiffStop $Lines
        if ($Stop) { Stop-Step $Stop.code "$($Target[0]) $($Target[1]): $($Stop.reason)" }
    }
}

function Assert-TrackedList([string]$List) {
    # a fixed list is tracked and equal to HEAD of this checkout (else not judgeable: exit 2)
    $Relative = Get-RepoPath $List
    & git -C $MainRoot ls-files --error-unmatch -- $Relative *> $null
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative is not tracked by git" }
    & git -C $MainRoot diff --quiet HEAD -- $Relative
    if ($LASTEXITCODE -ne 0) { Stop-Step 2 "$Relative differs from HEAD (or git failed)" }
}

function Assert-E8FixedLists {
    # 8-9 (a''): both lists from this checkout - FIXED_INPUTS_<run commit 8> first (its run step
    # lines are replaced by the tool list's: the tool commit changed the run steps), then
    # FIXED_INPUTS_<tool commit 8>, which names the first list with its sha256
    $ToolList = Get-ToolList
    Assert-TrackedList $FixedList
    Assert-TrackedList $ToolList
    $Stop = Get-E8FixedListStop $FixedList $ToolList $MainRoot $E8RunStepsPrefix
    if ($Stop) { Stop-Step $Stop.code $Stop.reason }
    $StepState.Codes['fixed_list'] = Get-RepoPath $FixedList
    $StepState.Codes['fixed_list_tool'] = Get-RepoPath $ToolList
}

function Assert-ToolClosure {
    # 8-9: no file the tool commit changed is in the static import closure of the VBK / VBK0
    # runners (P-1 closure check of erratum 2 2-4, the run commit's tool on the run worktree);
    # meets (1) stops 3, 2 / 3 stop with their code
    $Out = "$($StepState.Folder)\judge\e8_tool_closure.json"
    $Code = Invoke-Tool 'e8_tool_closure' @("$Coupled/jp3_import_closure.py", '--repo', $Worktree,
        '--entry', "$Coupled/las_t3_dg3.py", '--entry', "$Coupled/jp3_run_identity.py",
        '--base', $RunCommit, '--head', $ToolCommit, '--out', $Out)
    if ($Code -eq 1) { Stop-Step 3 "erratum 8 8-9: a file of the tool commit is in the runner import closure ($Out)" }
    if ($Code -ne 0) { Stop-Step $Code "e8_tool_closure exit $Code" }
}

function Initialize-E8Step([string]$StepName, [int]$Attempt, [string[]]$Requires) {
    # the edition 4a step start at the run commit (Initialize-Step), then the erratum 8 checks
    # of the tool commit (8-9 (a) .. (a''), (f)); the two identity expectations go into the record
    Assert-ToolConfigured
    $Folder = Initialize-Step $StepName $Attempt $Requires
    $StepState.Codes['expect_simulation'] = "$RunCommit ($Worktree)"
    $StepState.Codes['expect_judge'] = "$ToolCommit ($ToolWorktree)"
    Assert-ToolCheckout
    Assert-ToolScripts
    Assert-ToolDiff
    Assert-E8FixedLists
    Assert-ToolClosure
    return $Folder
}

function Invoke-ToolJudge([string]$Label, [string[]]$Arguments, [int[]]$ContinueCodes = @(0)) {
    # 8-9 (a'): a judge command in the tool checkout - its working folder and its script (the
    # first argument, repository-relative) there, the checkout at the tool commit and clean;
    # both go into the step record. Returns the exit code; a code outside ContinueCodes stops.
    Assert-ToolCheckout
    $Script = [IO.Path]::GetFullPath((Join-Path $ToolWorktree $Arguments[0]))
    if (-not $Script.StartsWith("$ToolWorktree\", [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $Script -PathType Leaf)) {
        Stop-Step 3 "judge script $Script is not a file of the tool checkout"
    }
    Push-Location -LiteralPath $ToolWorktree
    try {
        $WorkingFolder = (Get-Location).Path
        $Code = Invoke-Tool $Label (@($Script) + @($Arguments | Select-Object -Skip 1))
    } finally { Pop-Location }
    $StepState.Codes["judge_identity:$Label"] = [ordered]@{ commit = $ToolCommit; is_clean = $true
        working_folder = $WorkingFolder; script = $Script }
    if ($ContinueCodes -notcontains $Code) { Stop-Step $Code "$Label exit $Code" }
    return $Code
}

function Get-E8BaseVbk0Folder {
    # 8-9 (e): the stopped 12b_vbk0_base_a1 (its b1 / b2 VBK0 outputs pass only through the
    # decide check of 8-9 (d))
    $Result = Get-E8BaseStop $RunsRoot
    if ($Result.ContainsKey('code')) { Stop-Step $Result.code $Result.reason }
    $StepState.Codes['e8_base_vbk0'] = Get-RepoPath $Result.folder
    return $Result.folder
}

function Invoke-E8Decide([string]$Out, [hashtable]$Vbk0Folders) {
    # jp3_12b_judge.py decide (erratum 8 8-8.1) in the tool checkout on the VBK0 blocks of
    # $Vbk0Folders (block -> folder with VBK0_<block>.json and VBK0_<block>_t4h) with the 8-1.3
    # expectations of b1 / b2 (8-9 (d)); exit 2 / 3 stop
    $Arguments = @("$Coupled/jp3_12b_judge.py", 'decide', '--selection', $X11Selection,
        '--selection-sha256', (Get-X11Sha), '--out', $Out)
    foreach ($Block in @('b1', 'b2', 'b4')) {
        if (-not $Vbk0Folders.ContainsKey($Block)) { continue }
        $Source = $Vbk0Folders[$Block]
        $Arguments += @('--vbk0', "$Block=$Source\VBK0_$Block.json", '--vbk0-t4h', "$Block=$Source\VBK0_${Block}_t4h")
    }
    foreach ($Block in $E8Vbk0Expected.Keys) {
        $Arguments += @('--expect-vbk0-sha256', "$Block=$($E8Vbk0Expected[$Block].run_sha256)",
            '--expect-vbk0-t4h-digest', "$Block=$($E8Vbk0Expected[$Block].t4h_digest)")
    }
    Invoke-ToolJudge 'decide' $Arguments | Out-Null
}

function Assert-E8Decision([string]$Path, [string[]]$Allowed) {
    # the decision record of this step has an allowed status (8-9 (d), 3); its file and sha256
    # go into the step record
    $Stop = Get-E8DecisionStop $Path $Allowed
    if ($Stop) { Stop-Step $Stop.code $Stop.reason }
    $StepState.Codes['decision_file'] = Get-RepoPath $Path
    $StepState.Codes['decision_sha256'] = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
    $StepState.Codes['decision_status'] = [string](Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json).status
}

function Assert-E8RunCondition([string]$BaseFolder, [string]$Setting, [hashtable]$Environment, [int]$Workers) {
    # 8-9 (c) before a VBK or b4 VBK0 run: its environment and --workers against the b1 / b2
    # VBK0 runs of the base step record
    $Record = Get-Content -Raw -LiteralPath "$BaseFolder\step_record.json" | ConvertFrom-Json
    foreach ($Block in $E8Vbk0Expected.Keys) {
        $Command = @($Record.commands | Where-Object { $_.label -eq "VBK0_$Block" })
        if ($Command.Count -ne 1) { Stop-Step 3 "base step record without one VBK0_$Block command" }
        $Stop = Get-E8EnvironmentStop $Command[0].environment $Environment $Setting $E8VbkExtraEnvironment
        if (-not $Stop) { $Stop = Get-E8WorkersStop $Command[0].command $Workers }
        if ($Stop) { Stop-Step $Stop.code "against VBK0_${Block}: $($Stop.reason)" }
    }
    $StepState.Codes["e8_run_condition:$Setting"] = 'environment and --workers as the b1 / b2 VBK0 runs (8-9 (c))'
}

function Assert-E8RunIdentity([string]$BaseFolder, [string]$IdentityPath) {
    # 8-9 (c) after a run: its identity record against the b1 / b2 VBK0 ones
    foreach ($Block in $E8Vbk0Expected.Keys) {
        $Stop = Get-E8IdentityStop "$BaseFolder\VBK0_$Block.identity.json" $IdentityPath $RunCommit
        if ($Stop) { Stop-Step $Stop.code $Stop.reason }
    }
    $StepState.Codes["e8_identity:$(Split-Path -Leaf $IdentityPath)"] = 'as the b1 / b2 VBK0 runs (8-9 (c))'
}
