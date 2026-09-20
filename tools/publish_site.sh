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
WT=$(mktemp -d)
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
git worktree remove --force "$WT"
echo "published; the site is at the custom domain once DNS and the Pages setting are in place"
