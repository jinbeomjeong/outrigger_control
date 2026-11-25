#Requires -Version 7
# 436.9 J-P3 edition 7: the core kind of an affinity mask for the cpu-scheduler run records
# (record.py --core P | E | mixed). The shared helper Get-CoreKind of ..\run_steps\common.ps1
# wrote every mask with a P bit as 'P', so a P + E mask was recorded as P (edition 6 separate
# finding); edition 6 keeps its files, the edition 7 steps dot-source this file after
# common.ps1 and its Get-CoreKind replaces that one (PowerShell resolves the name at call time).
# No dependency on the run configuration: a test can dot-source this file alone.

$PCoreMask = 0x0000FFFF    # i7-14700: logical processors 0-15 = 8 P cores x 2 threads
$ECoreMask = 0x0FFF0000    # logical processors 16-27 = 12 E cores
$AllCoreMask = $PCoreMask -bor $ECoreMask

function Get-CoreMaskProblem([string]$MaskHex) {
    # why a mask is not an affinity mask of this machine ($null: it is)
    $Value = 0L
    if (-not [long]::TryParse(($MaskHex -replace '^0[xX]', ''), 'HexNumber', $null, [ref]$Value)) {
        return "mask '$MaskHex' is not a hex number"
    }
    if ($Value -le 0) { return "mask '$MaskHex' selects no processor" }
    if (($Value -band (-bnot [long]$AllCoreMask)) -ne 0) { return "mask '$MaskHex' names a processor above 27" }
    return $null
}

function Get-CoreKind([string]$MaskHex) {
    # 'P' (P cores only), 'E' (E cores only) or 'mixed' (both); a bad mask throws
    $Problem = Get-CoreMaskProblem $MaskHex
    if ($Problem) { throw $Problem }
    $Value = [Convert]::ToInt64($MaskHex, 16)
    $HasP = ($Value -band $PCoreMask) -ne 0
    $HasE = ($Value -band $ECoreMask) -ne 0
    if ($HasP -and $HasE) { return 'mixed' }
    if ($HasP) { return 'P' }
    return 'E'
}
