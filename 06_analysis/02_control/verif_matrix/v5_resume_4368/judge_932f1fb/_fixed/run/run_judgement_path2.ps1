# 436.8 R4 harness re-judgement, path 2 (re-audit r4_prerun_reaudit.md M-2, A-2 / A-3, R-1 .. R-5).
# Run by the main session in the main checkout after the M4 merge (RD-1 5). It reads only and
# writes only to judge_<M4 short>/harness_path2/. The two hashes are the only placeholders:
# M4_FULL_HASH (the --no-ff merge of R4 on master) and R4_FULL_HASH (the R4 integration merge).
#
# Steps (M-2 numbering), every step logged to <Out>/logs/<name>.out.txt / .err.txt and rc.tsv
# (exit code, output sha256, stdout sha256):
#   0 start gate (nothing runs unless all true): HEAD = M4, clean tracked tree, R4 is in M4,
#     the 15 (라) files have the same raw blob sha256 at M4 and R4 (and the re-audit R4 table
#     value), b9f5707..M4 -- 03_src 02_params is empty, the manifest copy is fa0b72bf..., the 43
#     result files, 5 key sources, 4 stored V0 grids and the other step inputs exist
#   1 seal  2 harness (+ R-2)  3 anchors  4 jp  5 g3 (G-3 false = stop)  6 d1 wrapper (R-5)
#   7 u3 (+ U-3 keys, U-6 242)  8 v5j u9  9 c16  10 items  11 v5c stage1  12 v5c grid (+ R-3)
#   13 v5c noise (+ R-1)  14 v5c merge  15 sha256 list of all outputs  16 end gate
# Not used: --allow-import-sha, --gs, --t4h-root (the convention folders exist; the start gate
# stops when they do not). Interpreter: conda run -n dynamics-dev python -I -B.
# No function here mixes Tee-Object with return (R-5): output goes to files by redirection.
# CPU placement: set by the main session from the compute-scheduler-expert table.

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Continue'

$Repo = 'C:\workspace\outrigger_control'
Set-Location -LiteralPath $Repo
$M4 = 'M4_FULL_HASH'
$R4 = 'R4_FULL_HASH'
$R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$Conda = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
$CondaPython = @('run', '-n', 'dynamics-dev', 'python', '-I', '-B')
$env:PYTHONDONTWRITEBYTECODE = '1'; $env:MKL_THREADING_LAYER = 'TBB'
foreach ($name in 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMBA_NUM_THREADS') {
    Set-Item "env:$name" '1'
}

$ManifestSource = 'C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\7ea6ef9d-fc13-4bf1-8179-0167f32d78a7\scratchpad\r4-p2\p2_manifest_draft.json'
$ManifestSha256 = 'fa0b72bf90694455da2edc5aa0598614adbae541d8b769560e1eee7b42696786'
$Base = '06_analysis\02_control\verif_matrix\v5_resume_4368'
$P2 = "$Repo\$Base\path2"
$V5c = "$Repo\$Base\path2_v5c"
$Rk = "$Repo\06_analysis\03_hydraulic\coupled\v5\resume_k1"
$Lk = "$Repo\06_analysis\02_control\v5_rerun\las_k1"
$V5 = "$Repo\06_analysis\03_hydraulic\coupled\v5"
$StoredGrid = "$Repo\06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid"
$X = "$Repo\07_results\S9\R4368X_b9f5707_20261115_013947"
$JpBatches = @("$Repo\07_results\S9\batch_V5-JP-VB_20261108_115631",
    "$Repo\07_results\S9\batch_V5-JP-V0_20261108_131212")

$GridStems = @('grid_r67_main', 'grid_r67_top', 'grid_r69_bottom', 'grid_r69_top')
$U3Names = @('slope', 'h9', 'h6', 'g6', 'g8', 'p3b', 'x426b', 'C', 'D')
$U6Files = @('u6_b5_main_VB.json', 'u6_b5_wide_VB.json', 'u6_b5_main_VB_IND_LAS.json',
    'u6_b5_wide_VB_IND_LAS.json')

