#Requires -Version 5.1
# Dedicated disposable GitHub-hosted runner only. Never run on a personal host.
param([Parameter(Mandatory)][string]$Python)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'This lab setup requires a disposable GitHub-hosted runner.'
}
$root = 'C:\SecureAuditStudy'
if (Test-Path $root) { throw 'Lab folder already exists; refusing to overwrite.' }
New-Item -ItemType Directory $root | Out-Null
foreach ($folder in @('core', 'checks', 'tools')) { Copy-Item $folder $root -Recurse }
$output = Join-Path $root 'lab-results'
New-Item -ItemType Directory $output | Out-Null
$snapshot = "$env:ImageOS/$env:ImageVersion/run-$env:GITHUB_RUN_ID"
$runner = Join-Path $root 'tools\validate_windows.py'
& $Python $runner --case-id full-admin --snapshot-id $snapshot --output "$output\full-admin"
if ($LASTEXITCODE) { throw 'Elevated baseline capture failed.' }
& $Python $runner --case-id firewall-only-admin --snapshot-id $snapshot --output "$output\firewall-only-admin" --select WIN-FW-001
if ($LASTEXITCODE) { throw 'Selected baseline capture failed.' }

$user = 'SecureAuditLab'
$created = $false
try {
    $password = 'Sa!' + [Guid]::NewGuid().ToString('N') + '9z'
    Write-Output "::add-mask::$password"
    $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
    New-LocalUser -Name $user -Password $securePassword -AccountNeverExpires | Out-Null
    $created = $true
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user
    & icacls.exe $root /grant "${user}:(OI)(CI)RX" /T /Q | Out-Null
    & icacls.exe $output /grant "${user}:(OI)(CI)M" /T /Q | Out-Null
    $credential = New-Object System.Management.Automation.PSCredential("$env:COMPUTERNAME\$user", $securePassword)
    # The command contains fixed source/output paths, never a password.
    $command = "& '$Python' '$runner' --case-id full-standard --snapshot-id '$snapshot' --output '$output\full-standard'; exit `$LASTEXITCODE"
    $command | Set-Content "$root\standard-capture.ps1" -Encoding UTF8
    $process = Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Credential $credential -LoadUserProfile -WorkingDirectory $root -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',"$root\standard-capture.ps1") -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Standard-user capture exited $($process.ExitCode)." }
} finally {
    if ($created) { Remove-LocalUser -Name $user }
}
& $Python tools/summarize_windows_study.py --input $output --output "$output\summary"
if ($LASTEXITCODE) { throw 'Study summary failed.' }
