#Requires -Version 7
# Stage 5 (G' V0 pre-run, spec v8 7.3 .. 7.5) judgement at T8'''' 7ea78232, fixed before the
# stage 5 outputs are opened (audit verif_stage5_prerun.md record 12, main session advice 2).
# Same form as stage4_prejudge_t8pppp\run_stage4_gates_t8pppp.ps1: the locked judge checkout
# ed8-judge4, HEAD and `status --porcelain --ignored` 0 lines before and after, dynamics-dev
# python.exe -I -B called directly, a new numba cache folder, an existing output refused.
# Before the judge it asserts the sha256 of every input it reads: the sealed held-out keys and
# the grid keys (the judge pins them too), the four stored V0 grid files under --grid-root
# (raw sha256 and git blob, recorded in grid_blobs.txt; the judge does not pin them), and the
# three stage 5 outputs and their step records (hashed after the runs ended, values unread).
# Run by the main session after the pre-judgement audit; a rerun needs a new output path and a
# new numba cache folder (both are refused when present).
#
# Exit (the judge's own exit passed through, jp3_ed8_judge.py module docstring):
#   0  judge exit 0: status frozen
#   1  judge exit 1: status stop (spec 7.3 4 / 7.4)
#   2  judge exit 2: setting_defect or not_judgeable (an input or step record defect, a missing
#      line, an existing --out)
#   3  judge exit 3: tool error
#   4  stop and ask: the judge checkout changed during the run, the after check failed (a git
#      error, kept apart from a change), or the judge process could not be started
#   5  refused before the judge: a precondition or an input sha256 differs (nothing written)
$ErrorActionPreference = 'Stop'
$JudgeRoot = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4'
$JudgeHead = '7ea782323c427917709ecbb365a58044449beac2'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$MainRoot = 'C:\workspace\outrigger_control'
$RunRoot = Join-Path $MainRoot '06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$Out = Join-Path $RunRoot 'judge_7ea78232_s5\ho_k_selection.json'
$NumbaCache = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\judge_7ea78232_stage5'
$Keys = Join-Path $MainRoot '06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json'
$GridKeys = Join-Path $MainRoot '06_analysis\02_control\j_p3_cause\ed6_design\keys\confirm_b_grid192.json'
$PinnedSha = [ordered]@{
    $Keys     = 'a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5'
    $GridKeys = '4e80e69bd2233b994853ae3f60ed0749f2c39c7dbb6390bc012b016efa5cf85b'
    (Join-Path $RunRoot 'ho_v0_a1\ed8_heldout_v0.jsonl')   = 'fd5f85f529d7a85aecba8588743ae18eb215e3ca1d7df22fe26acfe3f6c333d8'
    (Join-Path $RunRoot 'ho_v0.done')                      = 'c5f2df09c5c760bea25578f156c77cf7bb05df28ec320d1b223b09832bb4a837'
    (Join-Path $RunRoot 'ho_aa2_a1\ed8_heldout_aa2.jsonl') = '182dcaabbd1e29642386645a4d95521b83ff5d0fe14639ca5172d77e92dbd6b2'
    (Join-Path $RunRoot 'ho_aa2.done')                     = '6432bccb1b3c2a8015781cffb5f60d0e6a2ca3b703a4cafb513c3daa9eca3500'
    (Join-Path $RunRoot 'ho_aa3_a1\ed8_heldout_aa3.jsonl') = 'a2d65df1833442b422668b1ada4abc1187a65ca9fdb791eb93d1a4b7e4b448a1'
    (Join-Path $RunRoot 'ho_aa3.done')                     = '4669f443df7c3e8872628e632eaf39e1c951edb3f8d15f4373b755451d7765d1'
}
# The stored V0 grid files (grid_blobs.txt): main checkout path, git blob, raw sha256.
$GridDir = '06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid'
$GridFiles = [ordered]@{
    "$GridDir/grid_r67_main.json"   = @('1f88d9c98760353e90dbcdc6c00123c320cf8020', 'a2e74481760a27695ac63800a650e0be1b9b3980fcfaef1f1b64d4e98628316d')
    "$GridDir/grid_r67_top.json"    = @('8797afe1dd3e9d4dbe7508c1070eda330d6cfe57', '1d07e49fdbcaf375c4266866ff6955569c967d6d4eb9d4babc07558a64e92559')
    "$GridDir/grid_r69_bottom.json" = @('d4f3f8c69358f858daa34144e3531cda6fb9919e', '91026c460489463aa34e0377236854c892e46257d55133bda9c777584b548a89')
    "$GridDir/grid_r69_top.json"    = @('33e7508d5f027aef1884066f43e28bce183e8b9c', '87e8d72a25a5d40cccedce1c632a7e4f168f126aed38ada8a3b6760794d02390')
}

