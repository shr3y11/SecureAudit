#Requires -Version 5.1

<#
.SYNOPSIS
    Assesses whether Microsoft Defender Antivirus is active.

.DESCRIPTION
    SecureAudit approved scanner module for check WIN-DEF-001.

    The script queries Microsoft Defender status using Get-MpComputerStatus.
    It returns exactly one JSON object with Pass, Fail, or Error status.

    This script does not modify Defender settings.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$checkId = "WIN-DEF-001"
$checkName = "Microsoft Defender Antivirus Active"
$expectedValue = "Microsoft Defender Antivirus protection is enabled"

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

    $result | ConvertTo-Json -Depth 5 -Compress
}

try {
    $defenderCommand = Get-Command `
        -Name "Get-MpComputerStatus" `
        -ErrorAction SilentlyContinue

    if ($null -eq $defenderCommand) {
        throw "Get-MpComputerStatus is unavailable on this system."
    }

    $status = Get-MpComputerStatus -ErrorAction Stop

    $antivirusEnabled = [bool]$status.AntivirusEnabled
    $antispywareEnabled = [bool]$status.AntispywareEnabled
    $realTimeProtectionEnabled = [bool]$status.RealTimeProtectionEnabled
    $behaviorMonitorEnabled = [bool]$status.BehaviorMonitorEnabled

    $evidence = @(
        [ordered]@{
            setting = "AntivirusEnabled"
            enabled = $antivirusEnabled
        },
        [ordered]@{
            setting = "AntispywareEnabled"
            enabled = $antispywareEnabled
        },
        [ordered]@{
            setting = "RealTimeProtectionEnabled"
            enabled = $realTimeProtectionEnabled
        },
        [ordered]@{
            setting = "BehaviorMonitorEnabled"
            enabled = $behaviorMonitorEnabled
        }
    )

    $observedValue = (
        "AntivirusEnabled={0}, AntispywareEnabled={1}, " +
        "RealTimeProtectionEnabled={2}, BehaviorMonitorEnabled={3}"
    ) -f `
        $antivirusEnabled,
        $antispywareEnabled,
        $realTimeProtectionEnabled,
        $behaviorMonitorEnabled

    $requiredProtectionEnabled = (
        $antivirusEnabled -and
        $antispywareEnabled
    )

    if ($requiredProtectionEnabled) {
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
        -ObservedValue "Microsoft Defender status could not be assessed" `
        -Evidence $errorEvidence `
        -ErrorMessage $_.Exception.Message
}