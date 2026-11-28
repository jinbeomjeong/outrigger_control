#Requires -Version 7.2
# 436.9 edition 9 R3 (ed9_design/d1_prerun/impl_report_2.md): one run_v5 batch at the run commit
# C9, with a .done in the form jp3_ed8_gate_judge.step_output_problems reads (exit_code, commit,
# folder, codes.identity_start / identity_end {head, is_clean}).
#   -Batch      a run_v5 batch (ed8_heldout_v0 / aa2 / aa3 = C-m off, ed9_* = C-m on, the switch
#               is the batch: run_v5.D1_MEDIAN_BATCHES)
#   -Step       the step name (the .done is <Root>\<Step>.done, the folder <Root>\<Step>_a1)
#   -Root       a NEW folder under ed9_design\d1_prerun (outputs are never overwritten)
#   -JobsFile   the sealed key file for the held-out batches (omit for ed9_census_v0)
# Interpreter: dynamics-dev python.exe -I -B directly (the edition 8 stage 5 call,
# common_ed8.ps1 Start-Ed8Run), NUMBA_CACHE_DIR outside the worktree.
# Exit: 0 done; 2 an output exists; 3 identity / input problem; else the run_v5 exit code.
param([Parameter(Mandatory)][string]$Batch, [Parameter(Mandatory)][string]$Step,
    [Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$Commit,
    [Parameter(Mandatory)][string]$Worktree, [string]$JobsFile = '',
    [Parameter(Mandatory)][string]$MaskHex, [Parameter(Mandatory)][int]$Workers)
$ErrorActionPreference = 'Stop'
$Python = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$NumbaCache = "C:\Users\jinbeom\.claude\runners\outrigger-ed9-r3\numba_cache\$($Commit.Substring(0, 8))"

function Get-Identity {
    $Head = (& git -C $Worktree rev-parse HEAD)
    $HeadOk = $LASTEXITCODE -eq 0
    $Status = (& git -C $Worktree status --porcelain --untracked-files=no)
    $StatusOk = $LASTEXITCODE -eq 0
    return [ordered]@{ head = if ($HeadOk) { [string]$Head.Trim() } else { $null }
        is_clean = if ($StatusOk) { -not $Status } else { $null }
        time = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') }
}

function Stop-R3([int]$Code, [string]$Reason) {
    Write-Host "STOP: $Reason"
    exit $Code
}

$Folder = Join-Path $Root "${Step}_a1"
$Done = Join-Path $Root "$Step.done"
foreach ($Path in @($Folder, $Done)) {
    if (Test-Path -LiteralPath $Path) { Stop-R3 2 "$Path exists (every output path is new)" }
}
if ($Commit -notmatch '^[0-9a-f]{40}$') { Stop-R3 3 "commit $Commit is not a full sha" }
$Start = Get-Identity
if ($Start.head -ne $Commit -or $Start.is_clean -ne $true) {
    Stop-R3 3 "worktree $Worktree HEAD $($Start.head) clean $($Start.is_clean), expected $Commit clean"
}
New-Item -ItemType Directory -Force -Path $Folder | Out-Null
New-Item -ItemType Directory -Force -Path $NumbaCache | Out-Null
$Rows = Join-Path $Folder "$Batch.jsonl"
$Arguments = @('-I', '-B', '04_scripts/04_hydraulic/coupled/run_v5.py', $Batch)
if ($JobsFile) { $Arguments += @('--jobs-file', $JobsFile) }
$Arguments += @('--out', $Rows, '--workers', "$Workers", '--mask', $MaskHex)
$env:NUMBA_CACHE_DIR = $NumbaCache
$Started = Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'
Push-Location -LiteralPath $Worktree
try {
    & $Python @Arguments *> (Join-Path $Folder 'run_v5.log')
    $Code = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Item Env:NUMBA_CACHE_DIR -ErrorAction SilentlyContinue
}
$End = Get-Identity
if ($Code -ne 0) { Stop-R3 $Code "run_v5 exit $Code (see $Folder\run_v5.log); no .done" }
if ($End.head -ne $Commit -or $End.is_clean -ne $true) { Stop-R3 3 "identity at the end: $($End.head) clean $($End.is_clean); no .done" }
$Record = [ordered]@{ step = $Step; folder = $Folder; exit_code = 0; commit = $Commit
    started = $Started; done = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    codes = [ordered]@{ identity_start = $Start; identity_end = $End; batch = $Batch
        invocation = 'python.exe -I -B'; python = $Python; numba_cache_dir = $NumbaCache
        mask = $MaskHex; workers = $Workers; jobs_file = $JobsFile }
    commands = @("$Python $($Arguments -join ' ')") }
$Record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Done -Encoding utf8
Write-Host "DONE $Step -> $Folder"
exit 0
