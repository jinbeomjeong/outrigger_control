# Path-2 Chrono judgement of the 436.8 R3c bundles (HEAD f9bc3c7, git_at_start = R2 b9f5707). P cores 8-15 (0xFF00).
# Tools: path2_chrono\p2_chrono.py, p2_e7.py, p2_t45.py, test_p2_synthetic.py and path2\p2_4368.py. Not modified.
# All outputs in this folder (judge_f9bc3c7\chrono_path2). Full stdout of each step in logs\<step>.txt.
# Form follows judge_576eb87\chrono_path2\run_path2.ps1 (its outputs are not used). Table = $BUNDLES, loop var = $bn.
# Same step order as the R3b script judge_062e051/chrono_path2/run_path2_r3b.ps1 (R3b run was stopped in step 4; rev21 R21-4).
$ErrorActionPreference = 'Continue'
$repo = 'C:\workspace\outrigger_control'
$R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$vm = "$repo\06_analysis\02_control\verif_matrix\v5_resume_4368"
$OUT = "$vm\judge_f9bc3c7\chrono_path2"
$LOGS = "$OUT\logs"
$pc = "$vm\path2_chrono"
$t = "$vm\path2\p2_4368.py"
$s9 = "$repo\07_results\S9"
$s8 = "$repo\07_results\S8"
$man = "$vm\chrono_rows_manifest.json"
$tmp = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\p2r3c\synth_tmp'
$conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
$py = @('run', '-n', 'dynamics-dev', 'python', '-I', '-B')
$log = "$OUT\run_path2_r3c.log"
New-Item -ItemType Directory -Force $OUT, $LOGS | Out-Null
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

# C-5 L2b row folders (24, batch 113720): runner folder of the last 'batch wall ... -> <folder>' line in
# <batch>\<case>.log + argv --only (path2_chrono README 1, case_log), batch.json cases[] order. All have result.json.
$c5l2b = @(
  "$s8\v5s3_V0_E_G4_Fs4_20261114_113721\E_G4_Fs4",
  "$s8\v5s3_LS1_E_RE1bF_Fs8_20261114_113721\E_RE1bF_Fs8",
  "$s8\v5s3_LS4_E_RE1bF_Fs8_20261114_113721\E_RE1bF_Fs8",
  "$s8\v5s3_VB_E_RE1bF_Fs8_20261114_114534\E_RE1bF_Fs8",
  "$s8\v5s3_VB_E_RE1bF_Fs0_20261114_115500\E_RE1bF_Fs0",
  "$s8\v5s3_VB_G1R_FS24_FL_top_o050_Fs0_20261114_115454\G1R_FS24_FL_top_o050_Fs0",
  "$s8\v5s3_VB_E_G4_Fs4_20261114_120247\E_G4_Fs4",
  "$s8\v5s3_VB_E_G4_Fs4_ph0.05_20261114_120955\E_G4_Fs4_ph0.05",
  "$s8\v5s3_VB_E_G4_Fs8_20261114_121015\E_G4_Fs8",
  "$s8\v5s3_LS1_E_G4_Fs8_20261114_121535\E_G4_Fs8",
  "$s8\v5s3_VB_K8_top_fdown3.5_Fs8_20261114_122308\K8_top_fdown3.5_Fs8",
  "$s8\v5s3_LS4_E_G4_Fs8_20261114_122243\E_G4_Fs8",
  "$s8\v5s3_VB_S_top_fdown3.5_wika_Fs8_20261114_122828\S_top_fdown3.5_wika_Fs8",
  "$s8\v5s3_V0_G1R_FS24_FL_top_o050_Fs0_20261114_123356\G1R_FS24_FL_top_o050_Fs0",
  "$s8\v5s3_VB_K0V_top_fdown3.5_Fs0_20261114_123500\K0V_top_fdown3.5_Fs0",
  "$s8\v5s3_VB_K0_top_fdown3.2_Fs0_20261114_123917\K0_top_fdown3.2_Fs0",
  "$s8\v5s3_LS1_K0V_top_fup3.5_Fs0_20261114_124459\K0V_top_fup3.5_Fs0",
  "$s8\v5s3_VB_K8_top_rpB_Fs8_20261114_124415\K8_top_rpB_Fs8",
  "$s8\v5s3_VB_K0_top_fup3.2_Fs0_20261114_124917\K0_top_fup3.2_Fs0",
  "$s8\v5s3_VB_K0V_top_fup3.5_Fs0_20261114_125334\K0V_top_fup3.5_Fs0",
  "$s8\v5s3_VB_K0V_top_roll5.5_Fs0_20261114_125406\K0V_top_roll5.5_Fs0",
  "$s8\v5s3_LS4_K0V_top_fup3.5_Fs0_20261114_125746\K0V_top_fup3.5_Fs0",
  "$s8\v5s3_VB_K0_top_rpBop_Fs0_20261114_130208\K0_top_rpBop_Fs0",
  "$s8\v5s3_V0_E_G4_Fs4_ph0.05_20261114_130232\E_G4_Fs4_ph0.05"
)

