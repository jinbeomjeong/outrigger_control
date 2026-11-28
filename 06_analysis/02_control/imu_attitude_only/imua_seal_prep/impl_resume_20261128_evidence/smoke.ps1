param(
    [Parameter(Mandatory = $true)][string]$Label,
    [string]$ImuArgs = "",
    [string]$Mask = "0xFF0000",
    [string]$Only = ""
)
# Smoke runs of the U-3 / U-6 screens and run_v5 d1, one key each, outputs in the scratch folder.
$ErrorActionPreference = "Stop"
$Wt = "C:\workspace\outrigger_control\.claude\worktrees\v5-imua"
$Scratch = "C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\c52f3f13-1809-41e7-8ed4-76fbbd933dd2\scratchpad\python-imua"
$Py = "C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
$Ids = Join-Path $Scratch "ids"
$Out = Join-Path $Scratch "smoke_$Label"
New-Item -ItemType Directory -Force $Out | Out-Null
$env:MKL_THREADING_LAYER = "TBB"; $env:MKL_NUM_THREADS = "1"; $env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"; $env:NUMBA_NUM_THREADS = "1"; $env:PYTHONDONTWRITEBYTECODE = "1"
$jobs = @(
    @{ name = "D"; env = @{}; args = "04_scripts/03_control/s9/s9_soil_slope.py --groups H8 --v5-setting VB --ids-from `"$Ids\ids_D.json`" --pad B --workers 1 --affinity $Mask --out `"$Out\u3_D_VB.json`" $ImuArgs" },
    @{ name = "slope"; env = @{}; args = "04_scripts/03_control/s9/s9_slope_fix_candidates.py run --suite slope --settle-hook harness --v5-setting VB --ids-from `"$Ids\ids_slope.json`" --pad B --workers 1 --affinity $Mask --out `"$Out\u3_slope_VB.json`" $ImuArgs" },
    @{ name = "C"; env = @{ R72_SET = "x426"; R72_PATH = "per_leg"; S9_SETTLE_HOOK = "p0"; R72_AFFINITY = $Mask }; args = "04_scripts/03_control/s8/r72_g6_screen.py `"$Wt`" `"$Out\u3_C_VB.json`" 1 --v5-setting VB --ids-from `"$Ids\ids_C.json`" --pad B $ImuArgs" },
    @{ name = "b5"; env = @{ R72_PATH = "per_leg" }; args = "04_scripts/03_control/s9/b5_baseline_compare.py run --cases all --controllers C2,ABL,IND --v5-setting VB --ids-from `"$Ids\ids_b5main.json`" --workers 3 --affinity $Mask --out `"$Out\u6_b5_main_VB.json`" $ImuArgs" },
    @{ name = "b5las"; env = @{ R72_PATH = "per_leg" }; args = "04_scripts/03_control/s9/b5_baseline_compare.py run --cases all --controllers IND_LAS --v5-setting VB --ids-from `"$Ids\ids_b5main.json`" --workers 1 --affinity $Mask --out `"$Out\u6_b5_main_VB_IND_LAS.json`" $ImuArgs" },
    @{ name = "d1"; env = @{}; args = "04_scripts/04_hydraulic/coupled/run_v5.py d1 --settings V0,VB --one-per-setting --workers 2 --mask $Mask --out `"$Out\d1.jsonl`" $ImuArgs" }
)
$procs = @()
foreach ($job in $jobs) {
    if ($Only -and ($Only.Split(",") -notcontains $job.name)) { continue }
    foreach ($key in $job.env.Keys) { Set-Item -Path "env:$key" -Value $job.env[$key] }
    $log = Join-Path $Out "$($job.name).log"
    $p = Start-Process -FilePath $Py -ArgumentList "-I -B $($job.args)" -WorkingDirectory $Wt -NoNewWindow -PassThru -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    foreach ($key in $job.env.Keys) { Remove-Item -Path "env:$key" }
    $procs += [pscustomobject]@{ name = $job.name; proc = $p }
    "started $($job.name) pid $($p.Id)"
}
foreach ($item in $procs) {
    $item.proc.WaitForExit()
    "done $($item.name) exit $($item.proc.ExitCode)"
}
