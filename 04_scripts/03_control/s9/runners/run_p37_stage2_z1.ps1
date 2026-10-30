# Spec 429.7 stage 2 (single-token split of the stage 1 combination P36sa+P37t+R4c30+P38z, tag p37c).
# Each token runs only on the stage 1 runs where its part acted:
#   R4c30        <- R4c acted        P37t  <- P37t acted
#   P38z1        <- P38z acted       R4c30+P38z1 <- R4c acted
# Selection: p37_stage2_select.py --parts <part> (wrapper ids, study A / r67 job filters).
# Each token is compared as soon as it ends (wrapper: R2DS references, x426b: stage 1 file with
# current; study A / r67: stage 1 current screens, screen_candidate_compare.py).
# Edit -Mask / -Workers from the compute-scheduler-expert plan. Log: p37\<Tag>_reg.log, last line ALL DONE.
# Moved 2026-10-30 from session scratchpad p37\run_p37_stage2_z1.ps1. Only two changes from the original:
# the log goes to -LogDir (default %TEMP%\outrigger_runners) and the repository root is found from this
# file's location (the original used C:\workspace\outrigger_control). Commands and arguments are unchanged.
param([string]$BaseTag = 'p37c', [string]$Tag = 'p37s2', [string]$Mask = '0xFFFF', [int]$Workers = 12,
      [string]$Tokens = 'R4c30,P37t,P38z1,R4c30+P38z1',
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
New-Item -ItemType Directory -Force $LogDir | Out-Null
$log = Join-Path $LogDir "${Tag}_reg.log"
# Spec 429.7 table: token -> the stage 1 acted part that selects its runs
$partOf = @{ 'R4c30' = 'R4c'; 'P37t' = 'P37t'; 'P38z1' = 'P38z'; 'R4c30+P38z1' = 'R4c'; 'P38z25' = 'P38z'; 'R4c30+P38z25' = 'R4c' }
$groups = @(
    @{ name = 'harness'; suites = @('slope', 'h6'); hook = 'harness'; refs = @("$r83/R2DS_slope.json", "$r83/R2DS_h6.json") },
    @{ name = 'x426b'; suites = @('x426b'); hook = 'harness'; refs = @("$o/${BaseTag}_x426b.json") },
    @{ name = 'p0'; suites = @('g6', 'g8', 'p3b', 'v3s'); hook = 'p0'; refs = @("$r83/R2DS_g6.json", "$r83/R2DS_g8.json", "$r83/R2DS_p3b.json", "$r83/R2DS_v3s.json") }
)
function Step($name, [string]$script, [string[]]$a) {
    $t = Get-Date; "[$($t.ToString('HH:mm:ss'))] START $name" | Tee-Object -FilePath $log -Append
    & $py -I $script @a 2>&1 | Select-Object -Last 3 | Tee-Object -FilePath $log -Append
    "[$((Get-Date).ToString('HH:mm:ss'))] END $name rc=$LASTEXITCODE wall=$([int]((Get-Date)-$t).TotalSeconds)s" | Tee-Object -FilePath $log -Append
}
function ScreenEnv([string]$prefix, [hashtable]$vars) {
    foreach ($name in @('CANDIDATE','FILTER','OFFSETS','MODE','SET','AFFINITY')) { Remove-Item "Env:${prefix}_$name" -ErrorAction SilentlyContinue }
    foreach ($key in $vars.Keys) { Set-Item "Env:${prefix}_$key" $vars[$key] }
}
function ReadSel([string]$path) { if (Test-Path $path) { (Get-Content $path -Raw).Trim() } else { '' } }
$tokenList = @($Tokens.Split(',') | Where-Object { $_ })
foreach ($token in $tokenList) { if (-not $partOf.ContainsKey($token)) { "unknown token $token (spec 429.7 table)" | Tee-Object -FilePath $log -Append; exit 2 } }
# --- selections, one per acted part ---
foreach ($part in @($tokenList | ForEach-Object { $partOf[$_] } | Select-Object -Unique)) {
    $s = "$o/${Tag}_select_$part"
    Step "select_$part" $sel @('--prefix',$s,'--parts',$part,'--wrapper',"$o/${BaseTag}_harness_cmp.json","$o/${BaseTag}_p0_cmp.json","$o/${BaseTag}_x426b_cmp.json",'--study-a',"$o/${BaseTag}_A_cmp.json",'--r67',"$o/${BaseTag}_r67_main_cmp.json")
    Step "select_${part}_top" $sel @('--prefix',"${s}_top",'--parts',$part,'--r67',"$o/${BaseTag}_r67_top_cmp.json")
}
# --- runs and comparisons, token by token ---
foreach ($token in $tokenList) {
    $s = "$o/${Tag}_select_$($partOf[$token])"
    $stem = "${Tag}_$($token.Replace('+', '_'))"   # e.g. p37s2_R4c30_P38z1
    foreach ($group in $groups) {
        $present = @($group.suites | Where-Object { ReadSel "${s}_${_}_ids.txt" })
        if (-not $present) { "[skip] ${token} $($group.name): no acted ids" | Tee-Object -FilePath $log -Append; continue }
        $ids = ($present | ForEach-Object { ReadSel "${s}_${_}_ids.txt" }) -join ';'
        $out = "$o/${stem}_$($group.name).json"
        Step "w_${token}_$($group.name)" $w @('run','--suite',($present -join ','),'--ids',$ids,'--candidates',$token,'--settle-hook',$group.hook,'--workers',"$Workers",'--affinity',$Mask,'--out',$out)
        if (Test-Path $out) { Step "cmp_${token}_$($group.name)" $w (@('compare','--out',"$o/${stem}_$($group.name)_cmp.json",$out) + $group.refs) }
    }
    $aFilter = ReadSel "${s}_A_filter.txt"; $mFilter = ReadSel "${s}_r67_filter.txt"; $tFilter = ReadSel "${s}_top_r67_filter.txt"
    if ($aFilter) {
        ScreenEnv 'R426A' @{ SET = 'all'; AFFINITY = $Mask; CANDIDATE = $token; FILTER = $aFilter }
        Step "A_$token" $sa @($repoArg, "$o/${stem}_A.json", "$Workers")
        if (Test-Path "$o/${stem}_A.json") { Step "cmp_A_$token" $cmp @("$o/screen_A_current.json","$o/${stem}_A.json",'--out',"$o/${stem}_A_cmp.json") }
    } else { "[skip] ${token} A: no acted jobs" | Tee-Object -FilePath $log -Append }
    if ($mFilter) {
        ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; CANDIDATE = $token; FILTER = $mFilter }
        Step "r67_main_$token" $r67 @((Get-Location).Path, "$o/${stem}_r67_main.json", "$Workers")
        if (Test-Path "$o/${stem}_r67_main.json") { Step "cmp_r67_main_$token" $cmp @("$o/screen_r67_main_current.json","$o/${stem}_r67_main.json",'--out',"$o/${stem}_r67_main_cmp.json") }
    } else { "[skip] ${token} r67 main: no acted jobs" | Tee-Object -FilePath $log -Append }
    if ($tFilter) {
        ScreenEnv 'R67' @{ MODE = 'screen'; AFFINITY = $Mask; CANDIDATE = $token; FILTER = $tFilter; OFFSETS = '0,0.025,0.05,0.075' }
        Step "r67_top_$token" $r67 @((Get-Location).Path, "$o/${stem}_r67_top.json", "$Workers")
        if (Test-Path "$o/${stem}_r67_top.json") { Step "cmp_r67_top_$token" $cmp @("$o/screen_r67_top_current.json","$o/${stem}_r67_top.json",'--out',"$o/${stem}_r67_top_cmp.json") }
    } else { "[skip] ${token} r67 top: no acted jobs" | Tee-Object -FilePath $log -Append }
    ScreenEnv 'R67' @{}; ScreenEnv 'R426A' @{}
}
"ALL DONE" | Tee-Object -FilePath $log -Append
