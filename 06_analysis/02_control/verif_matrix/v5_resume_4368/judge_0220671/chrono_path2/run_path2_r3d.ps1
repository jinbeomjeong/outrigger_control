# DRAFT - NOT RUN. Path-2 Chrono re-judgement of the 436.8 bundles with the R3d tool (rev22 R22-3 3, 4).
# Replace 0220671 with the 7-digit R3d merge commit and 02206710fe9ea77088d466f8a486afd5e130bceb with its full hash before running; the
# script stops if either placeholder is left. git_at_start = R2 b9f5707 (as R3c).
# Outputs go to a NEW folder judge_0220671\chrono_path2 ; the R3c folder judge_f9bc3c7\chrono_path2 is only read.
# Steps: 0 R3c outputs.sha256 check (file sha and every entry, S-11) -> 1 seal -> 2 synthetic self test -> 3 E-7
# tool run (new folder) -> 4 judge C-1..C-8 with the R3c t45 replay output (not rebuilt, R22-3 2) -> 5 G-S load
# -> 6..8 p2_4368 seal / chrono / oc5k / openloop -> 9 R3c outputs.sha256 check again (S-11) -> 10 K-10 per bundle
# (k10_compare_r3d.py, R22-3 4; missing side = S-15) -> 11 outputs.sha256 of the new folder.
$ErrorActionPreference = 'Continue'
$R3D_SHORT = '0220671'
$R3D_FULL = '02206710fe9ea77088d466f8a486afd5e130bceb'
if ($R3D_SHORT -like '<*' -or $R3D_FULL -like '<*') { Write-Error 'placeholders not replaced'; exit 2 }
$repo = 'C:\workspace\outrigger_control'
$R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$vm = "$repo\06_analysis\02_control\verif_matrix\v5_resume_4368"
$R3C = "$vm\judge_f9bc3c7\chrono_path2"
$R3C_LIST_SHA = 'bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f'   # rev22 R22-3 2
$OUT = "$vm\judge_$R3D_SHORT\chrono_path2"
$LOGS = "$OUT\logs"
$pc = "$vm\path2_chrono"
$t = "$vm\path2\p2_4368.py"
$s9 = "$repo\07_results\S9"
$s8 = "$repo\07_results\S8"
$man = "$vm\chrono_rows_manifest.json"
$k10 = 'C:\workspace\_resume_4368_20261115\p2r3d\k10_compare_r3d.py'
# Synthetic self-test scratch (about 1.5 GB); removed after step 2 so outputs.sha256 does not cover it.
$tmp = "$OUT\synth_tmp"
$conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
$py = @('run', '-n', 'dynamics-dev', 'python', '-I', '-B')
$log = "$OUT\run_path2_r3d.log"
if ($OUT -eq $R3C) { Write-Error 'output folder must not be the R3c folder'; exit 2 }
if (Test-Path $OUT) { Write-Error "output folder exists: $OUT"; exit 2 }
if (-not $PSCommandPath) { Write-Error 'run this as a script file (pwsh -File), not pasted'; exit 2 }
New-Item -ItemType Directory -Force $OUT, $LOGS | Out-Null
# Keep the exact script that ran next to its outputs (hashed in step 11).
Copy-Item -LiteralPath $PSCommandPath "$OUT\run_path2_r3d.ps1"
"script $PSCommandPath sha256 $((Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLower())" |
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

function Check-R3C($label) {
  # rev22 R22-3 2 / 3: the R3c list file sha and every entry; any difference = S-11 (stop)
  $lp = "$R3C\outputs.sha256"
  $bad = @()
  if (-not (Test-Path $lp)) { $bad += 'outputs.sha256 missing' }
  elseif ((Get-FileHash -Algorithm SHA256 $lp).Hash.ToLower() -ne $R3C_LIST_SHA) { $bad += 'outputs.sha256 file sha differs' }
  else {
    foreach ($ln in Get-Content $lp) {
      if (-not $ln.Trim()) { continue }
      $parts = $ln -split '  ', 2
      $f = Join-Path $R3C $parts[1]
      if (-not (Test-Path $f)) { $bad += "missing $($parts[1])" }
      elseif ((Get-FileHash -Algorithm SHA256 $f).Hash.ToLower() -ne $parts[0]) { $bad += "differs $($parts[1])" }
    }
  }
  "[$((Get-Date).ToString('s'))] R3c outputs.sha256 check ($label): $(if ($bad) { 'S-11 ' + ($bad -join '; ') } else { 'all entries match' })" |
    Tee-Object -FilePath $log -Append | Out-Host
  return ($bad.Count -eq 0)
}

