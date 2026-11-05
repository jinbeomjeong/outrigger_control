# K1 soil sweep, arms in sequence, E cores 0x00FF0000, 8 workers. Result folder: k1soil\sweep.
$d = "C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\ctrl_k1soil"
$o = "C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\chrono\k1soil\sweep"
New-Item -ItemType Directory -Force $o | Out-Null
foreach ($arm in "A", "B", "Af", "Bf") {
    & C:\ProgramData\miniforge3\Scripts\conda.exe run --no-capture-output -n dynamics-dev python -I -B "$d\sweep_run.py" $arm "$o\$arm.jsonl" --workers 8 *> "$d\sweep_$arm.log"
    "arm $arm rc $LASTEXITCODE $(Get-Date -Format HH:mm:ss)"
}