# RD-1 4 / rev16:325 (라): the path 2 allow-list files ('/' paths for git), with the re-audit R4
# blob table (raw bytes of git show 1ab93f0:<file>; three path2_v5c files are CRLF blobs, R-7)
$BaseGit = '06_analysis/02_control/verif_matrix/v5_resume_4368'
$AllowListPath2 = [ordered]@{
    "$BaseGit/path2/README.md"           = 'f1803a5852a387630bf2cd5c8f43de114e1267e4e151b93dbbe35f999d5e0dd4'
    "$BaseGit/path2/p2_4368.py"          = '51a0e7ccca2a6cbd3abfdf0c09d27fb03eac6985c31954e0b526c075ceba12e6'
    "$BaseGit/path2/p2_u3.py"            = '7eb119223dfbb5236ee43213843edb1ae4e2ea1e618b5a33b72ae22660ffaf72'
    "$BaseGit/path2/p2_v5j.py"           = 'b815771dcaee69f5b474a7a6328f7699631d4c69309a973314a0ba3eaf06ecb8'
    "$BaseGit/path2/p2_x16.py"           = 'e17a144c38b3fc3a8b8f5b47209be0d3711a3ccba643863be44a820d275223e5'
    "$BaseGit/path2/test_p2_4368.py"     = 'cd9c10a3aa8d2f5ed5e3bcd0c8e6bf301b84d153d663e7d76786d8f1e7fd7985'
    "$BaseGit/path2/test_p2_u3.py"       = '533501dd889e8f263eee8215910d18f451bc0fca576732c8eb452d527a619c23'
    "$BaseGit/path2/test_p2_v5j.py"      = '017d432730bc6e52d11fc116cd29692f1af3b38b4d098b53f80edb7a061f9092'
    "$BaseGit/path2/test_p2_x16.py"      = 'c7efdefd7e7c6633823d6283d72086623055c6c73acafc40307b64b695f890d8'
    "$BaseGit/path2_v5c/README.md"       = 'c64a5282f42a68481c7389b61a063c8ba190952d8da37589b4eefd69f5c02888'
    "$BaseGit/path2_v5c/p2v5c_common.py" = '6640cc93d58a3eafe875e7b890472ac68263a31f511ea9d8f18123f69476fa82'
    "$BaseGit/path2_v5c/p2v5c_grid.py"   = '88e54e3438b145c2f6459e8fa1ea61acf819e1ae7f93311276216137cc476388'
    "$BaseGit/path2_v5c/p2v5c_noise.py"  = '7fa4153fe254d0d59d2f4dbb94b543f9235b6b76adea071ee637b16a73a112a1'
    "$BaseGit/path2_v5c/p2v5c_stage1.py" = 'd49cf4e617eb55283b68907524e56c6bd6659a93c656a9280ad0d24fe3421996'
    "$BaseGit/path2_v5c/test_p2v5c.py"   = '4793f54b31bb94cf6f1f3b64bc217efef998a08de543a025be7fddf5436fbb37'
}

# Expected exit codes per step, fixed before any result (tool README contracts: 0 nothing found,
# 1 fail / undecidable, 2 stop S-* / H-* or gate, 3 tool error). A finding is not a failure here;
# the outputs are read by the judgement. Not listed = this run fails.
$ExpectedRc = [ordered]@{
    seal       = @(0)
    harness    = @(0, 1, 2)   # S-6 / S-8 / S-15 stops are findings; S-1 and HEAD are checked apart
    anchors    = @(0, 1, 2)
    jp         = @(0, 2)      # 2 = RD-11 stop markers (S-15, unreadable events / shadow)
    g3         = @(0)         # 2 = G-3 false: H-3 / H-4 are not judged, the run stops (rev16:142)
    d1         = @(0, 1)      # 2 = G-2 input missing, seal mismatch or S-12 (p2_d1 / wrapper)
    u3         = @(0, 1, 2)   # 1 = G-5 (ask), 2 = gates incl. G-6 (JD-7 expects 3 G-6 records)
    v5j_u9     = @(0, 1, 2)
    c16        = @(0, 1, 2)
    items      = @(0)
    v5c_stage1 = @(0, 1, 2)
    v5c_grid   = @(0, 1, 2)   # 2 includes the supplement 6-4 "H-10" marker
    v5c_noise  = @(0, 1, 2)
    v5c_merge  = @(0, 1, 2)   # 2 includes the RD-7 markers and S-8; not_merged is checked apart
}
$HeadCheckedSteps = @('harness', 'anchors', 'jp', 'g3', 'u3', 'v5j_u9', 'c16',
    'v5c_stage1', 'v5c_grid', 'v5c_noise', 'v5c_merge')