"R3d HEAD $(git -C $repo rev-parse HEAD) (expected $R3D_FULL)" | Tee-Object -FilePath $log -Append
if ((git -C $repo rev-parse HEAD).Trim() -ne $R3D_FULL) { 'S-12: checkout is not R3d' | Tee-Object -FilePath $log -Append; exit 2 }
if (-not (Check-R3C 'before')) { exit 2 }

$p = [Diagnostics.Process]::GetCurrentProcess(); $old = $p.ProcessorAffinity
try {
  $p.ProcessorAffinity = [IntPtr]0xFF00
  # 1. seal (path2_chrono, rev16..rev23)
  Run '01_p2_chrono_seal' @("$pc\p2_chrono.py", 'seal') | Out-Null
  # 2. synthetic self test (script, not pytest)
  Run '02_test_p2_synthetic' @("$pc\test_p2_synthetic.py", '--tmp', $tmp) | Out-Null
  Remove-Item -Recurse -Force -LiteralPath $tmp
  "[$((Get-Date).ToString('s'))] removed synthetic scratch $tmp (result in logs\02_test_p2_synthetic.txt)" |
    Tee-Object -FilePath $log -Append | Out-Host
  # 3. E-7 tool run on the C-2 PS-c event row (new folder; compared with the R3c e7 output in step 10 as a record)
  Run '03_p2_e7' @("$pc\p2_e7.py", $repo, $OUT, '--git-at-start', $R2, $psc) | Out-Null
  # 4. judge per bundle; C-5 uses the R3c t45 replay output read-only (rev22 R22-3 2: not rebuilt)
  foreach ($k in $BUNDLES.Keys) {
    $n = $k -replace '-', ''
    $a = @("$pc\p2_chrono.py", 'judge', '--bundle', $k)
    foreach ($bn in $BUNDLES[$k]) { $a += @('--batch', "$s9\$bn\batch.json") }
    $a += @('--git-at-start', $R2, '--out', "$OUT\p2_$n.json")
    if ($k -eq 'C-2') { $a += @('--aux', "e7=$OUT\e7_path2.json") }
    if ($k -eq 'C-5') { $a += @('--aux', "t45=$R3C\t45\t45_path2.json") }
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

# 9. R3c outputs.sha256 again (after the re-judgement), S-11 on any difference
$after = Check-R3C 'after'

# 10. K-10 per bundle (rev22 R22-3 4): p2_C*.json must exist on both sides (else S-15); p2h_* and e7 as records
$cmp = "$OUT\k10"
New-Item -ItemType Directory -Force $cmp | Out-Null
$k10rc = @{}
foreach ($k in $BUNDLES.Keys) {
  $n = $k -replace '-', ''
  $k10rc[$k] = Run "10_k10_$n" @($k10, "$R3C\p2_$n.json", "$OUT\p2_$n.json", '--out', "$cmp\k10_p2_$n.json")
}
foreach ($f in @('e7_path2.json', 'gs_load.json', 'p2h_chrono.json', 'p2h_oc5k_C-8a.json', 'p2h_oc5k_C-8b.json', 'p2h_openloop.json')) {
  Run "10_k10_record_$($f -replace '\.json$', '')" @($k10, "$R3C\$f", "$OUT\$f", '--out', "$cmp\k10_record_$f") | Out-Null
}
$summary = foreach ($k in $BUNDLES.Keys) { "$k=" + @{0 = 'equal'; 1 = 'different (stop and ask)'; 2 = 'missing S-15'}[[int]$k10rc[$k]] }
"[$((Get-Date).ToString('s'))] K-10 per bundle: $($summary -join ', '); R3c list after: $(if ($after) { 'match' } else { 'S-11' })" |
  Tee-Object -FilePath $log -Append

# 11. sha256 of every output of the new folder
Get-ChildItem -Recurse -File $OUT | Where-Object { $_.Name -notin @('run_path2_r3d.log', 'outputs.sha256') } |
  ForEach-Object { "$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower())  $($_.FullName.Substring($OUT.Length + 1))" } |
  Set-Content -Encoding utf8NoBOM "$OUT\outputs.sha256"
Get-Content "$OUT\outputs.sha256"