function Run($name, [string[]]$a) {
  $out = & $conda @py @a 2>&1
  $rc = $LASTEXITCODE
  $safe = $name -replace '[^A-Za-z0-9_.-]', '_'
  $out | Set-Content -Encoding utf8NoBOM "$LOGS\$safe.txt"
  $last = ($out | Select-Object -Last 1)
  "[$((Get-Date).ToString('s'))] $name exit=$rc :: $last" | Tee-Object -FilePath $log -Append
}

$p = [Diagnostics.Process]::GetCurrentProcess(); $old = $p.ProcessorAffinity
try {
  $p.ProcessorAffinity = [IntPtr]0xFF00
  "HEAD $(git -C $repo rev-parse HEAD)" | Tee-Object -FilePath $log -Append
  # 1. seal (path2_chrono)
  Run '01_p2_chrono_seal' @("$pc\p2_chrono.py", 'seal')
  # 2. synthetic self test (script, not pytest)
  Run '02_test_p2_synthetic' @("$pc\test_p2_synthetic.py", '--tmp', $tmp)
  # 3. E-7 tool run on the C-2 PS-c event row
  Run '03_p2_e7' @("$pc\p2_e7.py", $repo, $OUT, '--git-at-start', $R2, $psc)
  # 4. T4-0 / T4 / T5 gate + regression + replay
  Run '04_p2_t45' (@("$pc\p2_t45.py", $repo, "$repo\07_results", "$OUT\t45") + $c5l2b)
  # 5. judge per bundle
  foreach ($k in $BUNDLES.Keys) {
    $n = $k -replace '-', ''
    $a = @("$pc\p2_chrono.py", 'judge', '--bundle', $k)
    foreach ($bn in $BUNDLES[$k]) { $a += @('--batch', "$s9\$bn\batch.json") }
    $a += @('--git-at-start', $R2, '--out', "$OUT\p2_$n.json")
    if ($k -eq 'C-2') { $a += @('--aux', "e7=$OUT\e7_path2.json") }
    if ($k -eq 'C-5') { $a += @('--aux', "t45=$OUT\t45\t45_path2.json") }
    Run "05_p2_chrono_judge_$n" $a
  }
  # 6. G-S load
  Run '06_p2_chrono_gs_load' @("$pc\p2_chrono.py", 'gs-load', '--batch', "$s9\$gs\batch.json", '--git-at-start', $R2, '--out', "$OUT\gs_load.json")
  # 7. p2_4368 seal
  Run '07_p2_4368_seal' @($t, '--repo', $repo, '--out', "$OUT\p2h_seal.json", 'seal')
  # 8. p2_4368 chrono, all main batches + OC5PROBE, with counts
  $ba = @()
  foreach ($k in $BUNDLES.Keys) { foreach ($bn in $BUNDLES[$k]) { $ba += @('--batch', "$s9\$bn") } }
  $ba += @('--batch', "$s9\$probe")
  Run '08_p2_4368_chrono' (@($t, '--repo', $repo, '--out', "$OUT\p2h_chrono.json", 'chrono') + $ba + @('--git-at-start', $R2, '--rows-manifest', $man, '--check-counts', '--c2-expected', '6', '--c2-psc', '2'))
  # 9. O-C5 k procedure and open-loop values
  Run '09_p2_4368_oc5k_C-8a' @($t, '--repo', $repo, '--out', "$OUT\p2h_oc5k_C-8a.json", 'oc5k', '--row', 'C-8a', '--probe', "$s9\$probe\OC5P_Kc3_VB_n1_k0p9179\result.json")
  Run '09_p2_4368_oc5k_C-8b' @($t, '--repo', $repo, '--out', "$OUT\p2h_oc5k_C-8b.json", 'oc5k', '--row', 'C-8b', '--probe', "$s9\$probe\OC5P_Kc1_V0_n1_k0p8829\result.json")
  $ol = "$s9\batch_V5-RESUME-K1-C6C7_20261113_215638"
  Run '09_p2_4368_openloop' @($t, '--repo', $repo, '--out', "$OUT\p2h_openloop.json", 'openloop', '--run', "C-6=$ol\P3a_G1_B_VB_prop", '--run', "C-7a=$ol\P3a_G1_B_VB_FB", '--run', "C-7b=$ol\P3a_G1_B_V0_FB")
} finally { $p.ProcessorAffinity = $old }

# 10. sha256 of every output
Get-ChildItem -Recurse -File $OUT | Where-Object { $_.Name -notin @('run_path2_r3c.ps1', 'run_path2_r3c.log', 'outputs.sha256') } |
  ForEach-Object { "$((Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLower())  $($_.FullName.Substring($OUT.Length + 1))" } |
  Set-Content -Encoding utf8NoBOM "$OUT\outputs.sha256"
Get-Content "$OUT\outputs.sha256"