function Stop-Refused([string] $Reason) {
    Write-Output "REFUSED: $Reason"
    exit 5
}

function Assert-JudgeCheckout {
    $head = (& git -C $JudgeRoot rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { Stop-Refused 'git rev-parse failed' }
    if ($head.Trim() -ne $JudgeHead) { Stop-Refused "judge HEAD $head" }
    $dirty = @(& git -C $JudgeRoot status --porcelain --ignored)
    if ($LASTEXITCODE -ne 0) { Stop-Refused 'git status failed' }
    if ($dirty.Count -ne 0) {
        Stop-Refused "judge checkout not clean (tracked, untracked or ignored): $($dirty.Count) lines"
    }
}

function Assert-PinnedInputs {
    foreach ($path in $PinnedSha.Keys) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { Stop-Refused "input missing: $path" }
        $digest = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($digest -ne $PinnedSha[$path]) { Stop-Refused "sha256 differs: $path" }
    }
}

function Assert-GridFiles {
    $names = @($GridFiles.Keys)
    $blobs = @(& git -C $MainRoot hash-object -- @names)
    if ($LASTEXITCODE -ne 0 -or $blobs.Count -ne $names.Count) { Stop-Refused 'git hash-object failed' }
    $dirty = @(& git -C $MainRoot status --porcelain --ignored -- @names)
    if ($LASTEXITCODE -ne 0) { Stop-Refused 'git status (grid files) failed' }
    if ($dirty.Count -ne 0) { Stop-Refused "grid files not clean: $($dirty.Count) lines" }
    for ($i = 0; $i -lt $names.Count; $i++) {
        $expected = $GridFiles[$names[$i]]
        if ($blobs[$i].Trim() -ne $expected[0]) { Stop-Refused "grid blob differs: $($names[$i])" }
        $digest = (Get-FileHash -LiteralPath (Join-Path $MainRoot $names[$i]) -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($digest -ne $expected[1]) { Stop-Refused "grid sha256 differs: $($names[$i])" }
    }
}

try {
    if (Test-Path -LiteralPath $Out) { Stop-Refused "output exists: $Out" }
    # A new output folder (user decision 2026-11-28, option ga of verif_stage5_prejudge.md); the judge makes it (out.parent.mkdir).
    if (Test-Path -LiteralPath (Split-Path -Parent $Out)) { Stop-Refused "output folder exists: $(Split-Path -Parent $Out)" }
    if (Test-Path -LiteralPath $NumbaCache) { Stop-Refused "numba cache folder exists: $NumbaCache" }
    Assert-JudgeCheckout
    Assert-PinnedInputs
    Assert-GridFiles
}
catch {
    Stop-Refused "precondition check error: $_"
}
$env:MKL_THREADING_LAYER = 'TBB'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = $NumbaCache
$Ed8 = '04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py'
$JudgeExit = $null
Push-Location -LiteralPath $JudgeRoot
try {
    # The --v0-rows / --step-done pairs are matched by position (judge_stage5): v0, aa2, aa3.
    & $Py -I -B $Ed8 stage5 `
        --keys $Keys `
        --grid-keys $GridKeys `
        --grid-root $MainRoot `
        --v0-rows "$RunRoot\ho_v0_a1\ed8_heldout_v0.jsonl" --step-done "$RunRoot\ho_v0.done" `
        --v0-rows "$RunRoot\ho_aa2_a1\ed8_heldout_aa2.jsonl" --step-done "$RunRoot\ho_aa2.done" `
        --v0-rows "$RunRoot\ho_aa3_a1\ed8_heldout_aa3.jsonl" --step-done "$RunRoot\ho_aa3.done" `
        --out $Out
    $JudgeExit = $LASTEXITCODE
}
catch {
    Write-Output "STOP: the judge could not be started: $_"
    exit 4
}
finally {
    Pop-Location
}
Write-Output "stage5 exit $JudgeExit"
$headAfter = (& git -C $JudgeRoot rev-parse HEAD)
$headCode = $LASTEXITCODE
$dirtyAfter = @(& git -C $JudgeRoot status --porcelain --ignored)
$statusCode = $LASTEXITCODE
if ($headCode -ne 0 -or $statusCode -ne 0) {
    Write-Output 'STOP: the after check of the judge checkout failed (git error, not a change)'
    exit 4
}
if ($headAfter.Trim() -ne $JudgeHead -or $dirtyAfter.Count -ne 0) {
    Write-Output "STOP: judge checkout changed (head $headAfter, $($dirtyAfter.Count) status lines)"
    exit 4
}
exit $JudgeExit
