#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Corvids Nest server to Linux garage server
.DESCRIPTION
    This script commits changes and pushes to the production server,
    triggering automatic deployment via Git post-receive hook.
.PARAMETER CommitMessage
    Commit message for the deployment
.PARAMETER SkipCommit
    Skip git commit, just push existing commits
.PARAMETER Remote
    Git remote name (default: production)
.PARAMETER Branch
    Git branch to push (default: main)
.PARAMETER Force
    Force push (use with caution!)
.EXAMPLE
    .\deploy.ps1
    .\deploy.ps1 -CommitMessage "Updated API endpoints"
    .\deploy.ps1 -SkipCommit
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$CommitMessage = "Deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",

    [Parameter(Mandatory=$false)]
    [switch]$SkipCommit,

    [Parameter(Mandatory=$false)]
    [string]$Remote = "production",

    [Parameter(Mandatory=$false)]
    [string]$Branch = "main",

    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Color output functions
function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [Parameter(Mandatory=$false)]
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { param([string]$Message) Write-ColorOutput $Message "Green" }
function Write-Info { param([string]$Message) Write-ColorOutput $Message "Cyan" }
function Write-Warning { param([string]$Message) Write-ColorOutput $Message "Yellow" }
function Write-Error { param([string]$Message) Write-ColorOutput $Message "Red" }

# Check if we're in the right directory
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$currentDir = Get-Location

if ($currentDir.Path -ne $repoRoot) {
    Write-Info "Changing to repository root: $repoRoot"
    Set-Location $repoRoot
}

# Check if Git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not in PATH"
    exit 1
}

# Check if remote exists
$remoteExists = git remote | Select-String -Pattern "^$Remote$" -Quiet
if (-not $remoteExists) {
    Write-Error "Git remote '$Remote' not found!"
    Write-Info "Available remotes:"
    git remote -v
    Write-Info "`nAdd production remote with:"
    Write-Info "git remote add production justin@<server-ip>:/opt/corvids-nest/.git"
    exit 1
}

Write-Info "═══════════════════════════════════════════"
Write-Info "  Corvids Nest Server Deployment"
Write-Info "═══════════════════════════════════════════"
Write-Info ""

# Show current branch
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Info "Current branch: $currentBranch"
Write-Info "Target remote: $Remote"
Write-Info "Target branch: $Branch"
Write-Info ""

# Check for uncommitted changes
$status = git status --porcelain
if ($status -and -not $SkipCommit) {
    Write-Info "Uncommitted changes detected:"
    git status --short
    Write-Info ""

    $response = Read-Host "Commit these changes? (Y/n)"
    if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
        Write-Info "Staging all changes..."
        git add .

        Write-Info "Committing with message: $CommitMessage"
        git commit -m $CommitMessage

        if ($LASTEXITCODE -ne 0) {
            Write-Error "Git commit failed!"
            exit 1
        }
        Write-Success "Changes committed"
    } else {
        Write-Warning "Deployment cancelled - uncommitted changes remain"
        exit 0
    }
} elseif ($SkipCommit) {
    Write-Info "Skipping commit (SkipCommit flag set)"
} else {
    Write-Info "No uncommitted changes"
}

Write-Info ""

# Show what will be pushed
Write-Info "Recent commits to be pushed:"
$commits = git log $Remote/$Branch..$currentBranch --oneline --decorate -5 2>$null
if ($commits) {
    $commits | ForEach-Object { Write-Info "  $_" }
} else {
    Write-Info "  No new commits (already up to date)"
}
Write-Info ""

# Confirm deployment
$response = Read-Host "Deploy to $Remote/$Branch? (Y/n)"
if ($response -ne "" -and $response -ne "Y" -and $response -ne "y") {
    Write-Warning "Deployment cancelled"
    exit 0
}

Write-Info ""
Write-Info "═══════════════════════════════════════════"
Write-Info "  Pushing to production server..."
Write-Info "═══════════════════════════════════════════"
Write-Info ""

# Push to production
$pushArgs = @("push")
if ($Force) {
    $pushArgs += "--force"
    Write-Warning "Force push enabled!"
}
$pushArgs += @($Remote, "$($currentBranch):$Branch")

& git @pushArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed!"
    exit 1
}

Write-Info ""
Write-Success "═══════════════════════════════════════════"
Write-Success "  Deployment successful!"
Write-Success "═══════════════════════════════════════════"
Write-Info ""
Write-Info "The post-receive hook on the server is now:"
Write-Info "  1. Updating code"
Write-Info "  2. Rebuilding Docker containers"
Write-Info "  3. Restarting services"
Write-Info ""
Write-Info "Useful commands:"
Write-Info "  View logs:    ssh justin@<server> 'cd /opt/corvids-nest/server && docker compose logs -f'"
Write-Info "  Check status: ssh justin@<server> 'cd /opt/corvids-nest/server && docker compose ps'"
Write-Info "  API health:   curl http://<server>:8000/health"
Write-Info ""
Write-Success "Deployment complete!"
