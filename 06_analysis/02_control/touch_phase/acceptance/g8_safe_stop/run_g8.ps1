# Run one job list on E cores 16..23 with the checkout, one BLAS thread per worker.
param([string]$Jobs, [string]$Out, [int]$Workers = 4)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$scratch = Split-Path -Parent $here
$env:ACC_WT = Join-Path $scratch 'cad_c4g2\wt'
$env:ACC_COMBO = 'off'
$env:R72_PATH = 'per_leg'
$env:MKL_THREADING_LAYER = 'TBB'
$env:MKL_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:NUMBA_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:R79_AFFINITY = '0x00FF0000'
$py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$env:CONDA_PREFIX = 'C:\ProgramData\miniforge3\envs\dynamics-dev'
$env:PATH = "C:\ProgramData\miniforge3\envs\dynamics-dev;C:\ProgramData\miniforge3\envs\dynamics-dev\Library\mingw-w64\bin;C:\ProgramData\miniforge3\envs\dynamics-dev\Library\usr\bin;C:\ProgramData\miniforge3\envs\dynamics-dev\Library\bin;C:\ProgramData\miniforge3\envs\dynamics-dev\Scripts;C:\ProgramData\miniforge3\envs\dynamics-dev\bin;$env:PATH"
$p = Start-Process -FilePath $py -ArgumentList @('-I','-B',"$here\g8trace.py",$env:ACC_WT,$Jobs,$Out,'--workers',"$Workers") -NoNewWindow -PassThru -RedirectStandardOutput "$Out.log" -RedirectStandardError "$Out.err"
$p.ProcessorAffinity = [IntPtr]0x00FF0000
$p.PriorityClass = 'BelowNormal'
$p.WaitForExit()
Write-Output "exit $($p.ExitCode)"
Get-Content "$Out.log" -Tail 25
