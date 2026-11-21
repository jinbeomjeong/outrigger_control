#Requires -Version 7
# Step (6v) addendum 4a-8 6.2: the VBJ bundle of T-JR-12 judged again at the fixed commit, from
# the stored VBJ / VBJ0 Dg-3 outputs of 78fd5d2d (sha fixed, 4a-8 7) with new plant_truth L1
# references. The VBH bundle and steps (1) .. (5) are not run again (4a-8 6.3).
#   0. 6.1: the static import closure of las_t3_dg3.py against git diff 78fd5d2d..fixed commit
#      (jp3_import_closure.py; any shared file stops: the exception does not hold, 5.3 b)
#   1. 4.2 / erratum 1 3: the L1 key file made again (jp3_tjr_judge.py l1-keys, 102 keys of the
#      stored H-6) and compared with the fixed prelaunch_j9\l1_keys_d3c6c57e.json (sha); the
#      L1 runs and dg3-judge use the fixed file
#   2. 4.3: L1 runs of VBJ and VBJ0 at once (las_t3_dg3.py --levels L1 --keys-file, identity
#      wrapper), the identity check at the fixed commit, the 4.5 command hash record
#   3. 4.4 / 5: dg3-judge VBJ0, then VBJ (each with its own L1 run; the judge rows checked)
#   4. 13.9: t12 --bundle VBJ (base VBJ0) with the two judge files
# Exit codes: 0 done, 1 / 2 / 3 = the tool's code (4a-5 5.1: stop), 3 also for a broken
# precondition (commit, tree, fixed or re-judgement input).
param([int]$Attempt = 1, [int]$Workers = 4, [string]$VbjMask = '0x00FF', [string]$Vbj0Mask = '0xFF00')
. "$PSScriptRoot\common.ps1"

# --- the fixed commit (4a-8 6.1; common.ps1 holds the 78fd5d2d run of steps (1) .. (7)) ------
$RunCommit = 'd3c6c57e27f5b5448ecc33708b955773705ab22e'
$RunShort = $RunCommit.Substring(0, 8)
$RunsRoot = "$CauseDir\j9_runs\$RunShort"
$IdentityChecks = "$RunsRoot\_identity_checks"
$StoredRunCommit = '78fd5d2d03e40ac7d9143429f602b58255c762fc'
$StoredDg3Dir = "$CauseDir\j9_runs\$($StoredRunCommit.Substring(0, 8))\dg3_a1"
$Tjr = "$Coupled/jp3_tjr_judge.py"
# 4a-8 6.2 3 / 7: the stored Dg-3 outputs read here (the same values as jp3_rejudge_inputs.py)
$RejudgeInputs = [ordered]@{
    DG3_VBJ0_SHA256 = @("$StoredDg3Dir\dg3_VBJ0.json", 'c1201b2d160dc2fee08671cdb285df65fa367e22b2e6af643e87c5216252b9c7')
    DG3_VBJ_SHA256  = @("$StoredDg3Dir\dg3_VBJ.json", '603e4b815d8abc11f09bb85731f9591df5e4c6cc812f2dd9f0e6c7ebae070cd0')
}
$L1Masks = [ordered]@{ VBJ = $VbjMask; VBJ0 = $Vbj0Mask }
# 4a-8 erratum 1 3: the L1 key file made before the run by the fixed commit's generator
# (jp3_tjr_judge.py l1-keys on the stored H-6 ea0ab94c and the P-1a extract a591c3a8), fixed by
# sha; the L1 runs and dg3-judge use this file, step 1 makes it again and compares
$FixedL1KeysFile = "$PrelaunchDir\l1_keys_d3c6c57e.json"
$FixedL1KeysSha256 = 'eea8ed0d5f3aa79ecb5cf1cb892fa82f7d4bac780f8b3b17dbd069200765c6af'

function Assert-RejudgeInputs {
    # 4a-8 6.2 3: each stored Dg-3 file has its fixed sha (missing or other: not judgeable), and
    # jp3_rejudge_inputs.py at the fixed commit holds the same values
    foreach ($Name in $RejudgeInputs.Keys) {
        $Path, $Expected = $RejudgeInputs[$Name]
        if (-not (Test-Path -LiteralPath $Path)) { Stop-Step 2 "re-judgement input $Name missing: $Path" }
        $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower()
        if ($Actual -ne $Expected) { Stop-Step 2 "re-judgement input $Name sha256 $Actual is not $Expected" }
    }
    $Code = 'import sys; sys.path.insert(0, sys.argv[1]); import jp3_rejudge_inputs as r; ' +
        '[print(n, getattr(r, n)) for n in sys.argv[2:]]'
    $Lines = @(& $DevPython -I -B -c $Code "$Worktree\04_scripts\04_hydraulic\coupled" @($RejudgeInputs.Keys))
    if ($LASTEXITCODE -ne 0 -or $Lines.Count -ne $RejudgeInputs.Count) { Stop-Step 3 'jp3_rejudge_inputs import failed' }
    foreach ($Line in $Lines) {
        $Name, $Value = $Line -split ' ', 2
        if ($RejudgeInputs[$Name][1] -ne $Value) { Stop-Step 3 "jp3_rejudge_inputs.$Name $Value differs from this file" }
    }
    # 4a-8 erratum 1 3: the fixed L1 key file (missing or other: not judgeable)
    if (-not (Test-Path -LiteralPath $FixedL1KeysFile)) { Stop-Step 2 "fixed L1 key file missing: $FixedL1KeysFile" }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $FixedL1KeysFile).Hash.ToLower()
    if ($Actual -ne $FixedL1KeysSha256) { Stop-Step 2 "fixed L1 key file sha256 $Actual is not $FixedL1KeysSha256" }
}

