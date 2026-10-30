# Spec 427.11 stage 1 / 429.5 (1): combination P36s+P37t+R4c30+P38z on the wrapper suites (1,220
# + x426b current 84), study A (16 jobs = 80 branches, current + combination) and r67 (384 =
# main grid 192 + top phase 192, current + combination). Same Step format as run_p36s_reg.ps1.
# Edit $mask / $workers from the compute-scheduler-expert plan before launching.
# Moved 2026-10-30 from session scratchpad p37\run_p37_stage1.ps1. Only two changes from the original:
# the log goes to -LogDir (default %TEMP%\outrigger_runners) and the repository root is found from this
# file's location (the original used C:\workspace\outrigger_control). Commands and arguments are unchanged.
param([string]$Candidate = 'P36sa+P37t+R4c30+P38z', [string]$Tag = 'p37c', [string]$Mask = '0xFFFF',
      [int]$Workers = 16, [switch]$SkipCurrent, [string]$BaseTag = 'p37c',
      [string]$LogDir = (Join-Path $env:TEMP 'outrigger_runners'))
$ErrorActionPreference = 'Continue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$repoArg = $repo -replace '\\', '/'   # the screens received the root with forward slashes
Set-Location $repo
$self = [System.Diagnostics.Process]::GetCurrentProcess(); $self.PriorityClass = 'AboveNormal'
$env:MKL_THREADING_LAYER = 'TBB'; $env:OMP_NUM_THREADS = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
$py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$w = '04_scripts/03_control/s9/s9_slope_fix_candidates.py'
$sa = '04_scripts/03_control/s9/s9_soil_event_screen.py'
$r67 = '04_scripts/03_control/s8/r67_g1_screen.py'
$cmp = '04_scripts/03_control/s9/screen_candidate_compare.py'
$o = '06_analysis/02_control/s9/rev85'; $r83 = '06_analysis/02_control/s9/rev83'
New-Item -ItemType Directory -Force $LogDir | Out-Null
$log = Join-Path $LogDir "${Tag}_reg.log"
function Step($name, [string]$script, [string[]]$a) {
    $t = Get-Date; "[$($t.ToString('HH:mm:ss'))] START $name" | Tee-Object -FilePath $log -Append
    & $py -I $script @a 2>&1 | Select-Object -Last 3 | Tee-Object -FilePath $log -Append
    "[$((Get-Date).ToString('HH:mm:ss'))] END $name rc=$LASTEXITCODE wall=$([int]((Get-Date)-$t).TotalSeconds)s" | Tee-Object -FilePath $log -Append
}
function ScreenEnv([string]$prefix, [hashtable]$vars) {
    foreach ($name in @('CANDIDATE','FILTER','OFFSETS','MODE','SET','AFFINITY')) { Remove-Item "Env:${prefix}_$name" -ErrorAction SilentlyContinue }
    foreach ($key in $vars.Keys) { Set-Item "Env:${prefix}_$key" $vars[$key] }
}
# --- wrapper suites (settle hook as the R2DS references) ---
Step 'harness' $w @('run','--suite','slope,h6','--candidates',$Candidate,'--settle-hook','harness','--workers',"$Workers",'--affinity',$Mask,'--out',"$o/${Tag}_harness.json")
$xCands = if ($SkipCurrent) { $Candidate } else { "current,$Candidate" }
Step 'x426b' $w @('run','--suite','x426b','--candidates',$xCands,'--settle-hook','harness','--workers',"$Workers",'--affinity',$Mask,'--out',"$o/${Tag}_x426b.json")
Step 'p0' $w @('run','--suite','g6,g8,p3b,v3s','--candidates',$Candidate,'--settle-hook','p0','--workers',"$Workers",'--affinity',$Mask,'--out',"$o/${Tag}_p0.json")
# --- study A (16 jobs, 80 branches) ---
if (-not $SkipCurrent) {
    ScreenEnv 'R426A' @{ SET = 'all'; AFFINITY = $Mask }
    Step 'A_current' $sa @($repoArg, "$o/screen_A_current.json", "$Workers")
}
ScreenEnv 'R426A' @{ SET = 'all'; AFFINITY = $Mask; CANDIDATE = $Candidate }
Step 'A_cand' $sa @($repoArg, "$o/${Tag}_A.json", "$Workers")
# --- r67 (main grid 192 + top phase 192) ---
if (-not $SkipCurrent) {
    ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask }
    Step 'r67_main_current' $r67 @((Get-Location).Path, "$o/screen_r67_main_current.json", "$Workers")
    ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; FILTER = 'screen|top|'; OFFSETS = '0,0.025,0.05,0.075' }
    Step 'r67_top_current' $r67 @((Get-Location).Path, "$o/screen_r67_top_current.json", "$Workers")
}
ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; CANDIDATE = $Candidate }
Step 'r67_main_cand' $r67 @((Get-Location).Path, "$o/${Tag}_r67_main.json", "$Workers")
ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; FILTER = 'screen|top|'; OFFSETS = '0,0.025,0.05,0.075'; CANDIDATE = $Candidate }
Step 'r67_top_cand' $r67 @((Get-Location).Path, "$o/${Tag}_r67_top.json", "$Workers")
ScreenEnv 'R67' @{}; ScreenEnv 'R426A' @{}
# --- comparisons ---
Step 'cmp_h' $w @('compare','--out',"$o/${Tag}_harness_cmp.json","$o/${Tag}_harness.json","$r83/R2DS_slope.json","$r83/R2DS_h6.json")
Step 'cmp_p0' $w @('compare','--out',"$o/${Tag}_p0_cmp.json","$o/${Tag}_p0.json","$r83/R2DS_g6.json","$r83/R2DS_g8.json","$r83/R2DS_p3b.json","$r83/R2DS_v3s.json")
$xBase = if ($SkipCurrent) { @("$o/${BaseTag}_x426b.json") } else { @() }
Step 'cmp_x' $w (@('compare','--out',"$o/${Tag}_x426b_cmp.json","$o/${Tag}_x426b.json") + $xBase)
Step 'cmp_A' $cmp @("$o/screen_A_current.json","$o/${Tag}_A.json",'--out',"$o/${Tag}_A_cmp.json")
Step 'cmp_r67_main' $cmp @("$o/screen_r67_main_current.json","$o/${Tag}_r67_main.json",'--out',"$o/${Tag}_r67_main_cmp.json")
Step 'cmp_r67_top' $cmp @("$o/screen_r67_top_current.json","$o/${Tag}_r67_top.json",'--out',"$o/${Tag}_r67_top_cmp.json")
"ALL DONE" | Tee-Object -FilePath $log -Append
