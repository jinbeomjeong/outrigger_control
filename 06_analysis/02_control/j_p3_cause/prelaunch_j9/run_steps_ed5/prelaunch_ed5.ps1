#Requires -Version 7
# 436.9 J-P3 edition 5 prelaunch inputs (no simulation here; stored files only), in this order:
#   -Part dry     X-4 dry selection at the run commit (erratum 1 9.1: select scans again; its g8 /
#                 ref key files must have the fixed sha256, else not usable - ask the user again)
#   -Part l1keys  the 12b L1 key file (erratum 2 2-1, jp3_12b_l1_keys.py); then step_l1ref.ps1
#                 runs the two L1 reference runs and step_p5fixed.ps1 the P5-2 / P5-4 fixed
#                 values (simulations, before the fixed list; prelaunch audit B-2)
#   -Part x11     X-11 plans (jp3_12b_plan.py), ONCE, just before step0_cdry.ps1 (the c dry seeds
#                 92 / 93, erratum 6 6-3, must not collide with keys written later; user
#                 decision 2026-11-22)
#   -Part ckdrop  the T-CK / DROPOUT seeds, keys and plans (erratum 2 2-9.5, jp3_ckdrop_plan.py;
#                 after x11: it reads the 12b cell table and seeds; the same scan as x11)
#   -Part v0sample  the j9_main V0 sample key list (2-9.1, jp3_j9main_judge.py v0-sample-keys)
#                 and its generation command file
#   -Part list    FIXED_INPUTS_<run commit 8>.SHA256SUMS (jp3_fixed_inputs_list.py) after the
#                 main session committed the parts above, the L1 runs and the filled-in
#                 common_ed5.ps1; it lists the L1 key file, the two L1 runs and the P5-2 /
#                 P5-4 records (p52.json, p54.json of p5fixed.done's folder, the run commit's;
#                 -P5FixedCommit <sha> takes another commit's records only with a disjoint
#                 jp3_import_closure.py report of the simulation path, listed too;
#                 erratum 4 4-1) too; the main
#                 session then commits the list before step0_cdry.ps1 (order: common_ed5.ps1)
#   -ScanExtra    (x11) more probe record folders whose r79 key strings the seed scan reads
#                 (erratum 2 2-3: the run worktree's 05_tests is always scanned; the probe file
#                 ed5_design/probes/probes_ed5.json lies under 06_analysis, the base scan)
# Every part refuses an existing output (never overwritten). Exit: the tool's code.
param([Parameter(Mandatory)][ValidateSet('dry', 'l1keys', 'x11', 'ckdrop', 'v0sample', 'list')][string]$Part,
    [string[]]$ScanExtra = @(), [string]$P5FixedCommit = '')
. "$PSScriptRoot\common_ed5.ps1"

function Assert-PrelaunchCommit {
    # the run worktree at the run commit with a clean tracked tree (a git failure stops)
    $Head = (& git -C $Worktree rev-parse HEAD)
    if ($LASTEXITCODE -ne 0 -or $Head.Trim() -ne $RunCommit) { Write-Host "STOP: worktree HEAD $Head is not $RunCommit"; exit 3 }
    $Status = (& git -C $Worktree status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $Status) { Write-Host 'STOP: the run worktree is not clean (or git failed)'; exit 3 }
}

function Get-L1RefFolder {
    # the folder of the done l1ref step (its .done marker); none stops
    $Done = "$RunsRoot\l1ref.done"
    if (-not (Test-Path -LiteralPath $Done)) { Write-Host "STOP: $Done missing (run step_l1ref.ps1)"; exit 2 }
    return "$RunsRoot\$(Split-Path -Leaf (Get-Content -Raw -LiteralPath $Done | ConvertFrom-Json).folder)"
}

Assert-PrelaunchCommit
Set-Location -LiteralPath $Worktree
foreach ($Name in $ThreadEnvironment.Keys) { Set-Item -Path "Env:$Name" -Value $ThreadEnvironment[$Name] }
$env:PYTHONDONTWRITEBYTECODE = '1'
New-Item -ItemType Directory -Force -Path $Ed5Inputs | Out-Null

