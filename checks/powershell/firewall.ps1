#Requires -Version 5.1

<#
.SYNOPSIS
    Assesses whether the Windows Firewall profiles are enabled.

.DESCRIPTION
    SecureAudit approved scanner module for check WIN-FW-001.

    The script queries the effective Domain, Private, and Public Windows
    Firewall profiles from the ActiveStore. It returns exactly one JSON
    object describing a Pass, Fail, or Error assessment.

    This script does not modify firewall settings.

.OUTPUTS
    A single JSON object written to standard output.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$checkId = "WIN-FW-001"
$checkName = "Windows Firewall Enabled"
$expectedValue = "All applicable Windows Firewall profiles are enabled"

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
    Import-Module NetSecurity -ErrorAction Stop

    $requiredProfileNames = @(
        "Domain",
        "Private",
        "Public"
    )

    $profiles = @(
        Get-NetFirewallProfile `
            -PolicyStore ActiveStore `
            -ErrorAction Stop |
            Where-Object {
                $_.Name -in $requiredProfileNames
            }
    )

    if ($profiles.Count -eq 0) {
        throw "No Windows Firewall profiles were returned from the ActiveStore."
    }

    $evidence = @(
        foreach ($profileName in $requiredProfileNames) {
            $profile = $profiles |
                Where-Object Name -eq $profileName |
                Select-Object -First 1

            if ($null -eq $profile) {
                [ordered]@{
                    profile = $profileName
                    enabled = $null
                    found   = $false
                }
            }
            else {
                [ordered]@{
                    profile = $profileName
                    enabled = [bool]$profile.Enabled
                    found   = $true
                }
            }
        }
    )

    $missingProfiles = @(
        $evidence | Where-Object { -not $_.found }
    )

    if ($missingProfiles.Count -gt 0) {
        $missingNames = (
            $missingProfiles |
            ForEach-Object { $_.profile }
        ) -join ", "

        throw "Required Windows Firewall profiles were not returned: $missingNames."
    }

    $disabledProfiles = @(
        $evidence | Where-Object { -not $_.enabled }
    )

    $observedParts = foreach ($item in $evidence) {
        "$($item.profile)=$($item.enabled)"
    }

    $observedValue = $observedParts -join ", "

    if ($disabledProfiles.Count -eq 0) {
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
        -ObservedValue "Firewall configuration could not be assessed" `
        -Evidence $errorEvidence `
        -ErrorMessage $_.Exception.Message
}