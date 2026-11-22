#Requires -Version 7
# 436.9 J-P3 edition 5: the stop decisions on the report of a record tool whose exit 1 goes on
# (re-audit K-1, erratum 2 2-10). No dependency on the other run step files: common_ed5.ps1
# dot-sources it, the unit tests run it alone.
#   Get-T12Jp3Stop      T-JR-12a VBJ (spec v5 6.2): its J-P3 is a judgement inside a record
#                       tool - jp3_outcome H-7 stops 1, pass goes on, anything else stops 2
#   Get-RecordReportStop a record tool's exit 1 (13.9 indicators, grade differences) never
#                       hides a setting defect or a not-judgeable reason: either stops 2
# Each returns $null (go on) or @{ code = <exit>; reason = <text> }.

function Read-GateReport([string]$ReportPath) {
    if (-not (Test-Path -LiteralPath $ReportPath)) { return $null }
    return Get-Content -Raw -LiteralPath $ReportPath | ConvertFrom-Json
}

function Get-T12Jp3Stop([string]$ReportPath) {
    $Report = Read-GateReport $ReportPath
    if ($null -eq $Report) { return @{ code = 3; reason = "$ReportPath missing" } }
    $Outcome = $Report.PSObject.Properties['jp3_outcome']
    if (-not $Outcome) { return @{ code = 3; reason = "$ReportPath has no jp3_outcome" } }
    switch ([string]$Outcome.Value) {
        'pass' { return $null }
        'H-7' { return @{ code = 1; reason = 'T-JR-12a VBJ: J-P3 H-7 (spec v5 6.2: a judgement, stop)' } }
        default { return @{ code = 2; reason = "T-JR-12a VBJ: J-P3 $($Outcome.Value) (not judged)" } }
    }
}

function Get-RecordReportStop([string]$ReportPath) {
    $Report = Read-GateReport $ReportPath
    if ($null -eq $Report) { return @{ code = 3; reason = "$ReportPath missing" } }
    foreach ($Kind in @('setting_defects', 'not_judgeable')) {
        $Found = $Report.PSObject.Properties[$Kind]
        if (-not $Found) { return @{ code = 3; reason = "$ReportPath has no $Kind" } }
        $Count = @($Found.Value).Count
        if ($Count -gt 0) {
            return @{ code = 2; reason = "$(Split-Path -Leaf $ReportPath): $Count $Kind (a record's exit 1 hides none, erratum 2 2-10)" }
        }
    }
    return $null
}
