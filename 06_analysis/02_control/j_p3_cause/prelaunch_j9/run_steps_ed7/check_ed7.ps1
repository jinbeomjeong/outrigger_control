#Requires -Version 7
# The start checks of the edition 7 run steps without a step (writes nothing): the config file,
# the run commit as HEAD of a clean run worktree, its parent b46bdf8f and the P7-10 scope, the
# 03_src tree, the common.ps1 fixed inputs and every edition 7 input with its sha256.
# Exit 0 (all hold) or the stop code of the first miss (3).
. "$PSScriptRoot\common_ed7.ps1"

Set-Location -LiteralPath $Worktree
$Identity = Get-RunIdentity
$Problem = Get-IdentityProblem $Identity
if ($Problem) { Exit-Ed7 3 $Problem }
$Problem = Get-ScopeProblem
if ($Problem) { Exit-Ed7 3 $Problem }
foreach ($Name in $FixedInputs.Keys) {
    $Path, $Expected = $FixedInputs[$Name]
    if (-not (Test-Path -LiteralPath $Path)) { Exit-Ed7 3 "fixed input $Name missing" }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower() -ne $Expected) { Exit-Ed7 3 "fixed input $Name differs" }
}
foreach ($Name in $Ed7Inputs.Keys) {
    $Problem = Get-InputProblem $Name
    if ($Problem) { Exit-Ed7 3 $Problem }
}
Write-Host "CHECK ok: $RunCommit ($Worktree), parent $ImplCommit, 03_src $ControllerTree"
exit 0
