#Requires -Version 7
# 436.9 J-P3 edition 5: the stop decision on the report of a record tool whose exit 1 goes on
# (T-JR-12a VBH / VBJ, base-judge-compare; re-audit K-1, erratum 3 3-1 draft). No dependency
# on the other run step files: common_ed5.ps1 dot-sources it, the unit tests run it alone.
#
# Get-RecordToolStop <report> [-VbjJp3], in this order (erratum 3 3-1):
#   1. -VbjJp3: the VBJ J-P3 read from its judged rows (jp3_outcome) is H-7 -> stop 1
#   2. -VbjJp3: no J-P3 judgement block (J-P3 with runs_judged and status) or 0 judged rows
#      -> not judgeable, stop 2 (a report that ended before the pairs, e.g. a lock window
#      mismatch, has none)
#   3. a setting defect or a not-judgeable reason -> stop 2
#   4. a failure outside the tool's record list (record_failures: the 13.9 indicators of
#      T-JR-12a - new FAULT, first READY, L2 grade, dominated-read reduction; the grade
#      differences of base-judge-compare) -> an input defect, stop 2
#   5. otherwise (record failures only, or none) -> go on
# Returns $null (go on) or @{ code = <exit>; reason = <text> }; a missing report or list is a
# tool error (3).

function Read-GateReport([string]$ReportPath) {
    if (-not (Test-Path -LiteralPath $ReportPath)) { return $null }
    return Get-Content -Raw -LiteralPath $ReportPath | ConvertFrom-Json
}

function Get-GateList($Report, [string]$Name) {
    $Found = $Report.PSObject.Properties[$Name]
    if (-not $Found) { return $null }
    # the unary comma keeps an empty list a list (a returned @() would arrive as $null)
    return , @($Found.Value | Where-Object { $null -ne $_ })
}

function Test-Jp3Block($Report) {
    $Block = $Report.PSObject.Properties['J-P3']
    if (-not $Block -or $null -eq $Block.Value) { return $false }
    $Judged = $Block.Value.PSObject.Properties['runs_judged']
    $Status = $Block.Value.PSObject.Properties['status']
    return [bool]($Judged -and $Status -and $Status.Value -and [int]$Judged.Value -gt 0)
}

function Get-RecordToolStop([string]$ReportPath, [switch]$VbjJp3) {
    $Report = Read-GateReport $ReportPath
    $Name = Split-Path -Leaf $ReportPath
    if ($null -eq $Report) { return @{ code = 3; reason = "$ReportPath missing" } }
    if ($VbjJp3) {
        $Outcome = $Report.PSObject.Properties['jp3_outcome']
        if ($Outcome -and [string]$Outcome.Value -eq 'H-7') {
            return @{ code = 1; reason = "${Name}: T-JR-12a VBJ J-P3 H-7 (spec v5 6.2: a judgement, stop)" }
        }
        if (-not (Test-Jp3Block $Report)) {
            return @{ code = 2; reason = "${Name}: no VBJ J-P3 judgement (block missing or 0 judged rows)" }
        }
    }
    foreach ($Kind in @('setting_defects', 'not_judgeable')) {
        $Items = Get-GateList $Report $Kind
        if ($null -eq $Items) { return @{ code = 3; reason = "$ReportPath has no $Kind" } }
        if ($Items.Count -gt 0) { return @{ code = 2; reason = "${Name}: $($Items.Count) $Kind" } }
    }
    $Failures = Get-GateList $Report 'failures'
    $Records = Get-GateList $Report 'record_failures'
    if ($null -eq $Failures -or $null -eq $Records) {
        return @{ code = 3; reason = "$ReportPath has no failures / record_failures" }
    }
    $Outside = @($Failures | Where-Object { $Records -notcontains $_ })
    if ($Outside.Count -gt 0) {
        return @{ code = 2; reason = "${Name}: $($Outside.Count) failures outside the record list (an input defect, erratum 3 3-1)" }
    }
    return $null
}
