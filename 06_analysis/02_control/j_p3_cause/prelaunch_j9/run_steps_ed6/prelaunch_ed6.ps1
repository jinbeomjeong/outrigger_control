#Requires -Version 7
# Prelaunch parts of edition 6 (no simulation):
#   -Part list   FIXED_INPUTS_RUN8.SHA256SUMS by jp3_fixed_inputs_list.py --edition 6
#                (erratum 1 1-2 / 1-4): the entries of fixed_inputs_entries_ed6.txt, the X-11
#                selection of ed6_inputs\x11 (seeds 50 .. 53) and its outputs, and by --add the
#                four L1 runs of the done l1ref step. Never overwritten; the main session commits
#                it before step 6.
#   -Part check  the start checks only (config, run commit, clean tree, 03_src, fixed inputs,
#                the X-11 selection sha256): exit 0 or the stop code; writes nothing.
param([Parameter(Mandatory)][ValidateSet('list', 'check')][string]$Part)
. "$PSScriptRoot\common_ed6.ps1"

$StepState.Name = "prelaunch_$Part"
Set-Location -LiteralPath $Worktree
Assert-RunCommit
Assert-ControllerBlobs
Assert-FixedInputs
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $X11Selection).Hash.ToLower() -ne $X11SelectionSha256) {
    Write-Host "STOP: $X11Selection is not the spec 6.4 selection"; exit 2
}
if ($Part -eq 'check') { Write-Host "CHECK ok: $RunCommit ($Worktree)"; exit 0 }

$L1Folder = Get-StepFolder 'l1ref'
$Out = if ($IsEd6Dry) { "$Ed6DryRoot\FIXED_INPUTS_$RunShort.SHA256SUMS" } else { $FixedList }
$Arguments = @('-I', '-B', "$Worktree\$Coupled\jp3_fixed_inputs_list.py", '--edition', '6', '--repo', $MainRoot,
    '--worktree', $Worktree, '--commit', $RunCommit, '--entries', $EntriesFile,
    '--x11-selection', $X11Selection, '--out', $Out)
foreach ($Label in $L1Labels.Keys) { $Arguments += @('--add', "$L1Folder\$Label.json") }
if ($IsEd6Dry) {
    Write-Host "DRY prelaunch list: $DevPython $($Arguments -join ' ')"
    exit 0
}
& $DevPython @Arguments
exit $LASTEXITCODE
