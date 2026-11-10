# B1 GC-1..4 lane runner (prerun audit fixes: plan-order argv, rc capture, env cleanup). pwsh -NoProfile -File gc_run_lane.ps1 -Lane 1|2|3 -Batch <abs batch dir>
param([Parameter(Mandatory)][ValidateSet(1,2,3)][int]$Lane,
      [Parameter(Mandatory)][string]$Batch)
$ErrorActionPreference = 'Stop'
$host.UI.RawUI.WindowTitle = "B1-GRIDCONV lane $Lane (E 0x0FFF0000 self_pin, threads 4) - do not close"
$wt = 'C:\workspace\outrigger_control\.claude\worktrees\gc-run-dc2029b'
$log = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\gc_sched\logs'
New-Item -ItemType Directory -Force $log, (Join-Path $Batch 'rowrec') | Out-Null
foreach ($n in 'OUTRIGGER_HULL_HOOK','OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED','OUTRIGGER_HULL_HOOK_DLL','OPENBLAS_NUM_THREADS') { Remove-Item "Env:$n" -ErrorAction SilentlyContinue }
$env:OMP_WAIT_POLICY = 'PASSIVE'
$env:OUTRIGGER_PLACEMENT = 'ecore'
$rows = @{
  'GC1_J2_B_RL_1cm'   = @('RL','0.01','74850','0.97327989,1.0')
  'GC2_J2_B_RL_0p5cm' = @('RL','0.005','74850','0.97327989,1.0')
  'GC3_J2_B_FL_1cm'   = @('FL','0.01','122010','0.98016556,1.0')
  'GC4_J2_B_FL_0p5cm' = @('FL','0.005','122010','0.98016556,1.0')
}
$lanes = @{ 1 = @('GC4_J2_B_FL_0p5cm'); 2 = @('GC2_J2_B_RL_0p5cm'); 3 = @('GC3_J2_B_FL_1cm','GC1_J2_B_RL_1cm') }
$py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
Set-Location $wt
foreach ($c in $lanes[$Lane]) {
  $r = $rows[$c]
  $argv = @('single-pad','--soil','J2','--pad-variant','dwg_rear250','--level','top','--leg',$r[0],'--joint','fixed','--grid',$r[1],'--threads','4','--normal-load',$r[2],'--load-steps',$r[3],'--load-ramp','3','--step-ramp','2','--step-hold','8','--case',$c,'--out-root',$Batch)
  $head0 = (git rev-parse HEAD).Trim(); $dirty0 = (git status --porcelain --untracked-files=no | Out-String).Trim()
  $t0 = Get-Date
  & $py -I -X utf8 -u 04_scripts/02_chrono/run_S9.py @argv *> (Join-Path $log "$c.log")
  $rc = $LASTEXITCODE
  $head1 = (git rev-parse HEAD).Trim()
  $rec = [ordered]@{ case = $c; argv = $argv; rc = $rc; interpreter = $py; interp_flags = @('-I','-X','utf8','-u'); cwd = $wt;
    head_start = $head0; head_end = $head1; tracked_dirty_start = $dirty0; start = $t0.ToString('o'); end = (Get-Date).ToString('o');
    env = [ordered]@{ OMP_WAIT_POLICY = $env:OMP_WAIT_POLICY; OUTRIGGER_PLACEMENT = $env:OUTRIGGER_PLACEMENT; OUTRIGGER_HULL_HOOK = $env:OUTRIGGER_HULL_HOOK } }
  $rec | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $Batch "rowrec\$c.json")
  "{0} exit={1} wall_s={2:N0}" -f $c,$rc,((Get-Date)-$t0).TotalSeconds | Add-Content (Join-Path $log 'lane_summary.txt')
  if ($rc -ne 0) { break }
}
