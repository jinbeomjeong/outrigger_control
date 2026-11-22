#Requires -Version 7
# Step (6b) T-JR-12b, VBK0 only (spec v5 6.3, 8 4.(6) 1 .. 4; user decision 2026-11-21: VBK0
# first). -Phase base runs b1 and b2; -Phase b3 (N top-up) / b4 (witness top-up) run that block
# after the decision of the phase before asked for it (its status needs_b3 / needs_b4). Each
# block: 4 workers on its own P quarter. Then jp3_12b_judge.py decide on every VBK0 block run so
# far (the folders of the done 12b_vbk0_* phases and this one). No VBK file exists yet and none
# is named. Exit: decide's code (0 decided / needs_b3 / needs_b4; 2 aa_floor_stop or not
# judgeable: stop and ask the user, no rerun before the answer, 6.3.8).
param([int]$Attempt = 1, [Parameter(Mandatory)][ValidateSet('base', 'b3', 'b4')][string]$Phase)
. "$PSScriptRoot\common_ed5.ps1"

$PhaseBlocks = [ordered]@{ base = @('b1', 'b2'); b3 = @('b3'); b4 = @('b4') }
$Earlier = @(if ($Phase -ne 'base') { '12b_vbk0_base' })
$Folder = Initialize-Ed5Step "12b_vbk0_$Phase" $Attempt (@('dry', 'l1ref') + $Earlier)  # erratum 2 2-1: L1 first
$EarlierFolders = @($Earlier | ForEach-Object { Get-StepFolder $_ })
if ($Phase -eq 'b4' -and (Test-Path -LiteralPath "$RunsRoot\12b_vbk0_b3.done")) {
    $EarlierFolders += Get-StepFolder '12b_vbk0_b3'  # b4 after a b3 top-up: all decided blocks
}
$Masks = @('0x000F', '0x00F0')

$Runs = @()
$Index = 0
foreach ($Block in $PhaseBlocks[$Phase]) {
    $Label = "VBK0_$Block"
    $Out = "$Folder\$Label.json"
    $RunEstimatesS[$Label] = 1900
    $Runs += Start-Run -Label $Label -MaskHex $Masks[$Index] -WrapOutput $Out `
        -Environment (Get-R79Environment 'VBK0' "$Folder\${Label}_t4h" "$X11Folder\${Block}_plan.json") `
        -TaskType 'jp3_12b_vbk0' -Workers 4 -Arguments @("$Coupled/las_t3_dg3.py", $Worktree, 'run', $Out,
            '--levels', 'L2', '--keys-file', "$X11Folder\${Block}_keys.txt", '--workers', '4', '--affinity', $Masks[$Index])
    $Index++
}
Wait-Runs $Runs
Invoke-IdentityCheck

$Arguments = @("$Coupled/jp3_12b_judge.py", 'decide', '--selection', $X11Selection, '--selection-sha256', (Get-X11Sha),
    '--out', "$Folder\judge\decision.json")
foreach ($Source in @($EarlierFolders) + @($Folder)) {
    foreach ($File in @(Get-ChildItem -LiteralPath $Source -File -Filter 'VBK0_b?.json')) {
        $Block = $File.BaseName.Substring(5)
        $Arguments += @('--vbk0', "$Block=$($File.FullName)", '--vbk0-t4h', "$Block=$Source\VBK0_${Block}_t4h")
    }
}
Invoke-Judge 'decide' $Arguments | Out-Null

Complete-Step
