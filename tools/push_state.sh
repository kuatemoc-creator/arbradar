#!/bin/sh
# Push this machine's database to the `state` branch, which the cloud run restores
# from before every build. Use it to seed the cloud with a laptop's history.
set -e
cd "$(dirname "$0")/.."
DB="$(pwd)/data/arbradar.sqlite3"
WT=$(mktemp -d)
git worktree prune
git show-ref --quiet refs/heads/state && git branch -q -D state      # the orphan branch is rebuilt every time
git worktree add --detach "$WT" >/dev/null
(cd "$WT" && git checkout -q --orphan state && (git rm -rfq . >/dev/null 2>&1 || true) && cp "$DB" arbradar.sqlite3 && git add arbradar.sqlite3 && git commit -qm "State from $(hostname -s) $(date +%F)" && git push -f origin state)
git worktree remove --force "$WT"
echo "state branch now carries $(du -h "$DB" | cut -f1) of history"