$FatalStopCodes = @('S-1', 'P2-SHA')

$StepRc = [ordered]@{}
$GateProblems = [System.Collections.Generic.List[string]]::new()

# ------------------------------------------------------------------------------ helpers
function Get-Sha256([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-BlobSha256([string]$Commit, [string]$File) {
    # Raw blob bytes (the bytes of `git show <commit>:<file>`, no filter, no text decoding).
    $info = [System.Diagnostics.ProcessStartInfo]::new('git')
    foreach ($argument in 'cat-file', 'blob', "${Commit}:$File") { $info.ArgumentList.Add($argument) }
    $info.WorkingDirectory = $Repo
    $info.RedirectStandardOutput = $true
    $info.UseShellExecute = $false
    $process = [System.Diagnostics.Process]::Start($info)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    $digest = $hasher.ComputeHash($process.StandardOutput.BaseStream)
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { return $null }
    return ([System.BitConverter]::ToString($digest) -replace '-', '').ToLowerInvariant()
}

function Read-JsonFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
    } catch {
        return $null
    }
}

function Get-JsonValue($Node, [string[]]$Keys) {
    # Walks a ConvertFrom-Json -AsHashtable tree; $null when a key is missing. A JSON list comes
    # back enumerated, so callers wrap list values in @(...).
    foreach ($key in $Keys) {
        if ($Node -isnot [System.Collections.IDictionary] -or -not $Node.Contains($key)) {
            return $null
        }
        $Node = $Node[$key]
    }
    return $Node
}

function Add-RcRow([string]$Name, [string]$Rc, [string]$Seconds, [string]$Started,
    [string]$OutSha, [string]$StdoutSha) {
    Add-Content -LiteralPath "$Log\rc.tsv" "$Name`t$Rc`t$Seconds`t$Started`t$OutSha`t$StdoutSha"
}

function Invoke-Step([string]$Name, [string]$OutFile, [string[]]$Arguments) {
    # One tool run; stdout / stderr go to files (R-5), the exit code to $StepRc and rc.tsv.
    $started = Get-Date
    & $Conda @CondaPython @Arguments > "$Log\$Name.out.txt" 2> "$Log\$Name.err.txt"
    $rc = $LASTEXITCODE
    $script:StepRc[$Name] = $rc
    $outSha = if (Test-Path -LiteralPath $OutFile -PathType Leaf) { Get-Sha256 $OutFile } else { '-' }
    $seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
    Add-RcRow $Name $rc $seconds $started.ToString('MM-dd HH:mm:ss') $outSha (Get-Sha256 "$Log\$Name.out.txt")
}

function Assert-StepOutput([string]$Name, [string]$OutFile) {
    # Stop the run on an exit code outside the table, a missing / unreadable output, a seal or
    # import stop, or a HEAD check that is not ok (the tools judge nothing then).
    $rc = $StepRc[$Name]
    if ($ExpectedRc[$Name] -notcontains $rc) {
        throw "${Name}: exit $rc is not in the expected set ($($ExpectedRc[$Name] -join ', '))"
    }
    $doc = Read-JsonFile $OutFile
    if ($null -eq $doc) { throw "${Name}: output $OutFile missing or not JSON" }
    $codes = @(Get-JsonValue $doc 'stop_codes')
    $fatal = @($codes | Where-Object { $FatalStopCodes -contains $_ })
    if ($fatal.Count -gt 0) { throw "${Name}: stop codes $($fatal -join ', ') (seals / imports)" }
    if ($HeadCheckedSteps -contains $Name -and (Get-JsonValue $doc 'head_check', 'ok') -ne $true) {
        throw "${Name}: head_check.ok is not true (RD-1 5, S-12)"
    }
}

function Add-GateProblem([string]$Text) { $script:GateProblems.Add($Text) }

