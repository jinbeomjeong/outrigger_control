#Requires -Version 7
# Edition 8 P8-4 rule-baseline-style rerun at T8'''' 7ea78232 (one run, no automatic rerun, not a C8 rerun).
# Same command as the original run_p84.ps1 '-Side run' (C8 56849248): full_suite_ed8.ps1 -> tools\verif\worktree_tests.py
# (serial pytest, Chrono-dev, main checkout data, no affinity, no priority change), judged against the
# base list of 41e107e9 (p84\base\existing_failures.txt, sha 7fce20f4...). Only the target worktree differs.
$ErrorActionPreference = 'Continue'
$Here = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84wt_7ea78232'
$Out = "$Here\out"
$Wt = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4'
$Expect = '7ea782323c427917709ecbb365a58044449beac2'
$Steps = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-impl\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed8'
$List = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84\base\existing_failures.txt'
$ListSha = '7fce20f4ab74c6e2137a9cd29d7e60e18d6459cce00b88d774618102fe0ae953'
$Log = "$Here\p84wt_driver.log"
function Log($m) { "$((Get-Date).ToString('o')) $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
function Stop-Run($m) {
    Log "[stop] $m"
    New-Item -ItemType Directory -Force -Path $Out | Out-Null
    "$m" | Out-File -FilePath "$Out\p84.stop" -Encoding utf8
    exit 3
}

if (Test-Path -LiteralPath $Out) { Stop-Run 'out folder already exists (never rerun automatically)' }
Log "[start] P8-4 worktree_tests style, T8pppp $Expect"
$Head = (& git -C $Wt rev-parse HEAD).Trim()
$StatusBefore = @(& git -C $Wt status --porcelain --ignored)
Log "[before] head=$Head status_lines=$($StatusBefore.Count)"
if ($Head -ne $Expect) { Stop-Run "HEAD $Head is not $Expect" }
if ($StatusBefore.Count -ne 0) { Stop-Run 'worktree not clean (status --porcelain --ignored non-empty)' }
if (-not (Test-Path -LiteralPath $List)) { Stop-Run "baseline list missing: $List" }
$Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $List).Hash.ToLower()
if ($Sha -ne $ListSha) { Stop-Run "baseline list sha $Sha differs from $ListSha" }

# same as original run_p84.ps1: numba cache outside the worktree (fresh folder here)
$env:NUMBA_CACHE_DIR = "$Here\numba_cache"
New-Item -ItemType Directory -Force -Path $env:NUMBA_CACHE_DIR | Out-Null

$t0 = Get-Date
Log '[run] begin'
& pwsh -NoProfile -File "$Steps\full_suite_ed8.ps1" -Side run -Worktree $Wt -OutDir $Out -ExpectCommit $Expect `
    -BaselineList $List -BaselineSha256 $Sha *>> "$Here\run_console.log"
$er = $LASTEXITCODE
$secs = [int]((Get-Date) - $t0).TotalSeconds
Log "[run] end exit=$er wall_s=$secs"

New-Item -ItemType Directory -Force -Path $Out | Out-Null
$StatusAfter = @(& git -C $Wt status --porcelain --ignored)
$StatusAfter | Out-File "$Out\git_after.txt" -Encoding utf8
$Pyc = @($StatusAfter | Where-Object { $_ -match '__pycache__' })
$Pyc | Out-File "$Out\pycache_paths.txt" -Encoding utf8
Log "[after] status lines=$($StatusAfter.Count) pycache lines=$($Pyc.Count) head=$((& git -C $Wt rev-parse HEAD).Trim())"
"exit=$er wall_s=$secs" | Out-File "$Out\p84.done" -Encoding utf8
exit $er
