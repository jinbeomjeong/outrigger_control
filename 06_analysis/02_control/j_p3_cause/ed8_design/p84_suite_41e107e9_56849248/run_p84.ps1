#Requires -Version 7
# Edition 8 P8-4 (spec v8 12, 11.1): full unit suite at the implementation commit 41e107e9 (base list),
# then at the run commit C8 56849248 judged against that list. Both in fresh detached checkouts
# (not the locked run worktree). No automatic rerun. Writes p84_driver.log and p84.done.
$ErrorActionPreference = 'Continue'
$Repo = 'C:\workspace\outrigger_control'
$Here = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\p84'
$Steps = "$Repo\.claude\worktrees\ed8-impl\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed8"
$Base = '41e107e98a5b0e45c3197dbfee46e8dd033eba35'
$Run = '56849248371b4916e2fe683265e7abffdd6fb8d7'
$WtBase = "$Repo\.claude\worktrees\ed8-base41"
$WtRun = "$Repo\.claude\worktrees\ed8-suite-c8"
$Log = "$Here\p84_driver.log"
function Write-Log($m) { "$((Get-Date).ToString('o')) $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
function Get-NumbaFiles($w) { @(Get-ChildItem -LiteralPath $w -Recurse -File -Include '*.nbi', '*.nbc' -ErrorAction SilentlyContinue).Count }

$env:NUMBA_CACHE_DIR = "$Here\numba_cache"
New-Item -ItemType Directory -Force -Path $env:NUMBA_CACHE_DIR | Out-Null
Write-Log "[start] P8-4 base $Base run $Run, NUMBA_CACHE_DIR $env:NUMBA_CACHE_DIR"
& git -C $Repo worktree add --detach $WtBase $Base 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8
& git -C $Repo worktree add --detach $WtRun $Run 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8

Write-Log "[base] begin"
& pwsh -NoProfile -File "$Steps\full_suite_ed8.ps1" -Side base -Worktree $WtBase -OutDir "$Here\base" -ExpectCommit $Base *>> "$Here\base_console.log"
$eb = $LASTEXITCODE
Write-Log "[base] end exit=$eb numba_files=$(Get-NumbaFiles $WtBase) status=[$(& git -C $WtBase status --porcelain --ignored)]"
if ($eb -ne 0) { Write-Log "[stop] base exit $eb"; New-Item -ItemType File -Force -Path "$Here\p84.done" | Out-Null; exit $eb }

$List = "$Here\base\existing_failures.txt"
$Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $List).Hash.ToLower()
Write-Log "[run] begin baseline $Sha"
& pwsh -NoProfile -File "$Steps\full_suite_ed8.ps1" -Side run -Worktree $WtRun -OutDir "$Here\run" -ExpectCommit $Run -BaselineList $List -BaselineSha256 $Sha *>> "$Here\run_console.log"
$er = $LASTEXITCODE
Write-Log "[run] end exit=$er numba_files=$(Get-NumbaFiles $WtRun) status=[$(& git -C $WtRun status --porcelain --ignored)]"
Write-Log "[done] base=$eb run=$er"
New-Item -ItemType File -Force -Path "$Here\p84.done" | Out-Null
exit $er
