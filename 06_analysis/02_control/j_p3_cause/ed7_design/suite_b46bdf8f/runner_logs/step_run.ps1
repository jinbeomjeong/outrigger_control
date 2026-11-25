#Requires -Version 7
# Step 2: run side (b46bdf8f, worktree ed7-impl) judged against the base list; then (whatever the
# suite exit code) copies the result files of both sides to the main checkout result folder,
# after the suite has finished reading the main checkout (never while a test runs).
$ErrorActionPreference = 'Stop'
$R = 'C:\Users\jinbeom\.claude\runners\outrigger-ed7-suite'
$Dest = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\suite_b46bdf8f'
$ShaFile = "$R\base\existing_failures.txt.sha256"
if (-not (Test-Path -LiteralPath "$R\base\existing_failures.txt") -or -not (Test-Path -LiteralPath $ShaFile)) {
    Write-Host 'STOP: base existing_failures.txt or its .sha256 is missing'; exit 2
}
$Sha = ((Get-Content -LiteralPath $ShaFile -TotalCount 1).Trim() -split '\s+')[0]
if ($Sha -notmatch '^[0-9a-fA-F]{64}$') { Write-Host "STOP: bad sha256 '$Sha'"; exit 2 }
$Suite = "$R\full_suite_ed7.ps1"
& 'C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe' -NoProfile -File $Suite `
    -Side run -Worktree C:\workspace\outrigger_control\.claude\worktrees\ed7-impl -OutDir "$R\run" `
    -ExpectCommit b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9 -BaselineList "$R\base\existing_failures.txt" -BaselineSha256 $Sha
$SuiteCode = $LASTEXITCODE

$ErrorActionPreference = 'Continue'
foreach ($Side in 'base', 'run') {
    $To = "$Dest\$Side"
    New-Item -ItemType Directory -Force -Path $To | Out-Null
    foreach ($Name in 'junit.xml', 'suite_record.json', 'existing_failures.txt', 'existing_failures.txt.sha256',
                      'suite_judgement.json', 'worktree_tests.md', 'worktree_tests.log') {
        $From = "$R\$Side\$Name"
        if (Test-Path -LiteralPath $From) { Copy-Item -LiteralPath $From -Destination "$To\$Name" }
    }
}
Write-Host "[collect] result files copied to $Dest (suite exit $SuiteCode)"
exit $SuiteCode
