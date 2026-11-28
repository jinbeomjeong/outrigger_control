# ed9 R3 post-run: step_check, r3c head check, scan, c1..c9, R4 (design reading).
# Prints only status and exit codes. Full stdout of each tool goes to $R\cmp\<name>.console.txt.
$ErrorActionPreference = 'Stop'
$Py  = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$PyD = 'C:\ProgramData\miniforge3\envs\python-dev\python.exe'
$C9b = '15d3a4a4f0d3244c242e98856d2228160d090b2d'
$WT  = 'C:\workspace\outrigger_control\.claude\worktrees\ed9-c9b'
$WTJ = 'C:\workspace\outrigger_control\.claude\worktrees\ed9-t9b'
$WTD = 'C:\workspace\outrigger_control\.claude\worktrees\ed9-diag'
$K   = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\keys_seal_41e107e9\heldout_g_ed8.json'
$J   = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause'
$R   = "$J\ed9_design\r3_runs"
$P   = "$J\ed9_design\d1_prerun"
$S   = "$J\j9_runs\56849248"
$G   = "$J\ed8_design\stage5_aa_diag"
$CI  = "$P\scripts\compare_identity.py"
$A   = "$R\r3a_off_15d3a4a4"
$B   = "$R\r3b_on_15d3a4a4"
$D   = "$R\r3c_diag_15d3a4a4"
$Cmp = "$R\cmp"
New-Item -ItemType Directory -Force $Cmp | Out-Null
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:MKL_THREADING_LAYER = 'TBB'

function Invoke-Step([string]$Name, [string]$Exe, [string[]]$ArgList) {
    $con = "$Cmp\$Name.console.txt"
    $t0 = Get-Date -Format s
    & $Exe @ArgList *> $con
    $code = $LASTEXITCODE
    $status = ''
    $last = Get-Content $con -Tail 1 -ErrorAction SilentlyContinue
    try { $status = ($last | ConvertFrom-Json).status } catch { $status = '?' }
    "{0,-12} exit={1} status={2} start={3}" -f $Name, $code, $status, $t0
    return $code
}

"== step_check"
$dones = @(Get-ChildItem $A, $B -Filter *.done | ForEach-Object FullName)
[void](Invoke-Step 'step_check' $PyD (@('-I','-B','C:\Users\jinbeom\.claude\tools\verif\step_check.py') + $dones + @('--expect-commit', $C9b)))

"== r3c head"
foreach ($n in 'off_plain','on_plain','on_trace') {
    $j = Get-Content "$D\$n.log.json" -Raw | ConvertFrom-Json
    "{0,-10} head_problem={1}" -f $n, ($null -eq $j.head_problem ? 'null' : 'SET')
}

"== scan"
[void](Invoke-Step 'scan_sso' $PyD @('-I','-B',"$P\scripts\scan_d1_step_rows.py",'--rows',"$A\same_shape_off_a1\ed9_heldout_same_shape_off.jsonl",'--group','same_shape_off','--out',"$Cmp\scan_same_shape_off.json"))

$Sst = @('--stored',"$S\ho_v0_a1\ed8_heldout_v0.jsonl",'--stored',"$S\ho_aa2_a1\ed8_heldout_aa2.jsonl",'--stored',"$S\ho_aa3_a1\ed8_heldout_aa3.jsonl")
$Anew = @('--new',"$A\ho_v0_a1\ed8_heldout_v0.jsonl",'--new',"$A\ho_aa2_a1\ed8_heldout_aa2.jsonl",'--new',"$A\ho_aa3_a1\ed8_heldout_aa3.jsonl")
$Bnew = @('--new',"$B\ho_v0_a1\ed9_heldout_v0.jsonl",'--new',"$B\ho_aa2_a1\ed9_heldout_aa2.jsonl",'--new',"$B\ho_aa3_a1\ed9_heldout_aa3.jsonl")

