#Requires -Version 5.1

<#
.SYNOPSIS
    Assesses whether the SMBv1 Windows optional feature is disabled.

.DESCRIPTION
    SecureAudit approved scanner module for check WIN-SMB1-001.

    The script queries the SMB1Protocol Windows optional feature and reports
    Pass when SMBv1 is disabled or its payload has been removed, Fail when it
    is enabled, and Error when its state cannot be assessed reliably.

    This script does not enable, disable, install, or remove Windows features.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$checkId = "WIN-SMB1-001"
$checkName = "SMBv1 Disabled"
$expectedValue = "SMBv1 is disabled"

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
    $optionalFeatureCommand = Get-Command `
        -Name "Get-WindowsOptionalFeature" `
        -ErrorAction SilentlyContinue

    if ($null -eq $optionalFeatureCommand) {
        throw "Get-WindowsOptionalFeature is unavailable on this system."
    }

    $feature = Get-WindowsOptionalFeature `
        -Online `
        -FeatureName "SMB1Protocol" `
        -ErrorAction Stop

    if ($null -eq $feature) {
        throw "No SMB1Protocol optional-feature information was returned."
    }

    $featureName = [string]$feature.FeatureName
    $featureState = [string]$feature.State

    if ([string]::IsNullOrWhiteSpace($featureState)) {
        throw "The SMB1Protocol feature returned an empty state."
    }

    $evidence = @(
        [ordered]@{
            feature_name = $featureName
            feature_state = $featureState
            restart_needed = [string]$feature.RestartNeeded
            custom_properties = @(
                foreach ($property in @($feature.CustomProperties)) {
                    if ($null -ne $property) {
                        [string]$property
                    }
                }
            )
        }
    )

    $observedValue = (
        "FeatureName={0}, State={1}, RestartNeeded={2}"
    ) -f `
        $featureName,
        $featureState,
        $feature.RestartNeeded

    $disabledStates = @(
        "Disabled",
        "DisabledWithPayloadRemoved"
    )

    if ($featureState -eq "Enabled") {
        Write-AssessmentResult `
            -Status "Fail" `
            -ObservedValue $observedValue `
            -Evidence $evidence `
            -ErrorMessage $null
    }
    elseif ($featureState -in $disabledStates) {
        Write-AssessmentResult `
            -Status "Pass" `
            -ObservedValue $observedValue `
            -Evidence $evidence `
            -ErrorMessage $null
    }
    else {
        throw (
            "SMB1Protocol returned an unsupported or transitional state: " +
            $featureState
        )
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
        -ObservedValue "SMBv1 status could not be assessed" `
        -Evidence $errorEvidence `
        -ErrorMessage $_.Exception.Message
}