# DRAFT - NOT RUN. Path-2 Chrono re-judgement of the 436.8 bundles with the R3f tool (rev25 R25-3; R3e not run).
# Replace <R3F_SHORT> with the 7-digit R3f merge commit and <R3F_FULL> with its full hash before running; the
# script stops if either placeholder is left. git_at_start = R2 b9f5707 (as R3c / R3d).
# Outputs go to a NEW folder judge_<R3F_SHORT>\chrono_path2 ; the R3c (judge_f9bc3c7) and R3d (judge_0220671) path 2
# folders are only read.
# Exit codes (rev25 R25-3 "실행 스크립트"): 2 = stopped before judging (placeholders, S-12 checkout is not R3f,
# S-11 list or judge-code check, S-15 folder count); 4 = C-1 / C-2 / C-3 bundle or row grade differs from R3d
# (stops at that step); 5 = the R3c / R3d lists differ after the run; 0 = otherwise.
# Steps: 0 R3c and R3d outputs.sha256 checks (file sha and every entry, S-11) + R3d run log sha -> 0b CD-2 (1)
# original judge code = b9f5707 (S-11) -> 1 seal -> 2 synthetic self test -> 3 E-7 tool run (new folder)
# -> 3b original judge (run_S8C.py judge) on the S8 folders of the C-1 / C-2 / C-5 L2b rows into the new folder
# (CD-2 (1)-(3)) -> 4 judge C-1..C-8 (C-1 / C-2 / C-5 with --s8c-dir, C-8 with --r3d-c8; R3c t45 replay output read,
# not rebuilt) -> 5 G-S load -> 6..8 p2_4368 seal / chrono / oc5k / openloop -> 9 R3c and R3d outputs.sha256
# checks again (S-11) -> 10 K-10 per bundle vs R3d (k10_compare_r3f.py: CD-10 run identity keys, output-path elements
# of argument lists and CD-7 reason keys excluded; missing side = S-15) -> 10b C-1..C-3 grade change check (exit 4)
# -> 11 outputs.sha256 of the new folder -> exit 5 if the after-run list check failed.
$ErrorActionPreference = 'Continue'
$R3F_SHORT = '8a0c843'
$R3F_FULL = '8a0c8432d23c9db0916bf6f9cb9139466bd32551'
if ($R3F_SHORT -like '<*' -or $R3F_FULL -like '<*') { Write-Error 'placeholders not replaced'; exit 2 }
$repo = 'C:\workspace\outrigger_control'
$R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$vm = "$repo\06_analysis\02_control\verif_matrix\v5_resume_4368"
$R3C = "$vm\judge_f9bc3c7\chrono_path2"
$R3C_LIST_SHA = 'bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f'   # rev22 R22-3 2 / rev24 R24-3
$R3D = "$vm\judge_0220671\chrono_path2"
$R3D_LIST_SHA = '096346c740c171bc10660dd8745587f99794ca39f4d036a15b996fa7775860bb'   # rev24 R24-3 (57 lines)
$R3D_LIST_LINES = 57
$OUT = "$vm\judge_$R3F_SHORT\chrono_path2"
$LOGS = "$OUT\logs"
$S8C = "$OUT\s8c"                                   # CD-2 (2): the path 2 original-judge outputs
$pc = "$vm\path2_chrono"
$t = "$vm\path2\p2_4368.py"
$s9 = "$repo\07_results\S9"
$s8 = "$repo\07_results\S8"
$man = "$vm\chrono_rows_manifest.json"
$k10 = Join-Path $PSScriptRoot 'k10_compare_r3f.py'
# Synthetic self-test scratch (about 1.5 GB); removed after step 2 so outputs.sha256 does not cover it.
$tmp = "$OUT\synth_tmp"
$conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
$py = @('run', '-n', 'dynamics-dev', 'python', '-I', '-B')
$chrono_py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'   # original judge env (run_S8C.py)
$JUDGE_CODE = @('03_src', '04_scripts/02_chrono/run_S8C.py', '04_scripts/02_chrono/run_S6C.py')   # CD-2 (1)
$log = "$OUT\run_path2_r3f.log"
if ($OUT -eq $R3C -or $OUT -eq $R3D) { Write-Error 'output folder must not be the R3c / R3d folder'; exit 2 }
if (Test-Path $OUT) { Write-Error "output folder exists: $OUT"; exit 2 }
if (-not $PSCommandPath) { Write-Error 'run this as a script file (pwsh -File), not pasted'; exit 2 }
New-Item -ItemType Directory -Force $OUT, $LOGS, $S8C | Out-Null
# Keep the exact script that ran next to its outputs (hashed in step 11).
Copy-Item -LiteralPath $PSCommandPath "$OUT\run_path2_r3f.ps1"
"script $PSCommandPath sha256 $((Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLower())" |
  Tee-Object -FilePath $log -Append | Out-Host
