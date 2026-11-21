# Dot-sources the run-step helpers and calls only the checks (no run, no folder in the repo).
. 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps\common.ps1'
$RunsRoot = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\python-j4a-remedy7\probe_runs'
$StepState.Name = 'probe'
Assert-RunCommit
Assert-FixedInputs
"core 0xFFFF=$(Get-CoreKind '0xFFFF') 0x00FF=$(Get-CoreKind '0x00FF') 0x0FFF0000=$(Get-CoreKind '0x0FFF0000')"
$Merged = @{ R79_V5_SETTING = 'VBH'; R79_ROD_MODEL = $R79RodModel['VBH'] } + $R79Common
"env keys $(($Merged.Keys | Sort-Object) -join ',')"
"checks ok"
