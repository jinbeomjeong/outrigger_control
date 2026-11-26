#Requires -Version 7
# The start checks of the edition 8 run steps without a step (writes nothing): the config file,
# the run commit C8 as HEAD of a clean run worktree, its parent (the implementation commit) and
# the P8-10 scope, the 03_src tree, the numba cache place, no numba file in the worktree, the
# common.ps1 fixed inputs and every edition 8 input with its sha256.
# Exit 0 (all hold) or the stop code of the first miss (3).
. "$PSScriptRoot\common_ed8.ps1"

Set-Location -LiteralPath $Worktree
$Identity = Get-RunIdentity
$Problem = Get-IdentityProblem $Identity
if ($Problem) { Exit-Ed8 3 $Problem }
$Problem = Get-ScopeProblem
if ($Problem) { Exit-Ed8 3 $Problem }
$Problem = Get-NumbaCacheProblem
if ($Problem) { Exit-Ed8 3 $Problem }
$Numba = Get-WorktreeNumbaFiles
if ($Numba.Count) { Exit-Ed8 3 "numba cache files in the worktree ($($Numba[0]))" }
foreach ($Name in $FixedInputs.Keys) {
    $Path, $Expected = $FixedInputs[$Name]
    if (-not (Test-Path -LiteralPath $Path)) { Exit-Ed8 3 "fixed input $Name missing" }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower() -ne $Expected) { Exit-Ed8 3 "fixed input $Name differs" }
}
foreach ($Name in $Ed8Inputs.Keys) {
    $Problem = Get-InputProblem $Name
    if ($Problem) { Exit-Ed8 3 $Problem }
}
Write-Host "CHECK ok: $RunCommit ($Worktree), parent $ImplCommit, 03_src $ControllerTree"
exit 0
