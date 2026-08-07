# Git Workflow

## Branch Model

```text
main
  ↑
develop
  ↑
feature / docs branches
```

`main` contains release-ready code.

`develop` is the integration branch.

Feature work is performed on focused branches.

## SecureAudit MVP Flow

The Windows MVP progressed through branches such as:

```text
feature/windows-mvp
        ↓ PR
develop
        ↓
feature/tkinter-gui
        ↓ PR
develop
        ↓
feature/admin-elevation
        ↓ PR
develop
        ↓
feature/windows-build
        ↓ PR
develop
        ↓
docs/project-documentation
        ↓ PR
develop
        ↓ final release PR
main
```

## Protected Branches

`develop` is protected.

Direct pushes are rejected and changes must be merged through Pull Requests.

The repository also rejects merge commits on the protected branch, so use the merge method allowed by the repository, such as squash or rebase.

## Start New Work

```powershell
git switch develop
git pull origin develop
git switch -c feature/example
git push -u origin feature/example
```

## Review Before Commit

```powershell
git status --short
git diff
git diff --check
```

Stage only intended files:

```powershell
git add .\path\to\file
```

Then:

```powershell
git diff --cached --check
git diff --cached --stat
git status
```

## Commit Style

```text
type(scope): description
```

Examples:

```text
feat(scanner): add SMBv1 assessment
feat(scoring): calculate compliance score and coverage
feat(storage): store scan history in SQLite
feat(ui): add catalog-driven compliance checklist
feat(admin): request Windows UAC elevation
build(windows): package SecureAudit with PyInstaller
docs(architecture): document SecureAudit MVP
```

## Push

First push:

```powershell
git push -u origin <branch>
```

Later:

```powershell
git push
```

## Merge

Open a Pull Request:

```text
feature branch → develop
```

For final release:

```text
develop → main
```

## Delete Completed Branches

After successful merge:

```powershell
git branch -d feature/example
git push origin --delete feature/example
```
