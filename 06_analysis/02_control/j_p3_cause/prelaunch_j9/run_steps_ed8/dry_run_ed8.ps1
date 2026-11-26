#Requires -Version 7
# Dry run of the edition 8 run steps (no simulation, no tool, nothing in the main checkout): every
# step in the run order with ED8_DRY_RUN_ROOT=DRY_ROOT; Start-Run / Start-Ed8CondaRun /
# Invoke-Tool record their commands, the step records go to DRY_ROOT\j9_runs\RUN8\, all commands
# into DRY_ROOT\commands_ed8.json. The S8-C document and the two P-pred decisions of T8 are
# stand-ins written here. Step 8 with another S8-C sha256 must stop 2 (then attempt 2 runs);
# last, the census step again (done already) must stop 2. Exit 0 when every step ended with 0 and the
# refusals with 2, else the first unexpected code (or 3).
param([Parameter(Mandatory)][string]$DryRoot, [Parameter(Mandatory)][string]$RunCommit,
    [Parameter(Mandatory)][string]$Worktree, [string]$MaskHex = '0x0FFFFFFF', [int]$Workers = 20)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $DryRoot) { Write-Host "STOP: $DryRoot exists"; exit 3 }
New-Item -ItemType Directory -Path $DryRoot | Out-Null
[ordered]@{ rule = 'dry run'; run_commit = $RunCommit; worktree = $Worktree } |
    ConvertTo-Json | Set-Content -LiteralPath "$DryRoot\ed8_run_config.json" -Encoding utf8NoBOM

function Write-DryFile([string]$Name, $Value) {
    # a stand-in file of T8 or the seal; returns its path and sha256
    $Path = "$DryRoot\$Name"
    $Value | ConvertTo-Json | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
    return @($Path, (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLower())
}
$NeedsB4 = Write-DryFile 'decision_needs_b4.json' ([ordered]@{ status = 'needs_b4'; blocks = @(); dry_run = $true })
$Decided = Write-DryFile 'decision_decided.json' ([ordered]@{ status = 'decided'; blocks = @('b1', 'b2', 'b4'); dry_run = $true })
$Seal = Write-DryFile 's8c_dry.json' ([ordered]@{ rule = 'S8-C stand-in'; dry_run = $true })
$S8c = @('-S8cRules', $Seal[0], '-S8cSha256', $Seal[1])
$Placement = @('-MaskHex', $MaskHex, '-Workers', "$Workers")
$Pwsh = (Get-Process -Id $PID).Path
$Steps = @(
    @('step4_impl_ed8.ps1', '-Part', 'scope'), @('step_l1ref_ed8.ps1'),
    (@('step4_impl_ed8.ps1', '-Part', 'p80') + $Placement),
    (@('step4_impl_ed8.ps1', '-Part', 'p816') + $Placement),
    (@('step4_impl_ed8.ps1', '-Part', 'p85') + $Placement),
    (@('step4_impl_ed8.ps1', '-Part', 'p88') + $Placement),
    (@('step4_impl_ed8.ps1', '-Part', 'p815') + $Placement),
    (@('step4_impl_ed8.ps1', '-Part', 't8') + $Placement),
    (@('step4_impl_ed8.ps1', '-Part', 'cases') + $Placement),
    (@('step5_heldout_v0_ed8.ps1', '-Part', 'v0') + $Placement),
    (@('step5_heldout_v0_ed8.ps1', '-Part', 'aa2') + $Placement),
    (@('step5_heldout_v0_ed8.ps1', '-Part', 'aa3') + $Placement),
    (@('step6_census_ed8.ps1') + $Placement),
    (@('step8_heldout_ed8.ps1') + $Placement + @('-S8cRules', $Seal[0], '-S8cSha256', ('0' * 64))),
    (@('step8_heldout_ed8.ps1', '-Attempt', '2') + $Placement + $S8c),
    (@('step9_dg3_ed8.ps1') + $S8c), (@('step10a_plan_ed8.ps1') + $S8c),
    (@('step10b_vbkn0_ed8.ps1', '-Phase', 'base') + $S8c),
    (@('step10b_vbkn0_ed8.ps1', '-Phase', 'b4', '-Decision', $NeedsB4[0], '-DecisionSha256', $NeedsB4[1]) + $S8c),
    (@('step10c_vbkn_ed8.ps1', '-Decision', $Decided[0], '-DecisionSha256', $Decided[1]) + $S8c))
$Refusals = @(, (@('step6_census_ed8.ps1') + $Placement))
$ExpectStop = @{ 13 = 2 }  # step 8 with another S8-C sha256 refuses (2); attempt 2 then runs
$env:ED8_DRY_RUN_ROOT = $DryRoot
$Codes = [ordered]@{}
$Unexpected = @()
try {
    foreach ($Step in $Steps) {
        $Name = ($Step -join ' ')
        & $Pwsh -NoProfile -File "$PSScriptRoot\$($Step[0])" @($Step | Select-Object -Skip 1) *> "$DryRoot\$($Step[0]).$($Codes.Count).log"
        $Expected = if ($ExpectStop.ContainsKey($Codes.Count)) { $ExpectStop[$Codes.Count] } else { 0 }
        $Codes[$Name] = $LASTEXITCODE
        if ($LASTEXITCODE -ne $Expected) { $Unexpected += $(if ($LASTEXITCODE) { $LASTEXITCODE } else { 3 }); break }
    }
    if (-not $Unexpected.Count) {
        foreach ($Step in $Refusals) {
            $Name = "refusal: $($Step -join ' ')"
            & $Pwsh -NoProfile -File "$PSScriptRoot\$($Step[0])" @($Step | Select-Object -Skip 1) *> "$DryRoot\refusal.$($Codes.Count).log"
            $Codes[$Name] = $LASTEXITCODE
            if ($LASTEXITCODE -ne 2) { $Unexpected += 3 }
        }
    }
} finally { Remove-Item Env:ED8_DRY_RUN_ROOT -ErrorAction SilentlyContinue }
$Records = foreach ($Record in (Get-ChildItem -LiteralPath $DryRoot -Recurse -Filter 'step_record.json')) {
    $Value = Get-Content -Raw -LiteralPath $Record.FullName | ConvertFrom-Json
    [ordered]@{ step = $Value.step; folder = $Value.folder; exit_code = $Value.exit_code; codes = $Value.codes
        commands = $Value.commands }
}
[ordered]@{ run_commit = $RunCommit; worktree = $Worktree; exit_codes = $Codes; steps = @($Records) } |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$DryRoot\commands_ed8.json" -Encoding utf8NoBOM
Write-Host ($Codes | ConvertTo-Json -Compress)
if ($Unexpected.Count) { exit $Unexpected[0] }
exit 0
