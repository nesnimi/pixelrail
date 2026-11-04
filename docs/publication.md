# Public GitHub publication

## Audit result and scope

The preparation scanned the publishable worktree and all reachable blobs in 10
local commits. No credential/private-key patterns or owner absolute home paths
were found. One historic commit email is not a GitHub noreply address: review
author/committer metadata before publishing existing history. Matched values are
never printed by the scanner. Pattern checks do not prove absence of all secrets.

```bash
python scripts/publication_audit.py --history
git log --all --format=fuller           # local inspection; do not paste personal data
git status --short
git diff --check
```

Existing history and uncommitted work have not been rewritten. Local raw design
references/development captures are ignored/excluded, not deleted. Public fixture
screenshots and licenses have been reviewed separately. Before adding new assets,
review their origin/license; never assume that a picture found online is reusable.

## Build a reviewable source artifact

```bash
python scripts/package_release.py
cd .cache/dist
sha256sum -c SHA256SUMS
cd ../..
```

The working tree (including necessary untracked v3.1 sources) is packaged without
Git history, native binaries/build stamps, cache, secrets or private reference art.
Two builds of identical source produce identical hashes. `RELEASE.json` marks
dirty/un-tagged snapshots as candidates. Build native code locally on each target.

## Recommended first public repository: a clean export

This retains the original local repository/history and avoids publishing its old
commit address. The following commands are **for the owner**, and were not run.
Use a new extraction directory; do not overwrite another checkout.

```bash
mkdir -p .cache/publication
tar -xzf .cache/dist/pixelrail-3.1.0-source.tar.gz -C .cache/publication
pixelrail_public="$PWD/.cache/publication/pixelrail-3.1.0"
git -C "$pixelrail_public" init -b main
git -C "$pixelrail_public" config user.name nesnimi
git -C "$pixelrail_public" config user.email 'YOUR_GITHUB_NOREPLY_EMAIL'
git -C "$pixelrail_public" add .
git -C "$pixelrail_public" diff --cached --check
git -C "$pixelrail_public" diff --cached --stat
git -C "$pixelrail_public" diff --cached        # inspect sources and third-party files
# Set the real GitHub-provided noreply address above before continuing.
git -C "$pixelrail_public" commit -m 'Prepare PixelRail v3.1.0'
cd "$pixelrail_public"
python scripts/publication_audit.py --history
gh auth status
gh repo create nesnimi/PixelRail --public --source . --remote origin
git push -u origin main
```

Confirm the authenticated GitHub account owns the intended namespace. These commands
publish only after the owner's review; no force push or local history deletion is
needed. If retaining existing history instead, explicitly approve its identities
and re-audit all refs; do not run reset/clean or automatic history rewriting.

## Draft Release v3.1.0

After physical acceptance, update candidate labels/CHANGELOG date and review tests.
In the public checkout, commit those changes, then:

```bash
git status --short
git diff --check
git add -- README.md README.ru.md CHANGELOG.md docs quickshell
git diff --cached --check
git diff --cached
git commit -m 'Release PixelRail v3.1.0'
git tag -a v3.1.0 -m 'PixelRail v3.1.0'
git push origin main
git push origin v3.1.0
python scripts/package_release.py
gh release create v3.1.0 --draft --verify-tag --title 'PixelRail v3.1.0' \
  --notes-file docs/releases/v3.1.0.md \
  .cache/dist/pixelrail-3.1.0-source.tar.gz .cache/dist/SHA256SUMS
```

Review the draft and [second-machine checklist](second-computer-checklist.md) before
publishing. See the official [repo create](https://cli.github.com/manual/gh_repo_create)
and [release create](https://cli.github.com/manual/gh_release_create) options.
No automatic repository creation, login, commit, tag, push or GitHub release occurs.
