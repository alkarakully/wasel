# Load test

A production-like copy of Wasel squeezed onto **4 CPU cores**, and a [k6](https://k6.io) script that plays a busy evening against it. Use it to see how many people one server can take, and to check that a change didn't make Wasel slower.

The copy has its own database (project `wasel-loadtest`), separate from development's.

## Run it

From the repository root:

```bash
docker compose -f deploy/loadtest/docker-compose.loadtest.yml up -d --build --force-recreate
RUN=evening PEAK=1000 CAPTAINS=300 STORES=150 TRACKERS=300 MINUTES=1 deploy/loadtest/run.sh
```

`up` builds the production image, migrates, and runs `manage.py seed_loadtest`. That makes 200 open stores with menus around Karrada, 3,000 customers, 500 captains and the store owners, all already signed in. Every `up` resets the test data.

`run.sh` runs k6 and samples CPU, memory and database connections every 5 seconds. Results go to `deploy/loadtest/results/` (git-ignored): `k6-$RUN.txt` (the k6 summary), `summary-$RUN.json` and `stats-$RUN.txt`.

Stop it with `docker compose -f deploy/loadtest/docker-compose.loadtest.yml down -v`.

## What the script does

| Who | How many | What they do |
| :--- | :--- | :--- |
| Customers | Ramp to `PEAK` in four steps, then hold | Open the home screen (stores near them, banners, offers), sometimes search, open a store, get a quote, and about 1 in 6 place a cash order. They pause 2 to 15 s between steps, like people. |
| Trackers | `TRACKERS` | Customers with the app open on their orders: a live socket, and a reload every 30 s. |
| Captains | `CAPTAINS` | Online, send GPS every 3 s over the live socket, take 7 in 10 offers (declining the rest), and pick the order up once it's ready. A delivery needs the customer's PIN, which only their app sees, so each captain stays on their first order: by the end, fewer captains are free than in real life. |
| Store tablets | `STORES` | A live socket, a board reload every 10 s, accepting new orders and marking some ready. |

Each step lasts `MINUTES`, so a run takes about `5 × MINUTES` minutes.

It passes when fewer than 1% of requests fail, browsing answers within 800 ms for 95% of requests, and ordering within 1.5 s.

## Notes

- The Wasel containers share CPUs 0–3 (`cpuset`), like one 4-core server. k6 runs on the other cores.
- On a Mac, Docker's memory limit (Docker Desktop › Settings › Resources) caps what the copy can use. PostgreSQL is sized down to match: about 3 GB for the database and 3 GB for the web processes. `deploy/docker-compose.prod.yml` sizes it for 16 GB.
- nginx and HTTPS are left out. In production nginx adds a little CPU for TLS and serves photos; k6 sends `X-Forwarded-Proto: https` the way nginx does.
- `WEB_CONCURRENCY` sets the number of web processes (default 8) and `DB_POOL_SIZE` the database connections per web process (default 10).
- PostgreSQL's query statistics (`pg_stat_statements`, with planning time) are on in this copy. See the costliest queries with:

  ```bash
  docker exec wasel-loadtest-db-1 psql -U wasel -d wasel -c "select calls, round(mean_plan_time::numeric,2) plan_ms, round(mean_exec_time::numeric,2) exec_ms, left(query, 100) from pg_stat_statements order by total_plan_time + total_exec_time desc limit 10"
  ```

## Results (November 2026, 4 cores on an Apple Silicon Mac, about 6 GB for Wasel)

| Customers browsing at peak | Also online | Browse p50 / p95 | Order p50 / p95 | Failed | CPU at peak |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 750 | 250 tracking, 400 captains, 150 stores | 15 ms / 482 ms | 23 ms / 635 ms | 0.10% | ≈ 3.3 of 4 cores |
| 1,000 | 300 tracking, 500 captains, 150 stores | 45 ms / 1.1 s | 67 ms / 1.2 s | 0.03% | all 4 cores |

Before today's tuning the same 1,000-customer test answered in 586 ms / 2.15 s (p50 / p95). Before the connection pool, most requests failed as the database ran out of connections.

The failures that remain are expected answers, not server errors: a delivery spot outside a store's area, or an offer another captain took first. Cloud vCPUs are usually slower per core than this Mac, and nginx with TLS adds some work, so expect somewhat less on a real 4-core server.