"k10 comparator $k10 sha256 $((Get-FileHash -Algorithm SHA256 -LiteralPath $k10).Hash.ToLower())" |
  Tee-Object -FilePath $log -Append | Out-Host
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force $tmp | Out-Null

$BUNDLES = [ordered]@{
  'C-1'   = @('batch_V5-RESUME-K1-C1_20261114_110925')
  'C-2'   = @('batch_V5-RESUME-K1-C2_20261114_222633', 'batch_V5-RESUME-K1-C2_20261114_230123')
  'C-3'   = @('batch_V5-RESUME-K1-C3_20261114_010541')
  'C-4'   = @('batch_V5-RESUME-K1-C4_20261113_222912')
  'C-5'   = @('batch_V5-RESUME-K1-C5_20261114_032426', 'batch_V5-RESUME-K1-C5_20261114_113720', 'batch_V5-RESUME-K1-C5_20261114_131025')
  'C-6C7' = @('batch_V5-RESUME-K1-C6C7_20261113_215638')
  'C-8'   = @('batch_V5-RESUME-K1-OC5_20261114_210626')
}
$CD2_BUNDLES = @('C-1', 'C-2', 'C-5')
$CD2_L2B_ROWS = 32                                  # C-1 6 + C-2 2 + C-5 24 L2b rows (R3d outputs)
$probe = 'batch_V5-RESUME-K1-OC5PROBE_20261113_215123'
$gs = 'batch_V5-RESUME-K1-GS_20261113_194755'
$psc = "$s9\batch_V5-RESUME-K1-C2_20261114_230123\D1PSC_J1_B_top_Fs4_FL_cslow"

function Run($name, [string[]]$a) {
  $out = & $conda @py @a 2>&1
  $rc = $LASTEXITCODE
  $safe = $name -replace '[^A-Za-z0-9_.-]', '_'
  $out | Set-Content -Encoding utf8NoBOM "$LOGS\$safe.txt"
  $last = ($out | Select-Object -Last 1)
  # Out-Host: without it the Tee output joins the function's return value (@(string, int)).
  "[$((Get-Date).ToString('s'))] $name exit=$rc :: $last" | Tee-Object -FilePath $log -Append | Out-Host
  return $rc
}

function Run-Judge($name, [string[]]$a) {
  # CD-2: the original judge in its own env (Chrono-dev), cwd = repo; same logging as Run
  Push-Location $repo
  try { $out = & $chrono_py -I -B @a 2>&1; $rc = $LASTEXITCODE } finally { Pop-Location }
  $safe = $name -replace '[^A-Za-z0-9_.-]', '_'
  $out | Set-Content -Encoding utf8NoBOM "$LOGS\$safe.txt"
  $last = ($out | Select-Object -Last 1)
  "[$((Get-Date).ToString('s'))] $name exit=$rc :: $last" | Tee-Object -FilePath $log -Append | Out-Host
  return $rc
}