"== compare"
[void](Invoke-Step 'c1' $PyD (@('-I','-B',$CI) + $Sst + $Anew + @('--expect-switch','off','--out',"$Cmp\c1.json")))
[void](Invoke-Step 'c2' $PyD (@('-I','-B',$CI) + $Sst + $Bnew + @('--allowed-from',"$P\scan_d1_step.json",'--allowed-group','stage5_v0','--require-allowed-change','--expect-switch','on','--require-prior',"$Cmp\c1.json",'--out',"$Cmp\c2.json")))
[void](Invoke-Step 'c3' $PyD @('-I','-B',$CI,'--stored',"$A\same_shape_off_a1\ed9_heldout_same_shape_off.jsonl",'--new',"$B\same_shape_a1\ed9_heldout_same_shape.jsonl",'--expect-switch','on','--allowed-from',"$Cmp\scan_same_shape_off.json",'--allowed-group','same_shape_off','--require-allowed-change','--out',"$Cmp\c3.json"))
[void](Invoke-Step 'c4' $PyD @('-I','-B',$CI,'--stored','C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl','--new',"$A\census_v0_off_a1\ed9_census_v0_off.jsonl",'--only-setting','V0','--expect-switch','off','--stored-tag-absent','final_C4G2_LAS_K1','--out',"$Cmp\c4.json"))
[void](Invoke-Step 'c5' $PyD @('-I','-B',$CI,'--stored',"$A\census_v0_off_a1\ed9_census_v0_off.jsonl",'--new',"$B\census_v0_a1\ed9_census_v0.jsonl",'--expect-switch','on','--allowed-from',"$P\scan_d1_step.json",'--allowed-group','census_v0_main','--require-allowed-change','--require-prior',"$Cmp\c4.json",'--out',"$Cmp\c5.json"))
$i = 0
foreach ($f in "$G\runs_trace_on.jsonl","$G\diag2\D_sweep_gyro_off_trace_on.jsonl","$G\diag2\E_sweep_ext_gyro_off_trace_on.jsonl") {
    $tag = @('c6a','c6b','c6c')[$i]; $i++
    [void](Invoke-Step $tag $PyD @('-I','-B',$CI,'--stored',$f,'--new',"$D\off_plain.jsonl",'--subset-of-new','--expect-switch','off','--stored-tag-absent','final_C4G2_LAS_K1','--out',"$Cmp\$tag.json"))
}
[void](Invoke-Step 'c7' $PyD @('-I','-B',$CI,'--stored',"$D\off_plain.jsonl",'--new',"$D\on_plain.jsonl",'--expect-switch','on','--allowed-from',"$P\r3c_expected_d1_step.json",'--allowed-group','r3c_expected','--require-allowed-change','--stored-path-under',$WT,'--new-path-under',$WT,'--require-prior',"$Cmp\c6a.json",'--require-prior',"$Cmp\c6b.json",'--require-prior',"$Cmp\c6c.json",'--out',"$Cmp\c7.json"))
[void](Invoke-Step 'c8' $PyD @('-I','-B',$CI,'--stored',"$D\on_plain.jsonl",'--new',"$D\on_trace.jsonl",'--with-d1-reasons','--stored-path-under',$WT,'--new-path-under',$WTD,'--out',"$Cmp\c8.json"))
[void](Invoke-Step 'c9' $PyD @('-I','-B',$CI,'--stored',"$D\on_plain.jsonl",'--new',"$B\ho_v0_a1\ed9_heldout_v0.jsonl",'--new',"$B\ho_aa2_a1\ed9_heldout_aa2.jsonl",'--new',"$B\ho_aa3_a1\ed9_heldout_aa3.jsonl",'--new',"$B\same_shape_a1\ed9_heldout_same_shape.jsonl",'--only-common','--expect-compared','5','--with-d1-reasons','--out',"$Cmp\c9.json"))
"== done (R4 separate)"
