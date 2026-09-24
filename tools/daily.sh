#!/bin/sh
# The daily run: pull every source, apply the rules, build today's issue and
# render the site. Publishing stays a separate step so the issue can be read
# first:   tools/daily.sh            build only
#          tools/daily.sh --publish  build and push the site to GitHub Pages
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
echo "== $(date '+%F %T') fetch"
$PY -m arbradar.cli fetch --days 3 --source rss,edgar,courtlistener,icsid,pca,pca_cases,gnews,tenders,courts 2>&1 | grep -v "^INFO" || true
# What this machine could not reach may have been relayed from one that could.
$PY -m arbradar.cli import --file data/relay.jsonl 2>&1 | grep -v "^INFO" || true
echo "== $(date '+%F %T') classify and build"
$PY -m arbradar.cli reclassify --days 7 2>&1 | grep -v "^INFO" || true
$PY -m arbradar.cli build --days 2 2>&1 | grep -v "^INFO"
$PY -m arbradar.cli articles 2>&1 | grep -v "^INFO"
if [ "$1" = "--publish" ]; then
  echo "== $(date '+%F %T') publish"
  tools/publish_site.sh origin 2>&1 | grep -v "^INFO"
fi
echo "== $(date '+%F %T') done"