function Check-List($label, $dir, $want, $lines) {
  # rev24 R24-3: the R3c / R3d list file sha and every entry; any difference = S-11 (stop)
  $lp = "$dir\outputs.sha256"
  $bad = @()
  if (-not (Test-Path $lp)) { $bad += 'outputs.sha256 missing' }
  elseif ((Get-FileHash -Algorithm SHA256 $lp).Hash.ToLower() -ne $want) { $bad += 'outputs.sha256 file sha differs' }
  else {
    $entries = @(Get-Content $lp | Where-Object { $_.Trim() })
    if ($lines -and $entries.Count -ne $lines) { $bad += "entries $($entries.Count) != $lines" }
    foreach ($ln in $entries) {
      $parts = $ln -split '  ', 2
      $f = Join-Path $dir $parts[1]
      if (-not (Test-Path $f)) { $bad += "missing $($parts[1])" }
      elseif ((Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() -ne $parts[0]) { $bad += "differs $($parts[1])" }
    }
  }
  "[$((Get-Date).ToString('s'))] $label outputs.sha256 check: $(if ($bad) { 'S-11 ' + ($bad -join '; ') } else { 'all entries match' })" |
    Tee-Object -FilePath $log -Append | Out-Host
  return ($bad.Count -eq 0)
}

function Check-Reused($when) {
  $okc = Check-List "R3c ($when)" $R3C $R3C_LIST_SHA 0
  $okd = Check-List "R3d ($when)" $R3D $R3D_LIST_SHA $R3D_LIST_LINES
  $rl = "$R3D\run_path2_r3d.log"
  "[$((Get-Date).ToString('s'))] R3d run log (outside the list) sha256 ($when): $(if (Test-Path $rl) { (Get-FileHash -Algorithm SHA256 $rl).Hash.ToLower() } else { 'missing' })" |
    Tee-Object -FilePath $log -Append | Out-Host
  return ($okc -and $okd)
}

function Get-GradeDiff($before, $after) {
  # rev25 R25-3 실행 스크립트 (2): C-1 / C-2 / C-3 bundle status and row status differences (one string each)
  $out = @()
  foreach ($k in @('C-1', 'C-2', 'C-3')) {
    $n = $k -replace '-', ''
    $pd, $pf = "$before\p2_$n.json", "$after\p2_$n.json"
    if (-not (Test-Path $pd) -or -not (Test-Path $pf)) { $out += "${k}: bundle output missing"; continue }
    $d0 = Get-Content -Raw $pd | ConvertFrom-Json
    $d1 = Get-Content -Raw $pf | ConvertFrom-Json
    if ($d0.bundle_result.status -ne $d1.bundle_result.status) {
      $out += "${k}: bundle $($d0.bundle_result.status) -> $($d1.bundle_result.status)"
    }
    $r0 = @{}; foreach ($r in $d0.rows) { $r0[$r.case] = $r.status }
    $r1 = @{}; foreach ($r in $d1.rows) { $r1[$r.case] = $r.status }
    foreach ($c in (@($r0.Keys) + @($r1.Keys) | Select-Object -Unique)) {
      if ($r0[$c] -ne $r1[$c]) { $out += "${k} ${c}: $($r0[$c]) -> $($r1[$c])" }
    }
  }
  return $out   # unrolled: the caller collects with @(...) (0 elements when nothing differs)
}

# rev25 R25-3 실행 스크립트 (1): the checkout must be R3f (full hash), else S-12
"R3f HEAD $(git -C $repo rev-parse HEAD) (expected $R3F_FULL)" | Tee-Object -FilePath $log -Append
if ((git -C $repo rev-parse HEAD).Trim() -ne $R3F_FULL) { 'S-12: checkout is not R3f' | Tee-Object -FilePath $log -Append; exit 2 }
if (-not (Check-Reused 'before')) { exit 2 }

# 0b. CD-2 (1): the original judge code of this checkout = R2 b9f5707 (diff 0, working tree), else S-11; commit and
# judge file sha256 recorded (the bundle outputs carry the same record, `cd2_judge_provenance`).
$jdiff = @(git -C $repo diff --name-only $R2 -- @JUDGE_CODE)
"[$((Get-Date).ToString('s'))] CD-2 (1) judge code diff vs $R2 : $(if ($jdiff.Count) { 'S-11 ' + ($jdiff -join ', ') } else { 'none' }); checkout $(git -C $repo rev-parse HEAD)" |
  Tee-Object -FilePath $log -Append | Out-Host
if ($jdiff.Count) { exit 2 }
foreach ($f in @('03_src/outrigger_sim/verify/s8_control.py', '03_src/outrigger_sim/verify/s6_control.py',
                 '03_src/outrigger_sim/verify/s6_bundle_c.py', '04_scripts/02_chrono/run_S8C.py', '04_scripts/02_chrono/run_S6C.py')) {
  "  judge file $f sha256 $((Get-FileHash -Algorithm SHA256 (Join-Path $repo $f)).Hash.ToLower())" | Tee-Object -FilePath $log -Append | Out-Host
}
# The S8 folders of the L2b rows (read from the R3d outputs, checked by the list above): one judge run per folder.
$s8dirs = @()
foreach ($k in $CD2_BUNDLES) {
  $n = $k -replace '-', ''
  $doc = Get-Content -Raw "$R3D\p2_$n.json" | ConvertFrom-Json
  $s8dirs += @($doc.rows | Where-Object { $_.engine -eq 'l2b' } | ForEach-Object { Split-Path -Parent $_.folder })
}
$s8dirs = @($s8dirs | Select-Object -Unique)
"[$((Get-Date).ToString('s'))] CD-2 L2b S8 folders: $($s8dirs.Count) (expected $CD2_L2B_ROWS)" | Tee-Object -FilePath $log -Append | Out-Host
if ($s8dirs.Count -ne $CD2_L2B_ROWS) { 'S-15: L2b S8 folder count differs' | Tee-Object -FilePath $log -Append; exit 2 }

$p = [Diagnostics.Process]::GetCurrentProcess(); $old = $p.ProcessorAffinity
try {
  $p.ProcessorAffinity = [IntPtr]0xFF00
  # 1. seal (path2_chrono, rev16..rev25)
  Run '01_p2_chrono_seal' @("$pc\p2_chrono.py", 'seal') | Out-Null
  # 2. synthetic self test (script, not pytest)
  Run '02_test_p2_synthetic' @("$pc\test_p2_synthetic.py", '--tmp', $tmp) | Out-Null
  Remove-Item -Recurse -Force -LiteralPath $tmp
  "[$((Get-Date).ToString('s'))] removed synthetic scratch $tmp (result in logs\02_test_p2_synthetic.txt)" |
    Tee-Object -FilePath $log -Append | Out-Host
  # 3. E-7 tool run on the C-2 PS-c event row (new folder; compared with the R3d e7 output in step 10 as a record)
  Run '03_p2_e7' @("$pc\p2_e7.py", $repo, $OUT, '--git-at-start', $R2, $psc) | Out-Null
  # 3b. CD-2 (2): original judge (verify_S8C) per S8 folder into this run's folder only; its summary is not a grade (CD-2 (3))
  foreach ($d in $s8dirs) {
    $leaf = Split-Path -Leaf $d
    New-Item -ItemType Directory -Force "$S8C\$leaf" | Out-Null
    Run-Judge "03b_verify_S8C_$leaf" @("$repo\04_scripts\02_chrono\run_S8C.py", 'judge', '--batch', $d, '--out', "$S8C\$leaf\verify_S8C.json") | Out-Null
  }
  # 4. judge per bundle; C-5 uses the R3c t45 replay output read-only (rev24 R24-3 / rev25 R25-3 reuse: not rebuilt)
  foreach ($k in $BUNDLES.Keys) {
    $n = $k -replace '-', ''
    $a = @("$pc\p2_chrono.py", 'judge', '--bundle', $k)
    foreach ($bn in $BUNDLES[$k]) { $a += @('--batch', "$s9\$bn\batch.json") }
    $a += @('--git-at-start', $R2, '--out', "$OUT\p2_$n.json")
    if ($k -eq 'C-2') { $a += @('--aux', "e7=$OUT\e7_path2.json") }
    if ($k -eq 'C-5') { $a += @('--aux', "t45=$R3C\t45\t45_path2.json") }
    if ($CD2_BUNDLES -contains $k) { $a += @('--s8c-dir', $S8C) }
    if ($k -eq 'C-8') { $a += @('--r3d-c8', "$R3D\p2_C8.json") }
    Run "04_p2_chrono_judge_$n" $a | Out-Null
  }
  # 5. G-S load
  Run '05_p2_chrono_gs_load' @("$pc\p2_chrono.py", 'gs-load', '--batch', "$s9\$gs\batch.json", '--git-at-start', $R2, '--out', "$OUT\gs_load.json") | Out-Null
  # 6. p2_4368 seal
  Run '06_p2_4368_seal' @($t, '--repo', $repo, '--out', "$OUT\p2h_seal.json", 'seal') | Out-Null
  # 7. p2_4368 chrono, all main batches + OC5PROBE, with counts
  $ba = @()
  foreach ($k in $BUNDLES.Keys) { foreach ($bn in $BUNDLES[$k]) { $ba += @('--batch', "$s9\$bn") } }
  $ba += @('--batch', "$s9\$probe")
  Run '07_p2_4368_chrono' (@($t, '--repo', $repo, '--out', "$OUT\p2h_chrono.json", 'chrono') + $ba + @('--git-at-start', $R2, '--rows-manifest', $man, '--check-counts', '--c2-expected', '6', '--c2-psc', '2')) | Out-Null
  # 8. O-C5 k procedure and open-loop values
  Run '08_p2_4368_oc5k_C-8a' @($t, '--repo', $repo, '--out', "$OUT\p2h_oc5k_C-8a.json", 'oc5k', '--row', 'C-8a', '--probe', "$s9\$probe\OC5P_Kc3_VB_n1_k0p9179\result.json") | Out-Null
  Run '08_p2_4368_oc5k_C-8b' @($t, '--repo', $repo, '--out', "$OUT\p2h_oc5k_C-8b.json", 'oc5k', '--row', 'C-8b', '--probe', "$s9\$probe\OC5P_Kc1_V0_n1_k0p8829\result.json") | Out-Null
  $ol = "$s9\batch_V5-RESUME-K1-C6C7_20261113_215638"
  Run '08_p2_4368_openloop' @($t, '--repo', $repo, '--out', "$OUT\p2h_openloop.json", 'openloop', '--run', "C-6=$ol\P3a_G1_B_VB_prop", '--run', "C-7a=$ol\P3a_G1_B_VB_FB", '--run', "C-7b=$ol\P3a_G1_B_V0_FB") | Out-Null
} finally { $p.ProcessorAffinity = $old }

# 9. R3c and R3d outputs.sha256 again (after the re-judgement), S-11 on any difference
$after = Check-Reused 'after'

# 10. K-10 per bundle vs R3d (rev24 R24-3 / rev25 R25-3 재판정 2 / 3): p2_C*.json must exist on both sides (else
# S-15); p2h_* and e7 as records. The comparator drops the output-path elements of argument lists (rev25 (다),
# --out-dir of both runs). Differences are then sorted against the pre-written allowed key list (판정서).
$cmp = "$OUT\k10"
New-Item -ItemType Directory -Force $cmp | Out-Null
$outdirs = @('--out-dir', $R3D, '--out-dir', $OUT)
$k10rc = @{}
foreach ($k in $BUNDLES.Keys) {
  $n = $k -replace '-', ''
  $k10rc[$k] = Run "10_k10_$n" (@($k10, "$R3D\p2_$n.json", "$OUT\p2_$n.json", '--out', "$cmp\k10_p2_$n.json") + $outdirs)
}
foreach ($f in @('e7_path2.json', 'gs_load.json', 'p2h_chrono.json', 'p2h_oc5k_C-8a.json', 'p2h_oc5k_C-8b.json', 'p2h_openloop.json')) {
  Run "10_k10_record_$($f -replace '\.json$', '')" (@($k10, "$R3D\$f", "$OUT\$f", '--out', "$cmp\k10_record_$f") + $outdirs) | Out-Null
}
$summary = foreach ($k in $BUNDLES.Keys) { "$k=" + @{0 = 'equal'; 1 = 'different (sort against the allowed key list)'; 2 = 'missing S-15'}[[int]$k10rc[$k]] }
"[$((Get-Date).ToString('s'))] K-10 per bundle vs R3d: $($summary -join ', '); R3c / R3d lists after: $(if ($after) { 'match' } else { 'S-11' })" |
  Tee-Object -FilePath $log -Append

# 10b. rev25 R25-3 실행 스크립트 (2): C-1 / C-2 / C-3 bundle grade and row grades vs R3d; any difference -> exit 4 here
$gradeDiff = @(Get-GradeDiff $R3D $OUT)
$gradeDiff | Set-Content -Encoding utf8NoBOM "$cmp\grade_change_C1_C3.txt"
"[$((Get-Date).ToString('s'))] C-1..C-3 grade change vs R3d: $($gradeDiff.Count)" | Tee-Object -FilePath $log -Append | Out-Host
if ($gradeDiff.Count) {
  'stop: C-1 / C-2 / C-3 bundle or row grade differs from R3d (rev25 R25-3 재판정): ask before judging' |
    Tee-Object -FilePath $log -Append | Out-Host
  exit 4
}

# 11. sha256 of every output of the new folder (the original-judge outputs under s8c\ included, CD-2 / R24-2 2)
Get-ChildItem -Recurse -File $OUT | Where-Object { $_.Name -notin @('run_path2_r3f.log', 'outputs.sha256') } |
  ForEach-Object { "$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower())  $($_.FullName.Substring($OUT.Length + 1))" } |
  Set-Content -Encoding utf8NoBOM "$OUT\outputs.sha256"
Get-Content "$OUT\outputs.sha256"
# rev25 R25-3 실행 스크립트: a failed after-run list check is reported by the exit code, not only in the log
if (-not $after) { 'S-11: R3c / R3d outputs.sha256 differ after the run' | Tee-Object -FilePath $log -Append | Out-Host; exit 5 }
exit 0
