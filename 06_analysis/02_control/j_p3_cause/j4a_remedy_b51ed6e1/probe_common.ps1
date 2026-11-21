# Exercises the new run-step helpers on scratch folders only (no run, nothing in the repo).
param([string]$Case)
. 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps\common.ps1'
$Scratch = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\bd7ff3b9-880c-4e9e-afd1-7024158f16f4\scratchpad\python-j4a-remedy8\probe'
$MainRoot = "$Scratch\repo"
$PrelaunchDir = "$MainRoot\prelaunch"
$RunsRoot = "$MainRoot\runs"
$P1OutputsList = "$PrelaunchDir\P1_OUTPUTS_probe.SHA256SUMS"
$StepState.Name = 'probe'

if ($Case -eq 'codes') {
    "codes 1,2 -> $(Get-StepCode @(1, 2)); 2,3 -> $(Get-StepCode @(2, 3)); 0,0 -> $(Get-StepCode @(0, 0))"
    exit 0
}
if ($Case -eq 'refuse') {
    # an earlier stop with a judge failure refuses; a base_judge_compare 1 alone does not
    $Record = @{ folder = 'a1'; exit_code = 1; reason = 'x'; codes = @{ 'tool:t12_VBH' = 1 } }
    $Record | ConvertTo-Json | Set-Content -LiteralPath "$RunsRoot\dg3.stop" -Encoding utf8NoBOM
    $Record2 = @{ folder = 'a1'; exit_code = 0; reason = 'y'; codes = @{ 'tool:base_judge_compare' = 1 } }
    $Record2 | ConvertTo-Json | Set-Content -LiteralPath "$RunsRoot\p1.stop" -Encoding utf8NoBOM
    Read-PreviousStops 'p1'
    "p1 allowed, previous $($StepState.PreviousStops.Count)"
    $StepState.Name = 'dg3'
    Read-PreviousStops 'dg3'
    'dg3 NOT refused'
    exit 0
}
if ($Case -eq 'p1list') {
    $P1Folder = "$RunsRoot\p1_a1"
    New-Item -ItemType Directory -Force -Path "$P1Folder\judge" | Out-Null
    Set-Content -LiteralPath "$P1Folder\h6_base_judge.json" -Value '{"a": 1}' -Encoding utf8NoBOM
    Set-Content -LiteralPath "$P1Folder\h6_base_judge_L1_reference.json" -Value '{"b": 2}' -Encoding utf8NoBOM
    $J = (Get-FileHash -Algorithm SHA256 "$P1Folder\h6_base_judge.json").Hash.ToLower()
    $L = (Get-FileHash -Algorithm SHA256 "$P1Folder\h6_base_judge_L1_reference.json").Hash.ToLower()
    @{ judge_sha256 = $J; l1_reference_sha256 = $L } | ConvertTo-Json | Set-Content -LiteralPath "$P1Folder\judge\bj.json" -Encoding utf8NoBOM
    Write-P1Outputs $P1Folder
    Get-Content -LiteralPath $P1OutputsList
    & git -C $MainRoot add -- 'prelaunch/P1_OUTPUTS_probe.SHA256SUMS' *> $null
    & git -C $MainRoot commit -q -m probe *> $null
    Assert-P1Outputs $P1Folder
    'p1 list ok'
    Set-Content -LiteralPath "$P1Folder\h6_base_judge.json" -Value '{"a": 9}' -Encoding utf8NoBOM
    Assert-P1Outputs $P1Folder
    'changed file NOT caught'
    exit 0
}
