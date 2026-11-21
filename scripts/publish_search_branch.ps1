#Requires -Version 5.1
<#
Publish the supplied review branch using the existing checkout's Git authentication.
Does not switch branches, change working files, push master, merge, or deploy.
Use -WhatIf to review without importing or pushing.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$BundlePath,
    [string]$RepositoryPath = 'C:\CodeJet\stellar_V2'
)
$ErrorActionPreference = 'Stop'
$branchName = 'feature/retail-search-campaign-20261120'
$importRef = 'refs/codejet-import/retail-search-campaign-20261120'
$repositoryName = 'jdbroach90/stellar_V2'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required.' }
$bundleFile = (Resolve-Path -LiteralPath $BundlePath).Path
$repositoryFolder = (Resolve-Path -LiteralPath $RepositoryPath).Path
if (-not (Test-Path -LiteralPath $bundleFile -PathType Leaf)) { throw 'The bundle path must be a file.' }
$remoteUrl = & git -C $repositoryFolder remote get-url origin
if ($LASTEXITCODE -ne 0) { throw 'Could not read origin from the selected checkout.' }
if ($remoteUrl -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)jdbroach90/stellar_V2(?:\.git)?/?$') {
    throw 'The selected checkout must have origin set to jdbroach90/stellar_V2. No remote was changed.'
}
& git -C $repositoryFolder bundle verify $bundleFile
if ($LASTEXITCODE -ne 0) { throw 'Git could not verify the bundle. Nothing was pushed.' }
$heads = @(& git -C $repositoryFolder bundle list-heads $bundleFile ('refs/heads/' + $branchName))
if ($LASTEXITCODE -ne 0 -or $heads.Count -ne 1) { throw 'The expected review branch is missing or ambiguous.' }
$branchPattern = '^([0-9a-f]{40}) refs/heads/' + [regex]::Escape($branchName) + '$'
$branchMatch = [regex]::Match($heads[0], $branchPattern)
if (-not $branchMatch.Success) { throw 'Unexpected bundle branch format.' }
$reviewCommit = $branchMatch.Groups[1].Value
Write-Host ('Repository: ' + $repositoryName)
Write-Host ('Review branch: ' + $branchName)
Write-Host ('Commit: ' + $reviewCommit)
Write-Host 'Your current branch and working files will stay as they are.'
if (-not $PSCmdlet.ShouldProcess(($repositoryName + ':' + $branchName), 'Publish the reviewed CodeJet search branch')) { return }
$existing = @(& git -C $repositoryFolder ls-remote --heads origin ('refs/heads/' + $branchName))
if ($LASTEXITCODE -ne 0) { throw 'Git could not access origin. Complete your normal GitHub sign-in locally, then rerun.' }
if ($existing.Count -gt 0) {
    $existingCommit = ($existing[0] -split '\s+')[0]
    if ($existingCommit -ne $reviewCommit) { throw 'A different commit already exists on this branch. Inspect it; no force push was attempted.' }
    Write-Host 'This exact review commit is already on GitHub.'
} else {
    & git -C $repositoryFolder fetch $bundleFile (('refs/heads/' + $branchName) + ':' + $importRef)
    if ($LASTEXITCODE -ne 0) { throw 'Could not import the bundle into its separate local ref. Nothing was pushed.' }
    $importedCommit = & git -C $repositoryFolder rev-parse $importRef
    if ($LASTEXITCODE -ne 0 -or $importedCommit -ne $reviewCommit) { throw 'Imported commit did not match the reviewed bundle.' }
    & git -C $repositoryFolder push origin ($importRef + ':refs/heads/' + $branchName)
    if ($LASTEXITCODE -ne 0) { throw 'GitHub did not accept the review branch. No production branch or working files were changed.' }
    $published = @(& git -C $repositoryFolder ls-remote --heads origin ('refs/heads/' + $branchName))
    if ($LASTEXITCODE -ne 0 -or $published.Count -ne 1 -or ($published[0] -split '\s+')[0] -ne $reviewCommit) {
        throw 'Push completed but the remote commit could not be verified. Check the branch in GitHub before retrying.'
    }
    Write-Host 'Published and verified the review branch.'
}
Write-Host ''
Write-Host 'Create a draft PR with base master and this review branch. Use growth/docs/PULL_REQUEST.md for its description.'
Write-Host ('https://github.com/' + $repositoryName + '/compare/master...' + $branchName + '?expand=1')
Write-Host 'Merging into the Render-linked production branch is the separate website release step.'
