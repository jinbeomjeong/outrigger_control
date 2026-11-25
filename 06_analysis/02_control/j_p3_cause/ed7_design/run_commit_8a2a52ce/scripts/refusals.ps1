#Requires -Version 7
# Refusal checks of the edition 7 run steps in dry mode (no simulation): each case expects an
# exit code; prints one line per case and exits with the number of unexpected codes.
param([Parameter(Mandatory)][string]$StepsDir, [Parameter(Mandatory)][string]$Root,
    [Parameter(Mandatory)][string]$RunCommit, [Parameter(Mandatory)][string]$Worktree)
$ErrorActionPreference = 'Stop'
$Pwsh = (Get-Process -Id $PID).Path
$Short = $RunCommit.Substring(0, 8)

function New-DryRoot([string]$Name, [string]$Commit = $RunCommit) {
    $Dry = "$Root\$Name"
    New-Item -ItemType Directory -Path $Dry | Out-Null
    [ordered]@{ rule = 'dry run'; run_commit = $Commit; worktree = $Worktree } |
        ConvertTo-Json | Set-Content -LiteralPath "$Dry\ed7_run_config.json" -Encoding utf8NoBOM
    return $Dry
}

function Invoke-DryStep([string]$Dry, [string[]]$Step, [string]$Log) {
    $env:ED7_DRY_RUN_ROOT = $Dry
    try { & $Pwsh -NoProfile -File "$StepsDir\$($Step[0])" @($Step | Select-Object -Skip 1) *> "$Dry\$Log.log" }
    finally { Remove-Item Env:ED7_DRY_RUN_ROOT -ErrorAction SilentlyContinue }
    return $LASTEXITCODE
}

$Unexpected = 0
function Test-Case([string]$Name, [int]$Expected, [int]$Actual, [string]$Log) {
    $Ok = $Expected -eq $Actual
    if (-not $Ok) { $script:Unexpected++ }
    $Reason = if (Test-Path -LiteralPath $Log) { (Get-Content -LiteralPath $Log | Where-Object { $_ -match 'STOP|DONE|CHECK' } | Select-Object -Last 1) } else { '' }
    Write-Host ("{0,-44} expected {1} got {2} {3} | {4}" -f $Name, $Expected, $Actual, $(if ($Ok) { 'ok' } else { 'UNEXPECTED' }), $Reason)
}

# 1. an existing attempt folder refuses (M-7 / 4a-5 5.2)
$Dry = New-DryRoot 'r1_folder'
New-Item -ItemType Directory -Path "$Dry\j9_runs\$Short\impl_scope_a1" | Out-Null
Test-Case 'existing attempt folder' 2 (Invoke-DryStep $Dry @('step5_impl_ed7.ps1', '-Part', 'scope') 'scope') "$Dry\scope.log"

# 2. a step before its requirements stops 3; a bad mask stops 3; the retry in the same folder 2
$Dry = New-DryRoot 'r2_order'
Test-Case 'confirm before impl steps' 3 (Invoke-DryStep $Dry @('step6_confirm_ed7.ps1', '-MaskHex', '0xFF', '-Workers', '8') 'confirm') "$Dry\confirm.log"
Test-Case 'scope' 0 (Invoke-DryStep $Dry @('step5_impl_ed7.ps1', '-Part', 'scope') 'scope') "$Dry\scope.log"
Test-Case 'l1ref' 0 (Invoke-DryStep $Dry @('step_l1ref_ed7.ps1') 'l1ref') "$Dry\l1ref.log"
Test-Case 't8 with a mask above 27' 3 (Invoke-DryStep $Dry @('step5_impl_ed7.ps1', '-Part', 't8', '-MaskHex', '0x10000000', '-Workers', '8') 't8_bad') "$Dry\t8_bad.log"
Test-Case 't8 again into the same attempt folder' 2 (Invoke-DryStep $Dry @('step5_impl_ed7.ps1', '-Part', 't8', '-MaskHex', '0xFF', '-Workers', '8') 't8_again') "$Dry\t8_again.log"
Test-Case 't8 attempt 2 (E-core mask)' 0 (Invoke-DryStep $Dry @('step5_impl_ed7.ps1', '-Part', 't8', '-Attempt', '2', '-MaskHex', '0x0FFF0000', '-Workers', '12') 't8_a2') "$Dry\t8_a2.log"
Test-Case 't8 without -MaskHex' 3 (Invoke-DryStep $Dry @('step5_impl_ed7.ps1', '-Part', 'cases') 'cases_nomask') "$Dry\cases_nomask.log"

