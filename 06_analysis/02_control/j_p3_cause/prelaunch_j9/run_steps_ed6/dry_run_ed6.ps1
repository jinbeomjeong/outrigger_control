#Requires -Version 7
# Dry run of the edition 6 run steps (no simulation, no judge, nothing in the main checkout):
# every step in the run order with ED6_DRY_RUN_ROOT=DRY_ROOT; Start-Run / Invoke-Tool record
# their commands, the step records go to DRY_ROOT\j9_runs\RUN8\, and all commands with their
# placeholders filled are collected into DRY_ROOT\commands_ed6.json. Exit 0 when every step
# ended with exit 0, else the first non-zero code.
param([Parameter(Mandatory)][string]$DryRoot, [Parameter(Mandatory)][string]$RunCommit,
    [Parameter(Mandatory)][string]$Worktree, [string]$MaskHex = '0x0FFFFFFF', [int]$Workers = 20)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $DryRoot) { Write-Host "STOP: $DryRoot exists"; exit 3 }
New-Item -ItemType Directory -Path $DryRoot | Out-Null
[ordered]@{ rule = 'dry run'; run_commit = $RunCommit; worktree = $Worktree } |
    ConvertTo-Json | Set-Content -LiteralPath "$DryRoot\ed6_run_config.json" -Encoding utf8NoBOM
$Pwsh = (Get-Process -Id $PID).Path
$Steps = @(
    @('step_l1ref_ed6.ps1'), @('prelaunch_ed6.ps1', '-Part', 'list'),
    @('step5_impl_ed6.ps1', '-Part', 'v0d0', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step5_impl_ed6.ps1', '-Part', 'p51', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step5_impl_ed6.ps1', '-Part', 't8', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step5_impl_ed6.ps1', '-Part', 'cases', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step5_impl_ed6.ps1', '-Part', 'probe', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step6_confirm_ed6.ps1', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step7_j9main_ed6.ps1', '-MaskHex', $MaskHex, '-Workers', "$Workers"),
    @('step8a_dg3_ed6.ps1'), @('step8b_vbkl0_ed6.ps1', '-Phase', 'base'), @('step8c_decide_ed6.ps1'),
    @('step8b_vbkl0_ed6.ps1', '-Phase', 'b4'), @('step8c_decide_ed6.ps1', '-WithB4'), @('step8d_vbkl_ed6.ps1'))
$env:ED6_DRY_RUN_ROOT = $DryRoot
$Codes = [ordered]@{}
try {
    foreach ($Step in $Steps) {
        $Name = ($Step -join ' ')
        & $Pwsh -NoProfile -File "$PSScriptRoot\$($Step[0])" @($Step | Select-Object -Skip 1) *> "$DryRoot\$($Step[0]).$($Codes.Count).log"
        $Codes[$Name] = $LASTEXITCODE
        if ($LASTEXITCODE -ne 0) { break }
    }
} finally { Remove-Item Env:ED6_DRY_RUN_ROOT -ErrorAction SilentlyContinue }
$Records = foreach ($Record in (Get-ChildItem -LiteralPath $DryRoot -Recurse -Filter 'step_record.json')) {
    $Value = Get-Content -Raw -LiteralPath $Record.FullName | ConvertFrom-Json
    [ordered]@{ step = $Value.step; folder = $Value.folder; codes = $Value.codes; commands = $Value.commands }
}
[ordered]@{ run_commit = $RunCommit; worktree = $Worktree; exit_codes = $Codes; steps = @($Records) } |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$DryRoot\commands_ed6.json" -Encoding utf8NoBOM
$Failed = @($Codes.Values | Where-Object { $_ -ne 0 })
Write-Host ($Codes | ConvertTo-Json -Compress)
if ($Failed.Count) { exit $Failed[0] }
exit 0
