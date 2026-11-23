#Requires -Version 7
# 436.9 J-P3 edition 6: the judged-failure marker of the T-JR-12a VBL bundle (erratum 2 2-4).
# The stop gate itself is Get-RecordToolStop of ..\run_steps_ed5\record_gates_ed5.ps1 (its J-P3
# H-7 read from jp3_outcome stops 1); edition 6 names the marker after its setting,
# 'judged:t12_VBL_jp3' = 1, which Get-RefusedPreviousStop reads like every 'judged:*' marker
# (a new attempt is refused). The edition 5 name 'judged:t12_VBJ_jp3' stays as it was there.
# No dependency on the run configuration: the gate test dot-sources this file alone.

$Ed6Jp3Marker = 'judged:t12_VBL_jp3'

function Get-Ed6JudgedFailureMarkers($Stop, [switch]$Jp3) {
    # the codes a judged failure leaves in the step record ($Stop of Get-RecordToolStop -VbjJp3
    # with code 1 = the J-P3 H-7); none otherwise
    if ($Jp3 -and $Stop -and $Stop.code -eq 1) { return @{ $Ed6Jp3Marker = 1 } }
    return @{}
}
