#Requires -Version 7
# Step (7b) the record bundles T-CK and DROPOUT (spec v5 6.4; erratum 2 2-9.5): after step (7),
# a record (no judgement, not a j9_main precondition). The prelaunch plans of
# prelaunch_ed5.ps1 -Part ckdrop (fixed list entries): per bundle 2 cases (12b cell table ranks
# 0, 1) x 4 fault legs x 2 arms (VBK0, VBK) = 16 lines, one r79 run per (bundle, leg, arm) with
# the bundle's key file and that leg's plan (anchor phase_enter:CHECK, delay_reads 0; T-CK STUCK
# -100 bar, DROPOUT NaN), R79_ROD_MODEL=plant_truth, 1 worker each, all at once on -MaskHex
# (the placement is the main session's). Then jp3_ckdrop_record.py: exit 2 / 3 are written as
# "not computed" (Invoke-RecordTool) and stop nothing.
param([int]$Attempt = 1, [Parameter(Mandatory)][string]$MaskHex)
. "$PSScriptRoot\common_ed5.ps1"

$Folder = Initialize-Ed5Step 'ckdrop' $Attempt @('records')
$Bundles = @('tck', 'dropout')
$Legs = @('FL', 'FR', 'RL', 'RR')
$Arms = @('VBK0', 'VBK')
foreach ($Bundle in $Bundles) {
    $Files = @("$CkdropFolder\${Bundle}_keys.txt") + @($Legs | ForEach-Object { "$CkdropFolder\${Bundle}_${_}_plan.json" })
    foreach ($File in $Files) {
        if (-not (Test-Path -LiteralPath $File)) { Stop-Step 2 "$File missing (prelaunch_ed5.ps1 -Part ckdrop)" }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $File).Hash.ToLower() -ne (Get-ListedSha $File)) {
            Stop-Step 2 "$File is not the fixed list's file"
        }
    }
}

$Runs = @()
$RecordArguments = @("$Coupled/jp3_ckdrop_record.py", '--out', "$Folder\judge\ckdrop_record.json")
foreach ($Bundle in $Bundles) {
    foreach ($Leg in $Legs) {
        foreach ($Arm in $Arms) {
            $Label = "${Bundle}_${Leg}_$Arm"
            $Out = "$Folder\$Label.json"
            $T4h = "$Folder\${Label}_t4h"
            $Runs += Start-Run -Label $Label -MaskHex $MaskHex -WrapOutput $Out `
                -Environment (Get-R79Environment $Arm $T4h "$CkdropFolder\${Bundle}_${Leg}_plan.json") `
                -TaskType 'jp3_ckdrop' -Workers 1 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
                    '--levels', 'L2', '--keys-file', "$CkdropFolder\${Bundle}_keys.txt", '--workers', '1',
                    '--affinity', $MaskHex)
            $RecordArguments += @('--run', "${Bundle}:${Leg}:$Arm=$Out", '--t4h', "${Bundle}:${Leg}:$Arm=$T4h")
        }
    }
}
Wait-Runs $Runs
Invoke-IdentityCheck
Invoke-RecordTool 'ckdrop_record' $RecordArguments | Out-Null

Complete-Step
