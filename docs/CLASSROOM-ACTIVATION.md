# Activate the classroom on Anuar's host

This extension adds phone orders and classmate pins to the existing Madrid map. It was prepared after the Canvas submission. The submitted archive and the approved final presentation/script remain separate. The classroom presentation copy has an opening QR for the stable URL:

https://delivery-atlas-demo.vercel.app/classroom.html

## Update the existing host

Use the serving checkout and the existing Compose project, data volumes, SQLite queue and gateway token. Follow the preservation steps in [DEMO-GUIDE.md](DEMO-GUIDE.md) before rebuilding: pause the watchdog, stop simulations from their own dashboards, wait for pending zero on both APIs if active, and verify the run exports. Do not use `down -v`, `reset --hard` or another empty checkout/project to replace the host.

Rayo supplies the reviewed Classroom PR and its exact head commit in the handoff email. While the PR is open, fetch and check out its branch in the serving checkout after preserving any local changes. Once merged, update `main` using `git merge --ff-only origin/main`. Confirm `git rev-parse HEAD` matches the supplied revision before rebuilding.

```bash
docker compose -f compose.yaml --profile atlas --profile ai up -d --build --wait
docker compose -f compose.yaml -f compose.share.yaml --profile atlas up -d --build --no-deps share-gateway
```

Wait for healthy services. Keep the manually created second API on port 18001 stopped during rehearsal. Preserve `data/sharing/token`, `gateway.env`, and the current running tunnel. If its hostname has expired, recreate the tunnel using the existing Compose setup and send its new HTTPS URL; a tunnel restart may change that URL.

## Open a room locally

1. Open `http://127.0.0.1:8001/`. For the first connectivity test use **Traffic simulator**, **3 customers**, **12 couriers**, then **Start customers and delivery**. This avoids spending model calls on the connection test. The final rehearsed hybrid configuration is still 100 customers / 50 couriers / 2-second ticks, started near the talk.
2. In **Class orders**, set **Public demo URL** to `https://delivery-atlas-demo.vercel.app`, then **Open classroom for 1 hour**. Opening another room replaces the active roster, so do not reopen it while checking the same participants.
3. Copy the `room_id` from the join link. Verify locally that `/api/classroom` reports `open: true`, the expected room ID and expiry, and `/api/classroom?room_id=ROOM_UUID` returns the class roster.
4. Open `/classroom.html` locally and make one named test order. Verify it becomes published, appears on the map, and survives a reload.

## Check the gateway and send the handoff

Using the existing token locally, check HTTP 200 through the tunnel for `status`, `operations`, `journey`, `performance`, `datasets`, and `classroom`, plus the room-specific classroom read. Without the token, protected reads must return 401. The only public write is `POST /api/classroom-order`, with a 2-KiB body; simulation controls and room open/close remain local and the gateway must reject them.

Reply to Geremi with:

- exact commit and healthy service status;
- current HTTPS tunnel origin (without credentials);
- room UUID, expiry and run UUID;
- endpoint results and the test order ID / published state;
- confirmation that pre-existing data volumes and the token were preserved.

Do not email the token. If the existing token has changed, coordinate a private configuration update rather than sending it in a message.

## Public release owned by Rayo

After host validation, Rayo publishes the matching reviewed frontend/proxy to `delivery-atlas-demo` in Vercel. Preserve the existing server-side token; change `ATLAS_SHARE_ORIGIN` only if the validated tunnel changed. Validate the stable QR URL, phone checkout, publication, map marker, receipt reload and ClickHouse row disclosure against Anuar's room. A READY deployment alone is not a successful connection test.

Room capacity is 100 orders, one per browser identity per room. It expires after one hour. A stopped or changed simulation pauses new submissions. Anonymous nicknames and room receipts live in SQLite; purchase/order/GPS events are published and read in ClickHouse. Do not describe nicknames as authenticated accounts or simulated locations as participants' actual GPS.
