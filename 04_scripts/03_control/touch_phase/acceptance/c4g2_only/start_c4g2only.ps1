# Starts the memory sidecar, then the sequential C4G2-only runner in this window.
$d = "C:\Users\jinbeom\AppData\Local\Temp\claude\C--workspace-outrigger-control\9d4aec18-3b7f-4f45-ae19-6d57127a6418\scratchpad\c4g2only"
$py = "C:\ProgramData\miniforge3\envs\python-dev\python.exe"
Start-Process -FilePath $py -ArgumentList @("-I", "-B", "`"$d\mem_watch.py`"", "`"$d\runner_c4g2only_logs_mem.log`"") -WindowStyle Hidden
pwsh -NoProfile -File "$d\runner_c4g2only.ps1"
exit $LASTEXITCODE