switch ($Part) {
    'dry' {
        if (Test-Path -LiteralPath $DrySelection) { Write-Host "STOP: $DrySelection exists"; exit 2 }
        & $RunExe -I -B "$Coupled/jp3_dryrun_evidence.py" select --out $DrySelection --scan-root $Analysis `
            --main-jsonl (Get-FixedPath 'MAIN_JSONL_SHA256') --baseline $BaselineDir `
            --dg3 (Get-FixedPath 'H6_SHA256') --noise (Get-FixedPath 'NOISE_VB_SHA256') `
            --keys-file (Get-FixedPath 'DRY_KEYS_FILE_SHA256')
    }
    'l1keys' {
        & $DevPython -I -B "$Coupled/jp3_12b_l1_keys.py" --noise (Get-FixedPath 'NOISE_VB_SHA256') `
            --out $L1KeysFile
    }
    'x11' {
        if (Test-Path -LiteralPath $X11Folder) { Write-Host "STOP: $X11Folder exists (the plans are made once)"; exit 2 }
        # erratum 1 audit E-1: the test sources and every probe record folder are scanned too
        $Extra = @('--scan-extra', "$Worktree\05_tests")
        foreach ($Root in $ScanExtra) { $Extra += @('--scan-extra', $Root) }
        & $DevPython -I -B "$Coupled/jp3_12b_plan.py" --noise (Get-FixedPath 'NOISE_VB_SHA256') `
            --scan-root $Analysis --out-dir $X11Folder @Extra
    }
    'ckdrop' {
        if (Test-Path -LiteralPath $CkdropFolder) { Write-Host "STOP: $CkdropFolder exists (made once)"; exit 2 }
        $Extra = @('--scan-extra', "$Worktree\05_tests")
        foreach ($Root in $ScanExtra) { $Extra += @('--scan-extra', $Root) }
        $X11Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $X11Selection).Hash.ToLower()
        & $DevPython -I -B "$Coupled/jp3_ckdrop_plan.py" --selection $X11Selection --selection-sha256 $X11Sha `
            --scan-root $Analysis --out-dir $CkdropFolder @Extra
    }
    'v0sample' {
        if (Test-Path -LiteralPath $V0SampleKeysFile) { Write-Host "STOP: $V0SampleKeysFile exists"; exit 2 }
        $Arguments = @('-I', '-B', "$Coupled/jp3_j9main_judge.py", 'v0-sample-keys', '--v0', (Get-FixedPath 'MAIN_JSONL_SHA256'),
            '--v0-sha256', $FixedInputs['MAIN_JSONL_SHA256'][1], '--out', $V0SampleKeysFile)
        # 2-9.1: the generation command goes into the fixed list with the key list
        [IO.File]::WriteAllText($V0SampleCommandFile, "$RunExe $($Arguments -join ' ')`n")
        & $RunExe @Arguments
    }
    'list' {
        $L1Folder = Get-L1RefFolder
        $Add = @('--add', $L1KeysFile)
        foreach ($Setting in $L1Settings) { $Add += @('--add', "$L1Folder\L1_$Setting.json") }
        # prelaunch audit B-2 / erratum 4 4-1: the P5-2 / P5-4 fixed records of step_p5fixed.ps1,
        # computed at the run commit; records of another commit (-P5FixedCommit) only with a
        # disjoint import closure of the simulation path between it and the run commit (its
        # report goes into the list; meets = compute again at the run commit)
        if (-not $P5FixedCommit) { $P5FixedCommit = $RunCommit }
        if ($P5FixedCommit -notmatch '^[0-9a-f]{40}$') { Write-Host "STOP: -P5FixedCommit $P5FixedCommit is not a full sha"; exit 2 }
        $P5Root = "$CauseDir\j9_runs\$($P5FixedCommit.Substring(0, 8))"
        $P5Done = "$P5Root\p5fixed.done"
        if (-not (Test-Path -LiteralPath $P5Done)) { Write-Host "STOP: $P5Done missing (run step_p5fixed.ps1)"; exit 2 }
        $P5Folder = "$P5Root\$(Split-Path -Leaf (Get-Content -Raw -LiteralPath $P5Done | ConvertFrom-Json).folder)"
        foreach ($Name in $P5FixedNames) { $Add += @('--add', "$P5Folder\judge\$Name") }
        if ($P5FixedCommit -ne $RunCommit) {
            $Closure = "$Ed5Inputs\p5fixed_import_closure_$($P5FixedCommit.Substring(0, 8)).json"
            if (Test-Path -LiteralPath $Closure) { Write-Host "STOP: $Closure exists"; exit 2 }
            $Entries = @(); foreach ($Entry in $P5FixedEntries) { $Entries += @('--entry', $Entry) }
            & $DevPython -I -B "$Coupled/jp3_import_closure.py" --repo $Worktree @Entries `
                --base $P5FixedCommit --head $RunCommit --out $Closure
            if ($LASTEXITCODE -ne 0) {
                Write-Host "STOP: the simulation path changed between $P5FixedCommit and $RunCommit (import closure exit $LASTEXITCODE): compute the fixed values again at the run commit"
                exit 2
            }
            $Add += @('--add', $Closure)
        }
        & $DevPython -I -B "$Coupled/jp3_fixed_inputs_list.py" --repo $MainRoot --worktree $Worktree `
            --commit $RunCommit --entries $EntriesFile --x11-selection $X11Selection `
            --dry-selection $DrySelection --out $FixedList @Add
    }
}
exit $LASTEXITCODE
