# Sharing Delivery Atlas on Vercel

**Published:** https://delivery-atlas-demo.vercel.app. Latest verification on 19
October: [stability evidence](evidencia-estabilidad.json). The local and public
routes passed all 23 HTTP checks. A 200-customer / 80-courier run served eight
concurrent viewers for 20 rounds without a 503; a manual order was delivered with
48 GPS positions from one courier. The API recovered after its process exited in
2.64 seconds. All 38 Python tests, including the real ClickHouse integration, and
7 JavaScript tests passed. Public operations requests in the final stress timing
sample reached 8.542 seconds; this local demo does not guarantee availability or
delay. Earlier verification: [public-flow evidence](evidencia-vercel.json).

## Architecture of this demo

```text
Teammate's browser -> web and GET function on Vercel
                   -> temporary Cloudflare HTTPS
                   -> authenticated read gateway
                   -> local Atlas API -> local ClickHouse
```

Event generation, SQLite and ClickHouse remain in Docker on the demo server (Anuar's computer since 21 October; Jere's before). The shared website displays its queries; it does not reproduce separately invented positions. If the computer goes to sleep, Docker stops or the tunnel closes, the website stays published but the data stops updating and a warning is shown.

The website is visible to anyone who has its link. Vercel and Cloudflare carry **fictional** positions and orders, counts and public catalog data. The massive files and the professor's resources are not published. The gateway token only exists in an ignored local file and in a sensitive environment variable of the function; it is never included in the browser JavaScript.

## What it can read

`simulation`, `operations`, `status`, `track`, `summary` (Madrid), `inventory`, `catalog` and `datasets` (the summary of the downloaded Criteo and Glovo datasets). The gateway validates routes and parameters, rejects POST/PUT/PATCH/DELETE and requires a token. `status` and `simulation` are reduced to the fields the dashboard needs. The Vercel function also rejects writes. The shared dashboard has no simulation controls and no insert button. Access to ClickHouse's SQL stays local.

There is a cache in the gateway: 1.5 s for tracking/status, 10 s for browsing and 60 s for catalog/inventory/datasets, with a maximum of 128 keys. It groups queries from several viewers; it adds delay compared with the local dashboard. The visual interval is still not a latency guarantee.

## Prepare and start

For a lab that already has its token files and linked Vercel project, use this
from the repository root after starting Docker:

```bash
python3 scripts/start_shared_demo.py --publish
```

It builds the current code, waits for ClickHouse, Atlas and the authenticated
gateway, obtains the current Quick Tunnel address and checks both `status` and
`operations` through it before updating Preview/Production configuration and
publishing the linked project. Run it again after recreating the tunnel: its
temporary address changes. Without `--publish` it starts and checks the shared
lab but does not update Vercel. Keep the computer awake during the demo.

Atlas shares one operations snapshot for 1.5 seconds between concurrent local
and public viewers; its ClickHouse client uses two query threads. ClickHouse,
Atlas and the gateway recover after unexpected container exits. Stop the old
Flask/Grafana stack before running Atlas so its second ClickHouse does not
compete for the classroom machine's memory. No data volume needs to be deleted.

The steps below document the initial setup and the individual commands.

1. Start Atlas by following [TRACKING-DEMO.md](TRACKING-DEMO.md). Start the fleet from http://127.0.0.1:8001/.
2. Create a token and the local files without printing it:

```bash
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('data/sharing'); p.mkdir(parents=True, exist_ok=True)
token = p / 'token'
if not token.exists():
    token.write_text(secrets.token_hex(32)); token.chmod(0o600)
env = p / 'gateway.env'
env.write_text('ATLAS_SHARE_TOKEN=' + token.read_text().strip() + '\n')
env.chmod(0o600)
PY
docker compose -f compose.yaml -f compose.share.yaml --profile atlas up -d --build --no-deps share-gateway share-tunnel
docker compose -f compose.yaml -f compose.share.yaml logs share-tunnel
```

3. Copy the `https://….trycloudflare.com` URL from the log to `data/sharing/origin` (it is not a password). [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) generates a temporary URL that changes when another tunnel is created; it has no availability guarantee. It does not require a Cloudflare account.
4. With an authenticated Vercel CLI, link **the demo project** and set its production variables:

```bash
vercel link --project delivery-atlas-demo --scope contrerasgeremi-gmailcoms-projects --yes
vercel env add ATLAS_SHARE_TOKEN production --sensitive --yes < data/sharing/token
vercel env add ATLAS_SHARE_ORIGIN production --yes < data/sharing/origin
vercel deploy --prod --scope contrerasgeremi-gmailcoms-projects --yes
```

Use `--force` with `env add` when replacing a variable that is already set, and deploy again. Do not pass tokens as arguments or write them to Git. `scripts/build_shared.mjs` prepares the three dashboard files; `.vercelignore` limits the upload to the frontend, function and configuration.

Vercel hosts the website and one function per request. The permanent process and the lab's storage stay outside the [time-limited functions](https://vercel.com/docs/functions/limitations).

## Stop sharing

```bash
docker compose -f compose.yaml -f compose.share.yaml stop share-tunnel share-gateway
```

This does not delete data or stop ClickHouse or the local demo. To open another
session, run `scripts/start_shared_demo.py --publish` again. The tunnel and the
simulator are deliberately started for each session; starting Docker alone does
not configure a new public address or resume an interrupted simulation.
