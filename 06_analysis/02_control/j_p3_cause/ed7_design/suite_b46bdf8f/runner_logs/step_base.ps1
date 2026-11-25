#Requires -Version 7
# Step 1: base side (merge-base 79495405, worktree ed6-run6).
$ErrorActionPreference = 'Stop'
$R = 'C:\Users\jinbeom\.claude\runners\outrigger-ed7-suite'
& 'C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe' -NoProfile -File "$R\full_suite_ed7.ps1" `
    -Side base -Worktree C:\workspace\outrigger_control\.claude\worktrees\ed6-run6 -OutDir "$R\base" `
    -ExpectCommit 7949540527baea680f144ef4e00a970cb10b9830
exit $LASTEXITCODE
