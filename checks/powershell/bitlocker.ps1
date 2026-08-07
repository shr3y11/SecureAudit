#Requires -Version 5.1

<#
.SYNOPSIS
    Assesses BitLocker protection on the Windows operating-system drive.

.DESCRIPTION
    SecureAudit approved scanner module for check WIN-BL-001.

    The script identifies the operating-system drive using $env:SystemDrive,
    queries BitLocker status using Get-BitLockerVolume, and returns one
    structured JSON object.

    This script does not enable, disable, suspend, or modify BitLocker.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$checkId = "WIN-BL-001"
$checkName = "BitLocker Protection Active"
$expectedValue = "BitLocker protection is active on the operating-system drive"

function Write-AssessmentResult {
    param(
        [Parameter(Mandatory)]
        [ValidateSet("Pass", "Fail", "Error")]
        [string]$Status,

        [Parameter(Mandatory)]
        [string]$ObservedValue,

        [Parameter(Mandatory)]
        [array]$Evidence,

        [AllowNull()]
        [string]$ErrorMessage
    )

    $result = [ordered]@{
        check_id       = $checkId
        check_name     = $checkName
        expected_value = $expectedValue
        observed_value = $ObservedValue
        status          = $Status
        evidence        = $Evidence
        error_message   = $ErrorMessage
        timestamp_utc   = [DateTime]::UtcNow.ToString("o")
    }

    $result | ConvertTo-Json -Depth 6 -Compress
}

try {
    $bitLockerCommand = Get-Command `
        -Name "Get-BitLockerVolume" `
        -ErrorAction SilentlyContinue

    if ($null -eq $bitLockerCommand) {
        throw "Get-BitLockerVolume is unavailable on this system."
    }

    if ([string]::IsNullOrWhiteSpace($env:SystemDrive)) {
        throw "The Windows operating-system drive could not be determined."
    }

    $systemDrive = $env:SystemDrive.TrimEnd("\")

    $volume = Get-BitLockerVolume `
        -MountPoint $systemDrive `
        -ErrorAction Stop

    if ($null -eq $volume) {
        throw "No BitLocker volume information was returned for $systemDrive."
    }

    $volumeStatus = [string]$volume.VolumeStatus
    $protectionStatus = [string]$volume.ProtectionStatus
    $encryptionPercentage = [int]$volume.EncryptionPercentage
    $encryptionMethod = [string]$volume.EncryptionMethod
    $volumeType = [string]$volume.VolumeType
    $lockStatus = [string]$volume.LockStatus

    $keyProtectorTypes = @(
        foreach ($protector in @($volume.KeyProtector)) {
            if ($null -ne $protector) {
                [string]$protector.KeyProtectorType
            }
        }
    )

    $evidence = @(
        [ordered]@{
            mount_point          = $systemDrive
            volume_type          = $volumeType
            volume_status        = $volumeStatus
            protection_status    = $protectionStatus
            encryption_percentage = $encryptionPercentage
            encryption_method    = $encryptionMethod
            lock_status          = $lockStatus
            key_protector_types  = $keyProtectorTypes
        }
    )

    $observedValue = (
        "MountPoint={0}, VolumeStatus={1}, ProtectionStatus={2}, " +
        "EncryptionPercentage={3}, EncryptionMethod={4}"
    ) -f `
        $systemDrive,
        $volumeStatus,
        $protectionStatus,
        $encryptionPercentage,
        $encryptionMethod

    $isFullyEncrypted = (
        $volumeStatus -eq "FullyEncrypted" -and
        $encryptionPercentage -eq 100
    )

    $isProtectionEnabled = (
        $protectionStatus -eq "On"
    )

    if ($isFullyEncrypted -and $isProtectionEnabled) {
        Write-AssessmentResult `
            -Status "Pass" `
            -ObservedValue $observedValue `
            -Evidence $evidence `
            -ErrorMessage $null
    }
    else {
        Write-AssessmentResult `
            -Status "Fail" `
            -ObservedValue $observedValue `
            -Evidence $evidence `
            -ErrorMessage $null
    }
}
catch {
    $errorEvidence = @(
        [ordered]@{
            error_type = $_.Exception.GetType().FullName
        }
    )

    Write-AssessmentResult `
        -Status "Error" `
        -ObservedValue "BitLocker status could not be assessed" `
        -Evidence $errorEvidence `
        -ErrorMessage $_.Exception.Message
}