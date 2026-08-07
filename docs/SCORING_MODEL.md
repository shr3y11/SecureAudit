# Scoring Model

## Goal

SecureAudit separates **compliance score** from **assessment coverage** so that unassessed controls do not silently distort the result.

## Status Model

```text
Pass
Fail
Error
```

Where:

```text
Pass  = assessed and expected condition met
Fail  = assessed and expected condition not met
Error = reliable assessment unavailable
```

## Assessed Checks

```text
Assessed = Pass + Fail
```

Errors are unassessed.

## Compliance Score

```text
Compliance Score =
Passed / Assessed × 100
```

If `Assessed = 0`, the score is:

```text
Not available
```

rather than `0%`.

A zero score would incorrectly imply that actual assessed controls failed.

## Assessment Coverage

```text
Assessment Coverage =
Assessed / Selected × 100
```

Coverage answers:

> How much of the selected scope was assessed successfully?

## Example

```text
Selected: 5
Pass:     3
Fail:     1
Error:    1
```

Then:

```text
Assessed = 4
Compliance score = 3 / 4 × 100 = 75%
Coverage = 4 / 5 × 100 = 80%
```

## Why Score and Coverage Must Be Separate

Example:

```text
Selected: 5
Pass:     1
Fail:     0
Error:    4
```

Results:

```text
Compliance score: 100%
Coverage:          20%
```

Displaying only `100%` would be misleading. Coverage exposes the incomplete assessment.

## Scope of the Score

The score means:

> Percentage of successfully assessed selected technical checks that passed.

It does not mean:

- complete CIS compliance
- overall security maturity
- ISO 27001 certification readiness
- NIST CSF certification
- audit certification
