. 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps\common.ps1'
$RunsRoot = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\python-j4a-remedy11\probe_runs'
$StepState.Name = 'probe'
$StepState.Folder = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\python-j4a-remedy11\probe_runs\p'
Assert-RunCommit
Assert-FixedInputs
function Get-RepoPath([string]$Path) { return $Path }
Assert-SimulationPathsUnchanged
'checks ok, previous ' + (Test-Path $PreviousRunsRoot) + ' ' + $PreviousRunsRoot
$StepState.Codes | ConvertTo-Json -Compress
