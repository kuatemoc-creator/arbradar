#!/bin/sh
# Publish out/site to the gh-pages branch of a GitHub remote, for GitHub Pages.
#   tools/publish_site.sh [remote]      (default remote: origin)
# One-time setup on GitHub: Settings -> Pages -> Source: "Deploy from a branch",
# branch gh-pages, folder /(root); Custom domain: the host in config.yaml site_url.
# DNS: a CNAME record for that host pointing at <github-user>.github.io.
set -e
cd "$(dirname "$0")/.."
REMOTE=${1:-origin}
git remote get-url "$REMOTE" >/dev/null 2>&1 || { echo "no git remote '$REMOTE'; add one first: git remote add origin git@github.com:<user>/arb-radar.git"; exit 1; }
.venv/bin/python -m arbradar.cli articles
# The cloud run publishes too: start from the remote tip so histories never diverge.
if git fetch -q "$REMOTE" gh-pages 2>/dev/null; then
  git branch -f gh-pages "$REMOTE/gh-pages" 2>/dev/null || true
fi
WT=$(mktemp -d)
trap 'git worktree remove --force "$WT" 2>/dev/null; git worktree prune' EXIT   # never leave a stale checkout behind
if ! git show-ref --quiet refs/heads/gh-pages && git show-ref --quiet "refs/remotes/$REMOTE/gh-pages"; then
  git branch gh-pages "$REMOTE/gh-pages"        # a fresh clone: continue the published history
fi
if git show-ref --quiet refs/heads/gh-pages; then
  git worktree add "$WT" gh-pages >/dev/null
else
  git worktree add --detach "$WT" >/dev/null
  (cd "$WT" && git checkout --orphan gh-pages >/dev/null && git rm -rfq . >/dev/null 2>&1 || true)
fi
rsync -a --delete --exclude .git out/site/ "$WT"/
touch "$WT/.nojekyll"
(cd "$WT" && git add -A && (git commit -qm "Publish site $(date +%F)" || true))
git push -u "$REMOTE" gh-pages
echo "published; the site is at the custom domain once DNS and the Pages setting are in place"
