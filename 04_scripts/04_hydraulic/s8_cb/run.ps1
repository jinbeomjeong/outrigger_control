param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
# Run a script of this folder in hydraulics-dev with Library\bin on PATH (scipy exit 127 trap).
$p = 'C:\ProgramData\miniforge3\envs\hydraulics-dev'
$env:PATH = "$p;$p\Library\mingw-w64\bin;$p\Library\usr\bin;$p\Library\bin;$p\Scripts;" + $env:PATH
$env:MPLBACKEND = 'Agg'
& "$p\python.exe" -I @Rest
exit $LASTEXITCODE
