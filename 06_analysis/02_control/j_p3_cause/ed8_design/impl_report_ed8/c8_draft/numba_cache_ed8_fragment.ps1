# DRAFT (not committed; C8 scope, jp3_remedy_spec_v8_rules.md 11.1): the NUMBA_CACHE_DIR part of
# the edition 8 run steps (common_ed8.ps1). The numba kernels of s9_soil_closed_loop.py use
# cache=True; without NUMBA_CACHE_DIR they write .nbi / .nbc next to the module, i.e. into the
# run worktree (new files after the run commit: the end identity and the mtime check see a
# changed tree). The cache goes to a fixed folder outside the worktree and outside the run
# outputs (j9_runs\<C8>\...), one per run commit, made before the first run and never deleted
# by a step.

$NumbaCacheRoot = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache'
# one folder per run commit: a cache of another commit's kernels is never reused
$NumbaCacheDir = "$NumbaCacheRoot\$RunShort"

function Get-NumbaCacheProblem {
    # The cache folder must lie outside the run worktree and outside the runs root.
    $Cache = [IO.Path]::GetFullPath($NumbaCacheDir).TrimEnd('\') + '\'
    foreach ($Forbidden in @($Worktree, $RunsParent)) {
        $Root = [IO.Path]::GetFullPath($Forbidden).TrimEnd('\') + '\'
        if ($Cache.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) {
            return "NUMBA_CACHE_DIR $Cache lies inside $Root"
        }
    }
    return $null
}

function Get-WorktreeNumbaFiles {
    # .nbi / .nbc files inside the run worktree (expected: none, before and after every step)
    return @(Get-ChildItem -LiteralPath "$Worktree\04_scripts" -Recurse -File -Include '*.nbi', '*.nbc' `
        -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
}

# In Initialize-Ed8Step (before any run):
#   $Problem = Get-NumbaCacheProblem; if ($Problem) { Stop-Step 3 $Problem }
#   New-Item -ItemType Directory -Force -Path $NumbaCacheDir | Out-Null
#   $Before = Get-WorktreeNumbaFiles; if ($Before) { Stop-Step 3 "numba cache files in the worktree: $($Before -join ', ')" }
#   $StepState.Codes['numba_cache_dir'] = $NumbaCacheDir
# In Start-Ed8Run (every process: run_v5, ed8_probe, r79 runners):
#   $Environment['NUMBA_CACHE_DIR'] = $NumbaCacheDir
# In Complete-Step (after the end identity):
#   $After = Get-WorktreeNumbaFiles; if ($After) { Stop-Step 3 "numba cache files appeared in the worktree" }
