#Requires -Version 7
# 436.9 J-P3 edition 5: the stop decision on the report of a record tool whose exit 1 goes on
# (T-JR-12a VBH / VBJ, base-judge-compare; re-audit K-1, erratum 3 3-1, sealed 7bab9217). No dependency
# on the other run step files: common_ed5.ps1 dot-sources it, the unit tests run it alone.
#
# Get-RecordToolStop <report> [-VbjJp3], in this order (erratum 3 3-1):
#   1. -VbjJp3: the VBJ J-P3 read from its judged rows (jp3_outcome) is H-7 -> stop 1
#   2. -VbjJp3: no J-P3 judgement block (J-P3 with runs_judged and status) or 0 judged rows
#      -> not judgeable, stop 2 (a report that ended before the pairs, e.g. a lock window
#      mismatch, has none)
#   3. a setting defect or a not-judgeable reason -> stop 2
#   4. a failure outside the tool's record list (record_failures: the 13.9 indicators of
#      T-JR-12a - new FAULT, first READY, L2 grade, dominated-read reduction; base-judge-compare
#      has none) -> an input defect, stop 2
#   5. otherwise (record failures only, or none) -> go on
# Get-P1CompareStop <report> <exit code> <p1 | p1_content> (erratum 3 3-1, sealed 7bab9217):
#   base-judge-compare in P-1 - an exit other than 0 (an R-2 grade difference is no record
#   failure) stops P-1 with exit 2 on the sha path and on the content path alike; exit 0 then
#   goes through Get-RecordToolStop (a defect / not-judgeable reason still stops 2)
# Get-P5FixedStop <p52.json> (prelaunch audit B-2, step_p5fixed.ps1): the P5-2 fixed record -
#   a problem (a missing key), no rev 6 row or no P4-on rev 6 row stops 2 (never a pass on an
#   empty set); a judged key total > 0 on the P4-on rev 6 rows stops 1 (P5-2 "판정 키 > 0")
# Get-DryCStop <dry_c.json> (prelaunch audit W-3, step1_p1.ps1): the c dry check written with
#   c < 0.5 goes on; c >= 0.5, c missing (no opportunity pair) or another status stops 2 (6.3.10:
#   stop and ask)
# Get-JudgedFailureMarkers / Get-RefusedPreviousStop (prelaunch audit W-1): the judged-failure
#   marker of a VBJ J-P3 H-7 stop ('judged:t12_VBJ_jp3' = 1) and the refusal of a new attempt
#   after such a stop (common_ed5.ps1 Read-PreviousStops)
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

function Get-P1CompareStop([string]$ReportPath, [int]$ExitCode, [string]$MatchItem) {
    if (@('p1', 'p1_content') -notcontains $MatchItem) {
        return @{ code = 3; reason = "P-1 match path '$MatchItem' is neither p1 nor p1_content" }
    }
    if ($ExitCode -ne 0) {
        return @{ code = 2; reason = "base-judge-compare exit $ExitCode on the $MatchItem path (erratum 3 3-1: an R-2 grade difference stops P-1)" }
    }
    return Get-RecordToolStop $ReportPath
}

function Get-GateField($Report, [string]$Name) {
    $Found = $Report.PSObject.Properties[$Name]
    if (-not $Found) { return $null }
    return $Found.Value  # a scalar field (a JSON null arrives as $null, like a missing one)
}

function Get-P5FixedStop([string]$ReportPath) {
    $Report = Read-GateReport $ReportPath
    $Name = Split-Path -Leaf $ReportPath
    if ($null -eq $Report) { return @{ code = 3; reason = "$ReportPath missing" } }
    $Problems = Get-GateList $Report 'problems'
    $Rev6 = Get-GateField $Report 'rev6_rows'
    $P4On = Get-GateField $Report 'p4_on_rev6_rows'
    $Judged = Get-GateField $Report 'judged_key_total'
    if ($null -eq $Problems -or $null -eq $Rev6 -or $null -eq $P4On -or $null -eq $Judged) {
        return @{ code = 3; reason = "$ReportPath lacks problems / rev6_rows / p4_on_rev6_rows / judged_key_total" }
    }
    if ($Problems.Count -gt 0) { return @{ code = 2; reason = "${Name}: $($Problems.Count) problems (a fixed record with a gap)" } }
    if ([int]$Rev6 -le 0 -or [int]$P4On -le 0) {
        return @{ code = 2; reason = "${Name}: no rev 6 / no P4-on rev 6 row (an empty set is no fixed value)" }
    }
    if ([int]$Judged -gt 0) { return @{ code = 1; reason = "${Name}: a J-P3 judged key > 0 on the P4-on rev 6 rows (P5-2)" } }
    return $null
}

function Get-JudgedFailureMarkers($Stop, [switch]$VbjJp3) {
    # prelaunch audit W-1: the codes a judged failure leaves in the step record (the T-JR-12a
    # VBJ J-P3 H-7, exit 1 of Get-RecordToolStop -VbjJp3); none otherwise
    if ($VbjJp3 -and $Stop -and $Stop.code -eq 1) { return @{ 'judged:t12_VBJ_jp3' = 1 } }
    return @{}
}

function Get-RefusedPreviousStop([string]$StopPath, [string[]]$RecordCodeTools) {
    # prelaunch audit W-1: why an earlier stop record refuses a new attempt ($null: it does
    # not) - a judge tool exit 1 outside the record tools, or a judged-failure marker = 1
    $Previous = Read-GateReport $StopPath
    if ($null -eq $Previous) { return $null }
    $Codes = $Previous.PSObject.Properties['codes']
    if (-not $Codes -or $null -eq $Codes.Value) { return $null }
    foreach ($Code in $Codes.Value.PSObject.Properties) {
        $IsTool = $Code.Name -like 'tool:*' -and $RecordCodeTools -notcontains $Code.Name
        $IsJudged = $Code.Name -like 'judged:*'
        if (($IsTool -or $IsJudged) -and $Code.Value -eq 1) { return "an earlier attempt failed ($($Code.Name) = 1)" }
    }
    return $null
}

function Get-DryCStop([string]$ReportPath) {
    $Report = Read-GateReport $ReportPath
    $Name = Split-Path -Leaf $ReportPath
    if ($null -eq $Report) { return @{ code = 3; reason = "$ReportPath missing" } }
    $Status = Get-GateField $Report 'status'
    if ([string]$Status -ne 'written') { return @{ code = 2; reason = "${Name}: status '$Status', written required" } }
    $C = Get-GateField $Report 'c'
    if ($null -eq $C) { return @{ code = 2; reason = "${Name}: no c (no opportunity pair)" } }
    if ([double]$C -ge 0.5) { return @{ code = 2; reason = "${Name}: c >= 0.5 - stop and ask before step (1) (spec v5 6.3.10)" } }
    return $null
}
