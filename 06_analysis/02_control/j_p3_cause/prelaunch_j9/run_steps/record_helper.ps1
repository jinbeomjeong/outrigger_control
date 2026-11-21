#Requires -Version 7
# Run-record patch for the NEXT edition's run steps (user decision 2026-11-21): the cpu-scheduler
# history line of each run also gets --batch-id (the runs a step starts together, so the speed
# correction counts them as one step) and --est-s (the step's estimate, when it has one).
#
# Not used by the edition 4a steps: common.ps1 is in the 4a fixed list and stays as it is, so
# the 4a outputs keep their commands. A next-edition step dot-sources this file AFTER
# common.ps1; its Write-RunRecords then replaces the common.ps1 one:
#
#   . "$PSScriptRoot\common.ps1"
#   . "$PSScriptRoot\record_helper.ps1"
#   $RunEstimatesS['dg3_VBJ'] = 5400      # optional, per Start-Run label (seconds)
#
# Batch id: "j9-" + the run commit's first 8 characters + "-" + the attempt folder name
# (e.g. j9-d3c6c57e-dg3_vbj_a1).

$RunEstimatesS = @{}
# label -> estimated wall time [s] of that run; a label without an entry gets no --est-s

function Get-RunBatchId {
    # the attempt folder of the running step names the batch (one Wait-Runs = one step)
    return "j9-$RunShort-$(Split-Path -Leaf $StepState.Folder)"
}

function Write-RunRecords([object[]]$Runs) {
    # cpu-scheduler history (record.py --from-sample), one line per run, with the batch id and
    # the estimate of its label (record_helper.ps1, next edition)
    $BatchId = Get-RunBatchId
    foreach ($Run in $Runs) {
        $Sample = "$($StepState.Folder)\logs\$($Run.Label).sample.json"
        if (-not (Test-Path -LiteralPath $Sample)) { Write-Host "no sampler file for $($Run.Label)"; continue }
        $Arguments = @('-I', '-B', "$SchedTools\record.py", '--task-id', "j9-$RunShort-$($Run.Label)",
            '--task-type', $Run.TaskType, '--core', (Get-CoreKind $Run.MaskHex), '--from-sample', $Sample,
            '--mask', $Run.MaskHex, '--workers', "$($Run.Workers)", '--batch-id', $BatchId,
            '--note', "436.9 J4a step $($StepState.Name)")
        if ($RunEstimatesS.ContainsKey($Run.Label)) {
            $Arguments += @('--est-s', "$($RunEstimatesS[$Run.Label])")
        }
        & $DevPython @Arguments |
            Out-File -LiteralPath "$($StepState.Folder)\logs\$($Run.Label).record.json" -Encoding utf8NoBOM
    }
}
