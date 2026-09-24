#!/bin/sh
# Relay the sources GitHub's runners are refused by (pca-cpa.org and a few court
# sites answer 403 to datacenter addresses) from a machine that can read them.
# Runs the adapters here, writes the items to the `relay` branch, and the cloud
# run imports them before it builds. Schedule it before the cloud run:
#   launchctl load tools/com.caselens.arbradar-relay.plist   (20:30 local, daily)
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
mkdir -p out
echo "== $(date '+%F %T') relay fetch"
$PY -m arbradar.cli export --days "${1:-7}" --out out/relay.jsonl 2>&1 | grep -v "^INFO" || true
[ -s out/relay.jsonl ] || { echo "nothing to relay"; exit 0; }
# The local database gets the same items, so a laptop build and the cloud agree.
$PY -m arbradar.cli import --file out/relay.jsonl 2>&1 | grep -v "^INFO" || true
WT=$(mktemp -d)
git worktree prune
git show-ref --quiet refs/heads/relay && git branch -q -D relay
git worktree add --detach "$WT" >/dev/null
(cd "$WT" && git checkout -q --orphan relay && (git rm -rfq . >/dev/null 2>&1 || true) \
  && cp "$OLDPWD/out/relay.jsonl" relay.jsonl && git add relay.jsonl \
  && git -c user.name="arbradar-relay" -c user.email="arbradar@caselens.tech" commit -qm "Relay from $(hostname -s) $(date +%F)" \
  && git push -f origin relay)
git worktree remove --force "$WT"
echo "== $(date '+%F %T') relayed $(wc -l < out/relay.jsonl | tr -d ' ') items"