# --------------------------------------------------------------------- step 0 start gate
function Test-PlaceholderHashes {
    foreach ($pair in @(@('M4', $M4), @('R4', $R4))) {
        if ($pair[1] -notmatch '^[0-9a-f]{40}$') { Add-GateProblem "$($pair[0]) is not a 40-hex commit: $($pair[1])" }
    }
}

function Test-CheckoutState {
    $head = "$(git rev-parse HEAD)".Trim()
    if ($LASTEXITCODE -ne 0 -or $head -ne $M4) { Add-GateProblem "HEAD $head is not M4 $M4 (RD-1 5, S-12)" }
    $dirty = @(git status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) { Add-GateProblem "tracked tree not clean: $($dirty -join '; ')" }
    git merge-base --is-ancestor $R4 $M4
    if ($LASTEXITCODE -ne 0) { Add-GateProblem "R4 $R4 is not an ancestor of M4" }
    $changed = @(git diff --name-only "$R2..$M4" -- 03_src 02_params)
    if ($LASTEXITCODE -ne 0 -or $changed.Count -ne 0) {
        Add-GateProblem "b9f5707..M4 -- 03_src 02_params not empty (git exit $LASTEXITCODE): $($changed -join '; ')"
    }
}

function Test-AllowListBlobs {
    # RD-1 4: M4 and R4 raw blobs equal for the 15 (라) files (R-7: raw bytes, not LF-normalised)
    $rows = foreach ($file in $AllowListPath2.Keys) {
        $atM4 = Get-BlobSha256 $M4 $file
        $atR4 = Get-BlobSha256 $R4 $file
        $verdict = if ($null -ne $atM4 -and $atM4 -eq $atR4 -and $atR4 -eq $AllowListPath2[$file]) { 'same' } else { 'DIFFERENT' }
        if ($verdict -ne 'same') { Add-GateProblem "(라) $file M4 $atM4 / R4 $atR4 / table $($AllowListPath2[$file])" }
        "$file`t$atM4`t$atR4`t$($AllowListPath2[$file])`t$verdict"
    }
    Set-Content -LiteralPath "$Log\blob_table_path2.tsv" -Encoding utf8NoBOM -Value (@("file`tM4`tR4`taudit_R4`tverdict") + $rows)
    if (@($rows).Count -ne 15) { Add-GateProblem "(라) table has $(@($rows).Count) files, 15 expected" }
}

function Copy-Manifest {
    if (-not (Test-Path -LiteralPath $ManifestSource -PathType Leaf) -or (Get-Sha256 $ManifestSource) -ne $ManifestSha256) {
        Add-GateProblem "manifest source missing or its sha256 is not $ManifestSha256 (R-4)"
        return
    }
    Copy-Item -LiteralPath $ManifestSource -Destination "$Out\manifest.json"
    if ((Get-Sha256 "$Out\manifest.json") -ne $ManifestSha256) { Add-GateProblem 'manifest copy sha256 differs (R-4)' }
}

function Get-RequiredInputs {
    # Supplement 4-4: RK 21 + LK 22 result files, 5 key sources, 4 stored V0 grids; then the
    # other inputs of steps 3 .. 13 (names only, no content is read).
    $rkFiles = @('h1_d1.jsonl', 'h5_u9_v0.jsonl', 'h6_dg3_v4on.json', 'h7_dg3_off.json',
        'h8_noise_VB.json', 'h8_noise_V0.json', 'h8_seedext_VB.json', 'h8_seedext_V0.json',
        'h9_stage1.jsonl', 'h9_family_F.jsonl', 'h9_family_F_VB.json', 'h9_family_F_V0.json',
        'h10_reuse_rerun.jsonl') | ForEach-Object { "$Rk\$_" }
    $rkFiles += $GridStems | ForEach-Object { "$Rk\h9_grid\$_.json"; "$Rk\h9_grid_v0_sample\$_.json" }
    $lkFiles = foreach ($name in $U3Names) { "$Lk\u3_${name}_V0.json"; "$Lk\u3_${name}_VB.json" }
    $lkFiles += $U6Files | ForEach-Object { "$Lk\$_" }
    $keySources = @("$V5\dg3\dg3_v4_on.json", "$V5\noise_vb\r79_VB_L1L2L3.json",
        "$V5\noise_v0\r79_V0_L1L2L3.json", "$V5\seedext\r79_VB_seedext.json", "$V5\seedext\r79_V0_seedext.json")
    $storedGrids = $GridStems | ForEach-Object { "$StoredGrid\$_.json" }
    $other = @("$Rk\h10_overlap_t_a.json", "$V5\main.jsonl", "$V5\p3_hash.jsonl",
        "$V5\las\shadow_jp_b0.jsonl") + ($JpBatches | ForEach-Object { "$_\batch.json" })
    return [ordered]@{ result_files = @($rkFiles + $lkFiles); key_sources = $keySources;
        stored_v0_grids = @($storedGrids); other = $other }
}

