#Requires -Version 5.1
# Read-only reference capture. Review raw values against the documented
# objective and a second interface before treating them as ground truth.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Read-Reference([scriptblock]$Command) {
    try { return @{ ok = $true; values = @(& $Command); error = $null } }
    catch { return @{ ok = $false; values = @(); error = $_.Exception.Message } }
}
$reference = [ordered]@{
    captured_at_utc = [DateTime]::UtcNow.ToString('o')
    is_administrator = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    powershell_version = $PSVersionTable.PSVersion.ToString()
    os = Read-Reference { Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber }
    firewall = Read-Reference { Get-NetFirewallProfile | Select-Object Name, Enabled }
    defender = Read-Reference { Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, RealTimeProtectionEnabled }
    bitlocker = Read-Reference { Get-BitLockerVolume -MountPoint $env:SystemDrive | Select-Object MountPoint, ProtectionStatus, VolumeStatus }
    guest = Read-Reference { Get-LocalUser | Where-Object { $_.SID.Value -match '-501$' } | Select-Object Name, Enabled, SID }
    smbv1 = Read-Reference { Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol | Select-Object FeatureName, State }
}
$reference | ConvertTo-Json -Depth 8 -Compress