# 3. a missing config / a placeholder / another commit
$Dry = "$Root\r3_noconfig"; New-Item -ItemType Directory -Path $Dry | Out-Null
Test-Case 'no config file' 3 (Invoke-DryStep $Dry @('check_ed7.ps1') 'check') "$Dry\check.log"
$Dry = New-DryRoot 'r3_placeholder' '<ED7_RUN_COMMIT>'
Test-Case 'placeholder in config' 3 (Invoke-DryStep $Dry @('check_ed7.ps1') 'check') "$Dry\check.log"
$Dry = New-DryRoot 'r3_parent' 'b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9'
Test-Case 'config names b46bdf8f (not HEAD)' 3 (Invoke-DryStep $Dry @('check_ed7.ps1') 'check') "$Dry\check.log"
$Dry = New-DryRoot 'r3_check'
Test-Case 'check_ed7 on C' 0 (Invoke-DryStep $Dry @('check_ed7.ps1') 'check') "$Dry\check.log"

# 4. 12b decision files: missing arguments, other sha256, other status
$Dry = New-DryRoot 'r4_decision'
foreach ($Step in @(@('step5_impl_ed7.ps1', '-Part', 'scope'), @('step_l1ref_ed7.ps1'),
        @('step5_impl_ed7.ps1', '-Part', 't8', '-MaskHex', '0xFF', '-Workers', '8'),
        @('step5_impl_ed7.ps1', '-Part', 'cases', '-MaskHex', '0xFF', '-Workers', '8'),
        @('step5_impl_ed7.ps1', '-Part', 'probe', '-MaskHex', '0xFF', '-Workers', '8'),
        @('step6_confirm_ed7.ps1', '-MaskHex', '0xFF', '-Workers', '8'),
        @('step7_j9main_ed7.ps1', '-MaskHex', '0xFF', '-Workers', '8'),
        @('step8_sens_ed7.ps1', '-MaskHex', '0xFF', '-Workers', '8'), @('step9_dg3_ed7.ps1'),
        @('step10a_plan_ed7.ps1'), @('step10b_vbkm0_ed7.ps1', '-Phase', 'base'))) {
    $Code = Invoke-DryStep $Dry $Step "seq_$($Step[0])_$($Step[-1])"
    if ($Code -ne 0) { Test-Case "sequence $($Step -join ' ')" 0 $Code "$Dry\seq.log" }
}
[ordered]@{ status = 'decided'; blocks = @('b1', 'b4') } | ConvertTo-Json | Set-Content -LiteralPath "$Dry\decided_b4.json" -Encoding utf8NoBOM
$Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath "$Dry\decided_b4.json").Hash.ToLower()
Test-Case 'b4 without -Decision' 3 (Invoke-DryStep $Dry @('step10b_vbkm0_ed7.ps1', '-Phase', 'b4') 'b4_noarg') "$Dry\b4_noarg.log"
Test-Case 'b4 with a decided decision' 2 (Invoke-DryStep $Dry @('step10b_vbkm0_ed7.ps1', '-Phase', 'b4', '-Attempt', '2', '-Decision', "$Dry\decided_b4.json", '-DecisionSha256', $Sha) 'b4_status') "$Dry\b4_status.log"
Test-Case 'vbkm with another sha256' 2 (Invoke-DryStep $Dry @('step10c_vbkm_ed7.ps1', '-Decision', "$Dry\decided_b4.json", '-DecisionSha256', ('0' * 64)) 'vbkm_sha') "$Dry\vbkm_sha.log"
Test-Case 'vbkm decided b4 without the b4 step' 2 (Invoke-DryStep $Dry @('step10c_vbkm_ed7.ps1', '-Attempt', '2', '-Decision', "$Dry\decided_b4.json", '-DecisionSha256', $Sha) 'vbkm_b4') "$Dry\vbkm_b4.log"
exit $Unexpected
