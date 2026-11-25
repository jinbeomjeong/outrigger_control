#Requires -Version 7
# P7-4 run side at C (8a2a52ce, worktree ed7-impl), judged against the fixed base list (79495405,
# sha256 571f42a1...). The suite script is the one in the C worktree. Afterwards (whatever the suite
# exit code) the run result files are copied to the main checkout result folder, after the suite
# has finished reading the main checkout.
$ErrorActionPreference = 'Stop'
$R = 'C:\Users\jinbeom\.claude\runners\outrigger-ed7-suite-c'
$W = 'C:\workspace\outrigger_control\.claude\worktrees\ed7-impl'
$Dest = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\suite_8a2a52ce\run'
$BaseList = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\suite_b46bdf8f\base\existing_failures.txt'
$BaseSha = '571f42a1074b7d506be885d9c3a68f22b2661821e011e83d751bc6ac06ecabeb'
$Pwsh = 'C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe'
$Suite = "$W\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed7\full_suite_ed7.ps1"
if (-not (Test-Path -LiteralPath $BaseList)) { Write-Host 'STOP: base list missing'; exit 2 }
$Have = (Get-FileHash -Algorithm SHA256 -LiteralPath $BaseList).Hash.ToLower()
if ($Have -ne $BaseSha) { Write-Host "STOP: base list sha256 $Have"; exit 2 }
& $Pwsh -NoProfile -File $Suite -Side run -Worktree $W -OutDir "$R\run" `
    -ExpectCommit 8a2a52ce2c07d2af11a6212a2932d2061261f156 -BaselineList $BaseList -BaselineSha256 $BaseSha
$SuiteCode = $LASTEXITCODE

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
foreach ($Name in 'junit.xml', 'suite_record.json', 'suite_judgement.json', 'worktree_tests.md', 'worktree_tests.log') {
    $From = "$R\run\$Name"
    if (Test-Path -LiteralPath $From) { Copy-Item -LiteralPath $From -Destination "$Dest\$Name" }
}
Write-Host "[collect] result files copied to $Dest (suite exit $SuiteCode)"
exit $SuiteCode
