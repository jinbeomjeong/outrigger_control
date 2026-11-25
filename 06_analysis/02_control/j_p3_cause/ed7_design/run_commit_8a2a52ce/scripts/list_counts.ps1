#Requires -Version 7
# argparse and job counts of the edition 7 run-step commands (--list: no simulation).
param([Parameter(Mandatory)][string]$Worktree, [Parameter(Mandatory)][string]$OutDir)
$ErrorActionPreference = 'Continue'
$Py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$Coupled = '04_scripts/04_hydraulic/coupled'
$Main = 'C:\workspace\outrigger_control'
$Keys = "$Main\06_analysis\02_control\j_p3_cause\ed7_design\keys_seal_b46bdf8f"
$V0 = "$Main\06_analysis\03_hydraulic\coupled\v5\main.jsonl"
$env:MKL_THREADING_LAYER = 'TBB'; $env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location -LiteralPath $Worktree
$Cases = [ordered]@{
    t8      = @("$Coupled/run_v5.py", 'ed7_t8', '--p3-hash-source', $V0, '--out', "$OutDir\t8.jsonl", '--list')
    cases   = @("$Coupled/run_v5.py", 'ed7_cases', '--out', "$OutDir\cases.jsonl", '--list')
    j9main  = @("$Coupled/run_v5.py", 'ed7_j9_main', '--out', "$OutDir\j9.jsonl", '--list')
    sens    = @("$Coupled/run_v5.py", 'ed7_keys', '--jobs-file', "$Keys\sens_keys_ed7.json", '--out', "$OutDir\sens.jsonl", '--list')
    g1      = @("$Coupled/run_v5.py", 'ed7_keys', '--jobs-file', "$Keys\confirm_g1_grid171.json", '--out', "$OutDir\g1.jsonl", '--list')
    probe   = @("$Coupled/ed7_probe.py", '--out', "$OutDir\probe.jsonl", '--arms', 'a2', '--part', 'all', '--list')
    probe_d = @("$Coupled/ed7_probe.py", '--part', 'd', '--out', "$OutDir\probe_d.jsonl", '--list')
    dg3_help  = @("$Coupled/las_t3_dg3.py", '--help')
    plan_help = @("$Coupled/jp3_12b_plan.py", '--help')
    ident_help = @("$Coupled/jp3_run_identity.py", '--help')
}
foreach ($Name in $Cases.Keys) {
    $Lines = @(& $Py -I -B @($Cases[$Name]) 2>&1)
    $Code = $LASTEXITCODE
    $Lines | Set-Content -LiteralPath "$OutDir\$Name.txt" -Encoding utf8NoBOM
    $Summary = ($Lines | Where-Object { "$_" -match 'runs, |"status"|usage' } | Select-Object -First 2) -join ' | '
    Write-Host ("{0,-10} exit {1}  {2}" -f $Name, $Code, $Summary)
}
