#Requires -Version 7
# 436.9 J-P3 edition 5 prelaunch inputs (no simulation; stored files only), in this order:
#   -Part dry    X-4 dry selection at the run commit (erratum 1 9.1: select scans again; its g8 /
#                ref key files must have the fixed sha256, else not usable - ask the user again)
#   -Part x11    X-11 plans (jp3_12b_plan.py), ONCE, just before step0_cdry.ps1 (the c dry seeds
#                90 / 91 must not collide with keys written later; user decision 2026-11-22)
#   -Part list   FIXED_INPUTS_<run commit 8>.SHA256SUMS (jp3_fixed_inputs_list.py) after the
#                main session committed the two parts above and the filled-in common_ed5.ps1
# Every part refuses an existing output (never overwritten). Exit: the tool's code.
#   -ScanExtra   (x11) more probe record folders whose r79 key strings the seed scan reads
param([Parameter(Mandatory)][ValidateSet('dry', 'x11', 'list')][string]$Part, [string[]]$ScanExtra = @())
. "$PSScriptRoot\common_ed5.ps1"

function Assert-PrelaunchCommit {
    # the run worktree at the run commit with a clean tracked tree (a git failure stops)
    $Head = (& git -C $Worktree rev-parse HEAD)
    if ($LASTEXITCODE -ne 0 -or $Head.Trim() -ne $RunCommit) { Write-Host "STOP: worktree HEAD $Head is not $RunCommit"; exit 3 }
    $Status = (& git -C $Worktree status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $Status) { Write-Host 'STOP: the run worktree is not clean (or git failed)'; exit 3 }
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
    'x11' {
        if (Test-Path -LiteralPath $X11Folder) { Write-Host "STOP: $X11Folder exists (the plans are made once)"; exit 2 }
        # erratum 1 audit E-1: the test sources and every probe record folder are scanned too
        $Extra = @('--scan-extra', "$Worktree\05_tests")
        foreach ($Root in $ScanExtra) { $Extra += @('--scan-extra', $Root) }
        & $DevPython -I -B "$Coupled/jp3_12b_plan.py" --noise (Get-FixedPath 'NOISE_VB_SHA256') `
            --scan-root $Analysis --out-dir $X11Folder @Extra
    }
    'list' {
        & $DevPython -I -B "$Coupled/jp3_fixed_inputs_list.py" --repo $MainRoot --worktree $Worktree `
            --commit $RunCommit --entries $EntriesFile --x11-selection $X11Selection `
            --dry-selection $DrySelection --out $FixedList
    }
}
exit $LASTEXITCODE
