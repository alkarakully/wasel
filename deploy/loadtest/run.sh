#!/bin/sh
# Runs one load test and records CPU, memory and database connections every 5 s.
#   RUN=evening PEAK=1500 CAPTAINS=300 STORES=150 TRACKERS=300 MINUTES=1 deploy/loadtest/run.sh
# Results: deploy/loadtest/results/{k6,stats,summary}-$RUN.*
set -u
cd "$(dirname "$0")/../.."
RUN=${RUN:-latest}
OUT=deploy/loadtest/results
COMPOSE="docker compose -f deploy/loadtest/docker-compose.loadtest.yml"
mkdir -p "$OUT"
: > "$OUT/stats-$RUN.txt"
(
  while true; do
    date +%T >> "$OUT/stats-$RUN.txt"
    docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' \
      wasel-loadtest-web-1 wasel-loadtest-db-1 wasel-loadtest-redis-1 wasel-loadtest-worker-1 >> "$OUT/stats-$RUN.txt"
    docker exec wasel-loadtest-db-1 psql -U wasel -d wasel -tAc \
      "select 'db connections ' || count(*) from pg_stat_activity where datname='wasel'" >> "$OUT/stats-$RUN.txt" 2>/dev/null
    sleep 5
  done
) &
STATS=$!
trap 'kill $STATS 2>/dev/null' EXIT
RUN=$RUN $COMPOSE run --rm k6 > "$OUT/k6-$RUN.txt" 2>&1
echo "k6 exit $?"
grep -E "checks|http_req_failed|http_req_duration|kind:|http_reqs|orders_placed|place_order|dispatch_offers|socket_messages|ws_sessions|vus_max|level=error" "$OUT/k6-$RUN.txt"
