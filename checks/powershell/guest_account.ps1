#Requires -Version 5.1

<#
.SYNOPSIS
    Assesses whether the built-in Windows Guest account is disabled.

.DESCRIPTION
    SecureAudit approved scanner module for check WIN-GUEST-001.

    The script locates the built-in Guest account using its well-known RID 501
    rather than relying only on the account name. It returns one JSON object.

    This script does not modify local accounts.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$checkId = "WIN-GUEST-001"
$checkName = "Guest Account Disabled"
$expectedValue = "The built-in Guest account is disabled"

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
    $localUserCommand = Get-Command `
        -Name "Get-LocalUser" `
        -ErrorAction SilentlyContinue

    if ($null -eq $localUserCommand) {
        throw "Get-LocalUser is unavailable on this system."
    }

    $guestAccount = @(
        Get-LocalUser -ErrorAction Stop |
        Where-Object {
            $_.SID.Value -match "-501$"
        }
    )

    if ($guestAccount.Count -eq 0) {
        throw "The built-in Guest account could not be located."
    }

    if ($guestAccount.Count -gt 1) {
        throw "Multiple local accounts matched the built-in Guest account RID."
    }

    $account = $guestAccount[0]

    $accountEnabled = [bool]$account.Enabled
    $accountDisabled = -not $accountEnabled

    $evidence = @(
        [ordered]@{
            account_name     = [string]$account.Name
            sid              = [string]$account.SID.Value
            enabled          = $accountEnabled
            principal_source = [string]$account.PrincipalSource
            last_logon       = if ($null -eq $account.LastLogon) {
                $null
            }
            else {
                ([DateTime]$account.LastLogon).ToUniversalTime().ToString("o")
            }
        }
    )

    $observedValue = (
        "AccountName={0}, SID={1}, Enabled={2}"
    ) -f `
        $account.Name,
        $account.SID.Value,
        $accountEnabled

    if ($accountDisabled) {
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
        -ObservedValue "Guest account status could not be assessed" `
        -Evidence $errorEvidence `
        -ErrorMessage $_.Exception.Message
}