function Test-RequiredInputs {
    $inputs = Get-RequiredInputs
    $expectedCounts = @{ result_files = 43; key_sources = 5; stored_v0_grids = 4; other = 6 }
    foreach ($group in $inputs.Keys) {
        $files = @($inputs[$group])
        if ($files.Count -ne $expectedCounts[$group]) { Add-GateProblem "$group lists $($files.Count) files, $($expectedCounts[$group]) expected" }
        foreach ($file in $files) {
            if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { Add-GateProblem "$group missing: $file" }
        }
    }
    # R11-2 convention T4h folders exist, so --t4h-root is not given (decided before results)
    foreach ($folder in "$X\H-11", "$X\_identity", "$X\_runners", "$Rk\h10_reuse_rerun_t4h", "$Rk\h6_dg3_v4on_t4h") {
        if (-not (Test-Path -LiteralPath $folder -PathType Container)) { Add-GateProblem "folder missing: $folder" }
    }
}

function Invoke-StartGate {
    Test-CheckoutState
    Test-AllowListBlobs
    Copy-Manifest
    Test-RequiredInputs
    Set-Content -LiteralPath "$Log\start_gate.txt" -Encoding utf8NoBOM -Value (@("problems: $($GateProblems.Count)") + $GateProblems)
    Add-RcRow 'START_GATE' $GateProblems.Count 0 (Get-Date).ToString('MM-dd HH:mm:ss') '-' '-'
    if ($GateProblems.Count -gt 0) { throw "start gate: $($GateProblems.Count) problem(s), see $Log\start_gate.txt" }
}

# ---------------------------------------------------------------------- step assertions
function Assert-HarnessInputs {
    # R-2: the 9 bundles are there, the supplement 4-4 input check ran on 42 files without
    # stops, and the H-9 parts are all three.
    $doc = Read-JsonFile "$Out\harness.json"
    $bundles = Get-JsonValue $doc 'bundles'
    foreach ($bundle in 'H-1', 'H-3', 'H-4', 'H-5', 'H-6', 'H-7', 'H-8', 'H-9', 'H-10') {
        if ($null -eq (Get-JsonValue $bundles $bundle)) { throw "R-2: bundle $bundle missing in harness.json" }
        if ((Get-JsonValue $bundles $bundle, 'missing_from_manifest') -eq $true) { throw "R-2: bundle $bundle missing from the manifest" }
    }
    if ((Get-JsonValue $doc 'r4_input_check', 'expected_files') -ne 42) { throw 'R-2: r4_input_check.expected_files is not 42' }
    if (@(Get-JsonValue $doc 'r4_input_check', 'stops').Where({ $null -ne $_ }).Count -gt 0) { throw 'R-2: r4_input_check has stops' }
    foreach ($part in 'main', 'V0-sample', 'family-F') {
        if ($null -eq (Get-JsonValue $bundles 'H-9', 'parts', $part)) { throw "R-2: H-9 part $part missing" }
    }
}

function Assert-G3True {
    # Step 5: a false G-3 (H-11) means H-3 / H-4 are not judged; stop and ask (rev16:142)
    if ((Get-JsonValue (Read-JsonFile "$Out\g3.json") 'G-3') -ne $true) { throw 'G-3 is not true: H-3 / H-4 not judged, stop and ask' }
}

function Assert-D1HeadCheck {
    # R-5: the wrapper writes its HEAD check on the first stdout line only
    $first = Get-Content -LiteralPath "$Log\d1.out.txt" | Where-Object { $_.Trim() } | Select-Object -First 1
    $record = if ($first) { $first | ConvertFrom-Json -AsHashtable } else { $null }
    if ((Get-JsonValue $record 'head_check', 'ok') -ne $true) { throw 'd1: the wrapper head_check is not ok (S-12)' }
}

