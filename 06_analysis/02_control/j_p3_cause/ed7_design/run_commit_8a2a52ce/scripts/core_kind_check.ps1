#Requires -Version 7
# Checks Get-CoreKind of core_kind_ed7.ps1 (P / E / mixed) and the edition 6 helper for contrast.
param([Parameter(Mandatory)][string]$StepsDir)
. "$StepsDir\core_kind_ed7.ps1"
$Cases = [ordered]@{ '0x000F' = 'P'; '0xFFFF' = 'P'; '0x00FF' = 'P'; '0x0FFF0000' = 'E'; '0x00010000' = 'E'
    '0x0FFFFFFF' = 'mixed'; '0x0001FFFF' = 'mixed'; '0x00018000' = 'mixed'; 'FFFF' = 'P' }
$Failures = 0
foreach ($Mask in $Cases.Keys) {
    $Kind = Get-CoreKind $Mask
    $Ok = $Kind -ceq $Cases[$Mask]
    if (-not $Ok) { $Failures++ }
    Write-Host ("{0,-12} {1,-6} expected {2,-6} {3}" -f $Mask, $Kind, $Cases[$Mask], $(if ($Ok) { 'ok' } else { 'FAIL' }))
}
foreach ($Bad in @('0x0', '0x10000000', 'zz', '')) {
    $Problem = Get-CoreMaskProblem $Bad
    $Threw = $false
    try { Get-CoreKind $Bad | Out-Null } catch { $Threw = $true }
    $Ok = [bool]$Problem -and $Threw
    if (-not $Ok) { $Failures++ }
    Write-Host ("bad {0,-12} problem='{1}' threw={2} {3}" -f $Bad, $Problem, $Threw, $(if ($Ok) { 'ok' } else { 'FAIL' }))
}
# the edition 6 helper (common.ps1) on the mixed mask, for the record
function Get-CoreKindEd6([string]$MaskHex) {
    $Value = [Convert]::ToInt64($MaskHex, 16)
    if (($Value -band 0xFFFF) -eq 0) { return 'E' }
    return 'P'
}
Write-Host "edition 6 helper on 0x0FFFFFFF: $(Get-CoreKindEd6 '0x0FFFFFFF') (edition 7: $(Get-CoreKind '0x0FFFFFFF'))"
exit $Failures
