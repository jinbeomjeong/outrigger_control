# Spec 427.11 stage 2: the stage 1 runs where P36s / P37t / R4c acted, with each single token.
# Needs the stage 1 outputs (Tag p37c). Selection: p37_stage2_select.py. Same Step format.
# Moved 2026-10-30 from session scratchpad p37\run_p37_stage2.ps1. Only two changes from the original:
# the log goes to -LogDir (default %TEMP%\outrigger_runners) and the repository root is found from this
# file's location (the original used C:\workspace\outrigger_control). Commands and arguments are unchanged.
param([string]$BaseTag = 'p37c', [string]$Tag = 'p37s2', [string]$Mask = '0xFFFF', [int]$Workers = 16,
      [string]$Tokens = 'P36sa,P37t,R4c20,R4c30',
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
$sel = '04_scripts/03_control/s9/p37_stage2_select.py'
$o = '06_analysis/02_control/s9/rev85'; $r83 = '06_analysis/02_control/s9/rev83'
$s = "$o/${Tag}_select"
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
function Ids([string]$suite) { $f = "${s}_${suite}_ids.txt"; if (Test-Path $f) { (Get-Content $f -Raw).Trim() } else { '' } }
Step 'select' $sel @('--prefix',$s,'--wrapper',"$o/${BaseTag}_harness_cmp.json","$o/${BaseTag}_p0_cmp.json","$o/${BaseTag}_x426b_cmp.json",'--study-a',"$o/${BaseTag}_A_cmp.json",'--r67',"$o/${BaseTag}_r67_main_cmp.json")
$topSel = "${s}_top"
Step 'select_top' $sel @('--prefix',$topSel,'--r67',"$o/${BaseTag}_r67_top_cmp.json")
$cands = $Tokens  # one run file per suite group, all single tokens
foreach ($group in @(@{name='harness'; suites=@('slope','h6'); hook='harness'}, @{name='x426b'; suites=@('x426b'); hook='harness'}, @{name='p0'; suites=@('g6','g8','p3b','v3s'); hook='p0'})) {
    $present = @($group.suites | Where-Object { Ids $_ })
    if (-not $present) { "[skip] $($group.name): no acted ids" | Tee-Object -FilePath $log -Append; continue }
    $ids = ($present | ForEach-Object { Ids $_ }) -join ';'
    Step "w_$($group.name)" $w @('run','--suite',($present -join ','),'--ids',$ids,'--candidates',$cands,'--settle-hook',$group.hook,'--workers',"$Workers",'--affinity',$Mask,'--out',"$o/${Tag}_$($group.name).json")
}
$aFilter = if (Test-Path "${s}_A_filter.txt") { (Get-Content "${s}_A_filter.txt" -Raw).Trim() } else { '' }
$mFilter = if (Test-Path "${s}_r67_filter.txt") { (Get-Content "${s}_r67_filter.txt" -Raw).Trim() } else { '' }
$tFilter = if (Test-Path "${topSel}_r67_filter.txt") { (Get-Content "${topSel}_r67_filter.txt" -Raw).Trim() } else { '' }
foreach ($token in $Tokens.Split(',')) {
    if ($aFilter) { ScreenEnv 'R426A' @{ SET = 'all'; AFFINITY = $Mask; CANDIDATE = $token; FILTER = $aFilter }; Step "A_$token" $sa @($repoArg, "$o/${Tag}_A_$token.json", "$Workers") }
    if ($mFilter) { ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; CANDIDATE = $token; FILTER = $mFilter }; Step "r67_main_$token" $r67 @((Get-Location).Path, "$o/${Tag}_r67_main_$token.json", "$Workers") }
    if ($tFilter) { ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; CANDIDATE = $token; FILTER = $tFilter; OFFSETS = '0,0.025,0.05,0.075' }; Step "r67_top_$token" $r67 @((Get-Location).Path, "$o/${Tag}_r67_top_$token.json", "$Workers") }
}
ScreenEnv 'R67' @{}; ScreenEnv 'R426A' @{}
# --- comparisons (baselines: R2DS, stage 1 current runs) ---
if (Test-Path "$o/${Tag}_harness.json") { Step 'cmp_h' $w @('compare','--out',"$o/${Tag}_harness_cmp.json","$o/${Tag}_harness.json","$r83/R2DS_slope.json","$r83/R2DS_h6.json") }
if (Test-Path "$o/${Tag}_p0.json") { Step 'cmp_p0' $w @('compare','--out',"$o/${Tag}_p0_cmp.json","$o/${Tag}_p0.json","$r83/R2DS_g6.json","$r83/R2DS_g8.json","$r83/R2DS_p3b.json","$r83/R2DS_v3s.json") }
if (Test-Path "$o/${Tag}_x426b.json") { Step 'cmp_x' $w @('compare','--out',"$o/${Tag}_x426b_cmp.json","$o/${Tag}_x426b.json","$o/${BaseTag}_x426b.json") }
foreach ($token in $Tokens.Split(',')) {
    if (Test-Path "$o/${Tag}_A_$token.json") { Step "cmp_A_$token" $cmp @("$o/screen_A_current.json","$o/${Tag}_A_$token.json",'--out',"$o/${Tag}_A_${token}_cmp.json") }
    if (Test-Path "$o/${Tag}_r67_main_$token.json") { Step "cmp_r67_main_$token" $cmp @("$o/screen_r67_main_current.json","$o/${Tag}_r67_main_$token.json",'--out',"$o/${Tag}_r67_main_${token}_cmp.json") }
    if (Test-Path "$o/${Tag}_r67_top_$token.json") { Step "cmp_r67_top_$token" $cmp @("$o/screen_r67_top_current.json","$o/${Tag}_r67_top_$token.json",'--out',"$o/${Tag}_r67_top_${token}_cmp.json") }
}
"ALL DONE" | Tee-Object -FilePath $log -Append