function Assert-U3Counts {
    # Step 7: U-3 keys 1,114 per setting, U-6 242 cases per controller column
    $doc = Read-JsonFile "$Out\u3.json"
    foreach ($setting in 'V0', 'VB') {
        $bySuite = Get-JsonValue $doc 'U-3', 'counts', $setting
        $total = if ($bySuite) { ($bySuite.Values | Measure-Object -Sum).Sum } else { 0 }
        if ($total -ne 1114) { throw "u3: U-3 $setting keys $total, 1114 expected" }
    }
    foreach ($controller in 'C2', 'ABL', 'IND', 'IND_LAS') {
        $cases = Get-JsonValue $doc 'U-6', 'table', $controller, 'cases'
        if ($cases -ne 242) { throw "u3: U-6 $controller cases $cases, 242 expected" }
    }
}

function Assert-GridPairSource {
    # R-3: the V0 pair source is the stored grid and the sample had 8 jobs
    $doc = Read-JsonFile "$Out\p2v5c_grid.json"
    if ((Get-JsonValue $doc 'v0_pair', 'source') -ne 'stored') { throw 'R-3: v0_pair.source is not stored' }
    if ((Get-JsonValue $doc 'v0_pair', 'sample', 'jobs') -ne 8) { throw 'R-3: v0_pair.sample.jobs is not 8' }
}

function Assert-NoiseSeedext {
    # R-1: both seedext files were read and the seedext block is there
    $doc = Read-JsonFile "$Out\p2v5c_noise.json"
    foreach ($keys in @(@('inputs', 'seedext_vb'), @('inputs', 'seedext_v0'),
            @('reaggregated', 'seedext', 'VB'), @('reaggregated', 'seedext', 'V0'))) {
        if ($null -eq (Get-JsonValue $doc $keys)) { throw "R-1: $($keys -join '.') missing in p2v5c_noise.json" }
    }
}

