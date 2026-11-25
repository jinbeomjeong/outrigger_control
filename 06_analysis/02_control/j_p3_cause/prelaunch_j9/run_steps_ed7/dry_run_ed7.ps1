#Requires -Version 7
# Dry run of the edition 7 run steps (no simulation, no tool, nothing in the main checkout):
# every step in the run order with ED7_DRY_RUN_ROOT=DRY_ROOT; Start-Run / Invoke-Tool record
# their commands, the step records go to DRY_ROOT\j9_runs\RUN8\, and all commands are collected
# into DRY_ROOT\commands_ed7.json. The two P-pred decisions of the judge commit T are stand-ins
# written here (needs_b4, then decided with b1 / b2 / b4). Last, the refusals: the confirm step
# again (done already) must stop 2. Exit 0 when every step ended with exit 0 and the refusal
# with 2, else the first unexpected code (or 3).
param([Parameter(Mandatory)][string]$DryRoot, [Parameter(Mandatory)][string]$RunCommit,
    [Parameter(Mandatory)][string]$Worktree, [string]$MaskHex = '0x0FFFFFFF', [int]$Workers = 20)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $DryRoot) { Write-Host "STOP: $DryRoot exists"; exit 3 }
New-Item -ItemType Directory -Path $DryRoot | Out-Null
[ordered]@{ rule = 'dry run'; run_commit = $RunCommit; worktree = $Worktree } |
    ConvertTo-Json | Set-Content -LiteralPath "$DryRoot\ed7_run_config.json" -Encoding utf8NoBOM

function Write-DryDecision([string]$Name, [string]$Status, [string[]]$Blocks) {
    # a stand-in for the decision file of T (status, blocks); returns its path and sha256
    $Path = "$DryRoot\$Name"
    [ordered]@{ status = $Status; blocks = $Blocks; dry_run = $true } |
        ConvertTo-Json | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
    return @($Path, (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower())
}
$NeedsB4 = Write-DryDecision 'decision_needs_b4.json' 'needs_b4' @()
$Decided = Write-DryDecision 'decision_decided.json' 'decided' @('b1', 'b2', 'b4')
$Placement = @('-MaskHex', $MaskHex, '-Workers', "$Workers")
$Pwsh = (Get-Process -Id $PID).Path
$Steps = @(
    @('step5_impl_ed7.ps1', '-Part', 'scope'), @('step_l1ref_ed7.ps1'),
    (@('step5_impl_ed7.ps1', '-Part', 't8') + $Placement),
    (@('step5_impl_ed7.ps1', '-Part', 'cases') + $Placement),
    (@('step5_impl_ed7.ps1', '-Part', 'probe') + $Placement),
    (@('step6_confirm_ed7.ps1') + $Placement), (@('step7_j9main_ed7.ps1') + $Placement),
    (@('step8_sens_ed7.ps1') + $Placement), @('step9_dg3_ed7.ps1'), @('step10a_plan_ed7.ps1'),
    @('step10b_vbkm0_ed7.ps1', '-Phase', 'base'),
    @('step10b_vbkm0_ed7.ps1', '-Phase', 'b4', '-Decision', $NeedsB4[0], '-DecisionSha256', $NeedsB4[1]),
    @('step10c_vbkm_ed7.ps1', '-Decision', $Decided[0], '-DecisionSha256', $Decided[1]))
$Refusals = @(, (@('step6_confirm_ed7.ps1') + $Placement))
$env:ED7_DRY_RUN_ROOT = $DryRoot
$Codes = [ordered]@{}
$Unexpected = @()
try {
    foreach ($Step in $Steps) {
        $Name = ($Step -join ' ')
        & $Pwsh -NoProfile -File "$PSScriptRoot\$($Step[0])" @($Step | Select-Object -Skip 1) *> "$DryRoot\$($Step[0]).$($Codes.Count).log"
        $Codes[$Name] = $LASTEXITCODE
        if ($LASTEXITCODE -ne 0) { $Unexpected += $LASTEXITCODE; break }
    }
    if (-not $Unexpected.Count) {
        foreach ($Step in $Refusals) {
            $Name = "refusal: $($Step -join ' ')"
            & $Pwsh -NoProfile -File "$PSScriptRoot\$($Step[0])" @($Step | Select-Object -Skip 1) *> "$DryRoot\refusal.$($Codes.Count).log"
            $Codes[$Name] = $LASTEXITCODE
            if ($LASTEXITCODE -ne 2) { $Unexpected += 3 }
        }
    }
} finally { Remove-Item Env:ED7_DRY_RUN_ROOT -ErrorAction SilentlyContinue }
$Records = foreach ($Record in (Get-ChildItem -LiteralPath $DryRoot -Recurse -Filter 'step_record.json')) {
    $Value = Get-Content -Raw -LiteralPath $Record.FullName | ConvertFrom-Json
    [ordered]@{ step = $Value.step; folder = $Value.folder; exit_code = $Value.exit_code; codes = $Value.codes
        commands = $Value.commands }
}
[ordered]@{ run_commit = $RunCommit; worktree = $Worktree; exit_codes = $Codes; steps = @($Records) } |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$DryRoot\commands_ed7.json" -Encoding utf8NoBOM
Write-Host ($Codes | ConvertTo-Json -Compress)
if ($Unexpected.Count) { exit $Unexpected[0] }
exit 0
