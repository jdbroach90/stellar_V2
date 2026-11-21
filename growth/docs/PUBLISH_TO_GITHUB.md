# Publish the completed branch from Windows

The completed review branch is included as `codejet-search-campaign.bundle` in the download. The GitHub connection used during preparation returned **403 — Resource not accessible by integration** when creating the branch. Consequently, this delivery did not create a remote branch or pull request, and did not change `master` or the live website.

The bundle contains the exact reviewed Git history and new commit. Use your existing local GitHub authentication to publish it; no passwords or access tokens belong in a script or this conversation.

## Publish without changing your current working files

Extract the download to `C:\CodeJet\search-release`. That folder should contain `project`, `codejet-search-campaign.bundle`, and `START_HERE.md`. Keep your existing `C:\CodeJet\stellar_V2` checkout in place.

In **PowerShell**, run a dry review first:

```powershell
& 'C:\CodeJet\search-release\project\scripts\publish_search_branch.ps1' -BundlePath 'C:\CodeJet\search-release\codejet-search-campaign.bundle' -RepositoryPath 'C:\CodeJet\stellar_V2' -WhatIf
```

To publish the reviewed feature branch, run the same command without `-WhatIf`:

```powershell
& 'C:\CodeJet\search-release\project\scripts\publish_search_branch.ps1' -BundlePath 'C:\CodeJet\search-release\codejet-search-campaign.bundle' -RepositoryPath 'C:\CodeJet\stellar_V2'
```

The script checks the repository destination, verifies the bundle, checks whether the remote branch exists, imports into a separate ref, pushes only the named feature branch, and verifies the resulting remote commit. It never switches your current branch, overwrites your working files, pushes `master`, force-pushes an existing branch, or merges a PR.

If PowerShell blocks a downloaded script, review it and follow your normal organization/device script policy. Do not weaken a machine-wide execution policy for this package. You can use the equivalent ordinary Git commands below instead.

## Equivalent Git commands

These commands do not check out the new branch or alter your working files. Verify that your existing `origin` repository is `jdbroach90/stellar_V2` before pushing.

```powershell
Set-Location C:\CodeJet\stellar_V2
git bundle verify 'C:\CodeJet\search-release\codejet-search-campaign.bundle'
git fetch 'C:\CodeJet\search-release\codejet-search-campaign.bundle' refs/heads/feature/retail-search-campaign-20261120:refs/codejet-import/retail-search-campaign-20261120
git push origin refs/codejet-import/retail-search-campaign-20261120:refs/heads/feature/retail-search-campaign-20261120
```

Stop if any command fails. Do not add `--force`, reset your checkout, or delete existing work to make it proceed. Normal Git authentication may need to be completed on your own computer.

## Open the draft pull request

After the branch is published, open the repository in GitHub and compare:

- **Base:** `master`
- **Compare:** `feature/retail-search-campaign-20261120`
- **Title:** `Add retail search pages, video funnel, and Google/ChatGPT campaign assets`
- **Description:** copy [PULL_REQUEST.md](PULL_REQUEST.md).

Create it as a draft while reviewing. The included GitHub workflow runs public-site and campaign checks after the branch is pushed, if Actions is enabled. Local checks passed during preparation; no remote Actions result is claimed before publication.

Review the files and checks. Merge when ready for the existing Render deployment. Then follow [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md) for public-host verification, Search Console, and optional paid campaigns.

## Use the files without Git first

The `project` folder is also a complete source checkout without Git internals or credentials. You can run the local Flask preview from that folder using the launch guide. Campaign CSVs, ad review copy, editable JSON, artwork, and the standalone traffic tool are inside `project/growth` and `project/static/images/campaign`.
