# B1 grid convergence GC-1..4 : 3 lanes on E pool (self_pin ecore). Run with: pwsh -NoProfile -File gc_lanes.ps1 -Lane 1|2|3
param([Parameter(Mandatory)][ValidateSet(1,2,3)][int]$Lane,
      [string]$Repo = 'C:\workspace\outrigger_control',
      [string]$LogDir = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\gc_sched\logs')

# Caller fills the run_S9 single-pad arguments (row, dx, output dir, ...). --threads 4 is appended here; do NOT repeat it.
$rowArgs = @{
  'GC-1' = '<FILL: GC-1 RL 0.01 args>'
  'GC-2' = '<FILL: GC-2 RL 0.005 args>'
  'GC-3' = '<FILL: GC-3 FL 0.01 args>'
  'GC-4' = '<FILL: GC-4 FL 0.005 args>'
}
$lanes = @{ 1 = @('GC-4'); 2 = @('GC-2'); 3 = @('GC-3','GC-1') }

$py = 'C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe'
New-Item -ItemType Directory -Force $LogDir | Out-Null
Set-Location $Repo
$env:OMP_WAIT_POLICY = 'PASSIVE'
$env:OUTRIGGER_PLACEMENT = 'ecore'   # place_process: affinity 0x0FFF0000 + EcoQoS off (self_pin)
foreach ($id in $lanes[$Lane]) {
  if ($rowArgs[$id] -like '<FILL*') { throw "$id args not filled" }
  $log = Join-Path $LogDir "$id.log"
  $t0 = Get-Date
  $argv = @('-I','-X','utf8','-u','04_scripts/02_chrono/run_S9.py','single-pad') + ($rowArgs[$id] -split ' (?=(?:[^"]*"[^"]*")*[^"]*$)') + @('--threads','4')
  & $py @argv *> $log
  $rc = $LASTEXITCODE
  "{0} exit={1} wall_s={2:N0}" -f $id,$rc,((Get-Date)-$t0).TotalSeconds | Add-Content (Join-Path $LogDir 'lane_summary.txt')
  if ($rc -ne 0) { break }   # stop this lane on failure
}