# ------------------------------------------------------------------------- step 1 .. 14
function Invoke-Steps {
    Invoke-Step 'seal' "$Out\seal.json" @("$P2\p2_4368.py", '--out', "$Out\seal.json", 'seal')
    Assert-StepOutput 'seal' "$Out\seal.json"

    Invoke-Step 'harness' "$Out\harness.json" @("$P2\p2_4368.py", '--out', "$Out\harness.json", 'harness',
        '--manifest', "$Out\manifest.json", '--expect-head', $M4)
    Assert-StepOutput 'harness' "$Out\harness.json"
    Assert-HarnessInputs

    Invoke-Step 'anchors' "$Out\anchors.json" @("$P2\p2_4368.py", '--out', "$Out\anchors.json", 'anchors',
        '--h1', "$Rk\h1_d1.jsonl", '--expect-head', $M4)
    Assert-StepOutput 'anchors' "$Out\anchors.json"

    Invoke-Step 'jp' "$Out\jp.json" @("$P2\p2_4368.py", '--out', "$Out\jp.json", 'jp',
        '--shadow', "$V5\las\shadow_jp_b0.jsonl", '--batch', $JpBatches[0], '--batch', $JpBatches[1], '--expect-head', $M4)
    Assert-StepOutput 'jp' "$Out\jp.json"

    Invoke-Step 'g3' "$Out\g3.json" @("$P2\p2_x16.py", '--out', "$Out\g3.json", 'g3', '--h11-dir', "$X\H-11", '--expect-head', $M4)
    Assert-StepOutput 'g3' "$Out\g3.json"
    Assert-G3True

    Invoke-Step 'd1' "$Out\d1.json" @("$P2\p2_x16.py", 'd1', '--expect-head', $M4, '--', '--h1', "$Rk\h1_d1.jsonl", '--out', "$Out\d1.json")
    Assert-D1HeadCheck
    Assert-StepOutput 'd1' "$Out\d1.json"

    $u3Arguments = foreach ($name in $U3Names) { '--u3'; "V0=$Lk\u3_${name}_V0.json"; '--u3'; "VB=$Lk\u3_${name}_VB.json" }
    Invoke-Step 'u3' "$Out\u3.json" (@("$P2\p2_u3.py", '--out', "$Out\u3.json") + $u3Arguments + @(
            '--u6', "ALL=$Lk\u6_b5_main_VB.json", '--u6', "ALL=$Lk\u6_b5_wide_VB.json",
            '--u6', "IND_LAS=$Lk\u6_b5_main_VB_IND_LAS.json", '--u6', "IND_LAS=$Lk\u6_b5_wide_VB_IND_LAS.json",
            '--h1', "$Rk\h1_d1.jsonl", '--expect-head', $M4))
    Assert-StepOutput 'u3' "$Out\u3.json"
    Assert-U3Counts

    # u9: --vb / --stored-main / --stored-p3 as in the first path 2 run (run_all.ps1), H-5 README
    Invoke-Step 'v5j_u9' "$Out\v5j_u9.json" @("$P2\p2_v5j.py", '--out', "$Out\v5j_u9.json", 'u9',
        '--v0', "$Rk\h5_u9_v0.jsonl", '--vb', "$Rk\h10_reuse_rerun.jsonl", '--stored-main', "$V5\main.jsonl",
        '--stored-p3', "$V5\p3_hash.jsonl", '--expect-head', $M4)
    Assert-StepOutput 'v5j_u9' "$Out\v5j_u9.json"

    Invoke-Step 'c16' "$Out\c16.json" @("$P2\p2_x16.py", '--out', "$Out\c16.json", 'c16', '--out-root', $X, '--expect-head', $M4)
    Assert-StepOutput 'c16' "$Out\c16.json"

    Invoke-Step 'items' "$Out\rd13_items.json" @("$P2\p2_x16.py", '--out', "$Out\rd13_items.json", 'items')
    Assert-StepOutput 'items' "$Out\rd13_items.json"

    Invoke-Step 'v5c_stage1' "$Out\p2v5c_stage1.json" @("$V5c\p2v5c_stage1.py", '--expect-head', $M4,
        '--out', "$Out\p2v5c_stage1.json", 'stage1', '--h9', "$Rk\h9_stage1.jsonl",
        '--h10', "$Rk\h10_reuse_rerun.jsonl", '--overlap-ta', "$Rk\h10_overlap_t_a.json")
    Assert-StepOutput 'v5c_stage1' "$Out\p2v5c_stage1.json"

    $gridArguments = foreach ($stem in $GridStems) {
        '--vb'; "$stem=$Rk\h9_grid\$stem.json"
        '--v0-stored'; "$stem=$StoredGrid\$stem.json"
        '--v0-sample'; "$stem=$Rk\h9_grid_v0_sample\$stem.json"
    }
    Invoke-Step 'v5c_grid' "$Out\p2v5c_grid.json" (@("$V5c\p2v5c_grid.py", '--expect-head', $M4,
            '--out', "$Out\p2v5c_grid.json", 'grid') + $gridArguments + @('--family-f', "$Rk\h9_family_F.jsonl"))
    Assert-StepOutput 'v5c_grid' "$Out\p2v5c_grid.json"
    Assert-GridPairSource

    Invoke-Step 'v5c_noise' "$Out\p2v5c_noise.json" @("$V5c\p2v5c_noise.py", '--expect-head', $M4,
        '--out', "$Out\p2v5c_noise.json", 'noise', '--noise-vb', "$Rk\h8_noise_VB.json",
        '--noise-v0', "$Rk\h8_noise_V0.json", '--h6', "$Rk\h6_dg3_v4on.json",
        '--seedext-vb', "$Rk\h8_seedext_VB.json", '--seedext-v0', "$Rk\h8_seedext_V0.json",
        '--judge-dir', "$Out\p2v5c_r79_judge", '--git-at-start', $R2)
    Assert-StepOutput 'v5c_noise' "$Out\p2v5c_noise.json"
    Assert-NoiseSeedext

    Invoke-Step 'v5c_merge' "$Out\p2v5c_merge.json" @("$V5c\p2v5c_stage1.py", '--expect-head', $M4,
        '--out', "$Out\p2v5c_merge.json", 'merge', '--part', "$Out\p2v5c_noise.json",
        '--part', "$Out\p2v5c_stage1.json", '--part', "$Out\p2v5c_grid.json")
    Assert-StepOutput 'v5c_merge' "$Out\p2v5c_merge.json"
    if ((Get-JsonValue (Read-JsonFile "$Out\p2v5c_merge.json") 'not_merged') -eq $true) { throw 'v5c_merge: not merged (S-11 / S-12)' }
}