$Folder = Initialize-Step 'dg3_vbj' $Attempt @()
Assert-RejudgeInputs

# 0. 4a-8 6.1: the import closure of the runner against the files the fixed commit changed
Invoke-Judge 'import_closure' @("$Coupled/jp3_import_closure.py", '--repo', $Worktree,
    '--entry', "$Coupled/las_t3_dg3.py", '--base', $StoredRunCommit, '--head', $RunCommit,
    '--out', "$Folder\judge\import_closure.json") | Out-Null

# 1. 4a-8 4.2 / erratum 1 3: the L1 key file made again in the attempt folder; it must be the
# fixed file byte for byte (sha), else not judgeable. The runs use the fixed file.
$RemadeKeysFile = "$Folder\l1_keys.json"
Invoke-Judge 'l1_keys' @($Tjr, 'l1-keys', '--h6', (Get-FixedPath 'H6_SHA256'), '--keys-out', $RemadeKeysFile,
    '--l1-extract', (Get-FixedPath 'STORED_H6_L1_REFERENCE_SHA256'), '--out', "$Folder\judge\l1_keys.json") | Out-Null
$RemadeSha = Read-ReportField "$Folder\judge\l1_keys.json" 'keys_file_sha256'
$StepState.Codes['l1_keys_sha256'] = $RemadeSha
if ($RemadeSha -ne $FixedL1KeysSha256) {
    Stop-Step 2 "the remade L1 key file sha256 $RemadeSha is not the fixed $FixedL1KeysSha256 (4a-8 erratum 1 3)"
}
$KeysFile = $FixedL1KeysFile

# 2. 4a-8 4.3: the L1 runs (the Dg-3 run environment of the setting, plant_truth)
$Runs = @()
foreach ($Setting in $L1Masks.Keys) {
    $Out = "$Folder\l1_$Setting.json"
    $Environment = @{ R79_V5_SETTING = $Setting; R79_T4H_DIR = "$Folder\${Setting}_L1_t4h"
        R79_ROD_MODEL = 'plant_truth' } + $R79Common
    $Runs += Start-Run -Label "l1_$Setting" -MaskHex $L1Masks[$Setting] -WrapOutput $Out -Environment $Environment `
        -TaskType 'jp3_l1_r79' -Workers $Workers -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L1', '--keys-file', $KeysFile, '--workers', "$Workers", '--affinity', $L1Masks[$Setting])
}
Wait-Runs $Runs
Invoke-IdentityCheck
$L1Sha = @{}
foreach ($Setting in $L1Masks.Keys) {
    $L1Sha[$Setting] = (Get-FileHash -Algorithm SHA256 -LiteralPath "$Folder\l1_$Setting.json").Hash.ToLower()
    $StepState.Codes["l1_${Setting}_sha256"] = $L1Sha[$Setting]
}
Invoke-Judge 'l1_hash_record' @($Tjr, 'l1-hash-record', '--vbj-l1', "$Folder\l1_VBJ.json",
    '--vbj0-l1', "$Folder\l1_VBJ0.json", '--out', "$Folder\judge\l1_hash_record.json") | Out-Null

# 3. 4a-8 4.4 / 5: the r79 judge files of VBJ0 and VBJ, each with its own L1 run
$JudgeSha = @{}
foreach ($Setting in @('VBJ0', 'VBJ')) {
    $Report = "$Folder\judge\dg3_${Setting}_judge_report.json"
    Invoke-Judge "dg3_judge_$Setting" @($Tjr, 'dg3-judge', '--setting', $Setting,
        '--dg3', $RejudgeInputs["DG3_${Setting}_SHA256"][0], '--dg3-sha256', $RejudgeInputs["DG3_${Setting}_SHA256"][1],
        '--l1-reference', "$Folder\l1_$Setting.json", '--l1-reference-sha256', $L1Sha[$Setting],
        '--l1-keys-file', $KeysFile, '--judge-out', "$Folder\judge\dg3_${Setting}_judge.json",
        '--out', $Report) | Out-Null
    $JudgeSha[$Setting] = Read-ReportField $Report 'judge_sha256'
}

# 4. 13.9: T-JR-12 VBJ bundle (4a-8 2 B2 k, 5 judge rows); 1 is reported as it is (6.4)
$VbjCode = Invoke-Tool 't12_VBJ' @($Tjr, 't12', '--bundle', 'VBJ', '--base', $RejudgeInputs['DG3_VBJ0_SHA256'][0],
    '--base-judge', "$Folder\judge\dg3_VBJ0_judge.json", '--base-judge-sha256', $JudgeSha['VBJ0'],
    '--new', $RejudgeInputs['DG3_VBJ_SHA256'][0], '--new-judge', "$Folder\judge\dg3_VBJ_judge.json",
    '--new-judge-sha256', $JudgeSha['VBJ'], '--out', "$Folder\judge\t12_VBJ.json")
if ($VbjCode -ne 0) { Stop-Step $VbjCode "t12 VBJ exit $VbjCode" }

Complete-Step
