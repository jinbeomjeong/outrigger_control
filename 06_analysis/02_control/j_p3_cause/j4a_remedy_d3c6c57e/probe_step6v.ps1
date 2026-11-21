#Requires -Version 7
# Probe of the step6v preconditions only (no run, no judge): run commit, fixed inputs, the
# re-judgement input sha values and the jp3_rejudge_inputs constants, the closure tool.
. 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps\common.ps1'
$Scratch = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\python-j4a-remedy12\probe_runs'
$RunCommit = 'd3c6c57e27f5b5448ecc33708b955773705ab22e'
$RunsRoot = $Scratch
$StepState.Name = 'probe'
$StepState.Folder = "$Scratch\p"
New-Item -ItemType Directory -Force -Path "$Scratch\p\logs", "$Scratch\p\judge" | Out-Null
Set-Location -LiteralPath $Worktree
Assert-RunCommit
Assert-FixedInputs
$StoredDg3Dir = "$CauseDir\j9_runs\78fd5d2d\dg3_a1"
$Expected = [ordered]@{
    DG3_VBJ0_SHA256 = @("$StoredDg3Dir\dg3_VBJ0.json", 'c1201b2d160dc2fee08671cdb285df65fa367e22b2e6af643e87c5216252b9c7')
    DG3_VBJ_SHA256  = @("$StoredDg3Dir\dg3_VBJ.json", '603e4b815d8abc11f09bb85731f9591df5e4c6cc812f2dd9f0e6c7ebae070cd0')
}
foreach ($Name in $Expected.Keys) {
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Expected[$Name][0]).Hash.ToLower()
    "$Name file sha equal: $($Actual -eq $Expected[$Name][1])"
}
$Code = 'import sys; sys.path.insert(0, sys.argv[1]); import jp3_rejudge_inputs as r; ' +
    '[print(n, getattr(r, n)) for n in sys.argv[2:]]'
$Lines = @(& $DevPython -I -B -c $Code "$Worktree\04_scripts\04_hydraulic\coupled" @($Expected.Keys))
foreach ($Line in $Lines) {
    $Name, $Value = $Line -split ' ', 2
    "$Name constant equal: $($Expected[$Name][1] -eq $Value)"
}
"fixed paths: H6 $(Test-Path (Get-FixedPath 'H6_SHA256')), L1 extract $(Test-Path (Get-FixedPath 'STORED_H6_L1_REFERENCE_SHA256'))"
'probe done'