# ---------------------------------------------------------------- step 15 and 16
function Write-OutputShaList {
    # Same form as path 1 step 6: every output file but logs\ and this list, before any comparison
    $root = (Resolve-Path -LiteralPath $Out).Path
    Get-ChildItem -LiteralPath $Out -Recurse -File |
        Where-Object { $_.Name -ne 'sha256_manifest.txt' -and $_.FullName -notlike "$root\logs\*" } |
        Sort-Object FullName |
        ForEach-Object { "$(Get-Sha256 $_.FullName)  $($_.FullName.Substring($root.Length + 1))" } |
        Set-Content -LiteralPath "$Out\sha256_manifest.txt" -Encoding utf8NoBOM
}

function Test-EndGate {
    # HEAD and clean tree again, then every step of the table ran with an expected exit code.
    $problems = [System.Collections.Generic.List[string]]::new()
    $head = "$(git rev-parse HEAD)".Trim()
    if ($head -ne $M4) { $problems.Add("end: HEAD $head is not M4") }
    $dirty = @(git status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $dirty.Count -ne 0) { $problems.Add("end: tracked tree not clean: $($dirty -join '; ')") }
    $rows = foreach ($name in $ExpectedRc.Keys) {
        $rc = if ($StepRc.Contains($name)) { $StepRc[$name] } else { 'not run' }
        $verdict = if ($ExpectedRc[$name] -contains $rc) { 'expected' } else { 'UNEXPECTED' }
        if ($verdict -ne 'expected') { $problems.Add("end: $name exit $rc ($($ExpectedRc[$name] -join '/') expected)") }
        "$name`t$rc`t$($ExpectedRc[$name] -join '/')`t$verdict"
    }
    Set-Content -LiteralPath "$Log\rc_gate.tsv" -Encoding utf8NoBOM -Value (@("step`trc`texpected`tverdict") + $rows)
    Set-Content -LiteralPath "$Log\end_gate.txt" -Encoding utf8NoBOM -Value (@("problems: $($problems.Count)") + $problems)
    $script:EndProblemCount = $problems.Count
}

# --------------------------------------------------------------------------------- run
Test-PlaceholderHashes  # before any folder is made: a placeholder left in would name the folder
if ($GateProblems.Count -gt 0) { Write-Output ($GateProblems -join "`n"); exit 1 }
$Out = "$Repo\$Base\judge_$($M4.Substring(0, 7))\harness_path2"
$Log = "$Out\logs"
if (Test-Path -LiteralPath $Out) {
    $existing = @(Get-ChildItem -LiteralPath $Out -Recurse -File | Where-Object { $_.FullName -notlike "$Log\*" })
    if ($existing.Count -gt 0) { Write-Output "output folder already has $($existing.Count) file(s): $Out (move it aside first)"; exit 1 }
}
New-Item -ItemType Directory -Force -Path $Log | Out-Null
Add-RcRow 'RUNSTART' 0 0 (Get-Date).ToString('MM-dd HH:mm:ss') '-' '-'

$RunFailure = $null
$EndProblemCount = 0
try {
    Invoke-StartGate
    Invoke-Steps
} catch {
    $RunFailure = $_.Exception.Message
    Set-Content -LiteralPath "$Log\stopped.txt" -Encoding utf8NoBOM -Value $RunFailure
}
Write-OutputShaList
Test-EndGate
Add-RcRow 'ALLDONE' $(if ($RunFailure -or $EndProblemCount) { 1 } else { 0 }) 0 (Get-Date).ToString('MM-dd HH:mm:ss') '-' '-'
if ($RunFailure) { Write-Output "stopped: $RunFailure" }
if ($EndProblemCount -gt 0) { Write-Output "end gate: $EndProblemCount problem(s), see $Log\end_gate.txt" }
if ($RunFailure -or $EndProblemCount -gt 0) { exit 1 }
Write-Output "path 2 done: $Out (sha256 list sha256_manifest.txt, exit codes logs\rc_gate.tsv)"
exit 0
