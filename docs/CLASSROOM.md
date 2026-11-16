# Classroom participation

Students choose a nickname and a dish on their phones. The existing manual checkout produces purchase and delivery events. The host dashboard displays class orders and labelled map markers.

## Host setup

Deploy the feature frontend to Vercel and rebuild Atlas and the share gateway on the host using the existing preservation steps in [DEMO-GUIDE.md](DEMO-GUIDE.md). Keep the current token in server-side configuration.

Start a customer simulation locally. In **Class orders**, set the public demo URL and choose **Open classroom for 1 hour**. Display its QR or use the stable link below. The room accepts up to 100 orders. Closing ordering keeps existing orders available for tracking.

Students open https://delivery-atlas-demo.vercel.app/classroom.html, which discovers the active room, or scan the room-specific QR. Each browser keeps a random device ID and its submitted order locally. A nickname appears on the projection alongside the dish and status. A new room gives each device another order. These are anonymous classroom identities.

Opening another room replaces the active roster. A changed or stopped simulation pauses new orders. Test with three phones before the class.

## Explain ClickHouse while the class participates

1. Show a nickname on the order receipt. It initially says the order was accepted into the durable queue.
2. Wait for the published status. Python validates the checkout contract and the publisher inserts events into ClickHouse.
3. Select a class order on the projection. A labelled star follows its courier. After delivery it marks the simulated destination.
4. Show the latest-state query and the route history. These are different read patterns over the incoming GPS stream.

Nicknames and room receipts are stored in SQLite metadata on the host. Purchase events, order state and GPS are published and queried in ClickHouse. A published label is based on the order appearing in ClickHouse. This addition uses the existing tables and views.

The new public write route is /api/classroom-order. Opening rooms, simulation controls and arbitrary event writes stay on the local host. Public order bodies are limited to 2 KiB. Rooms expire after one hour. Clients can retry the same order after a lost response. Limits apply to browser identities and the room.

The public URL becomes operational when the updated Atlas API and gateway are running. An older gateway rejects writes. A changed tunnel requires updating the existing Vercel origin.

## Presentation resources

The [classroom presentation](../presentaciones/classroom-2026-11-16/Delivery-Atlas.html), [English script](../presentaciones/classroom-2026-11-16/SCRIPT-EN.md) and [QR](../presentaciones/classroom-2026-11-16/Join-classroom.svg) accompany this feature. This live demonstration extension was prepared after the submitted Canvas archive. Use it after the host and public path pass the rehearsal check.

## Validation

On 16 November, three independent mobile browser contexts placed orders against a disposable ClickHouse 25.8.33.6 instance. All three appeared in the queried order state and as labelled markers on the Madrid map. A reload restored the first receipt. The host closed ordering and retained the receipts. Automated checks passed 87 Python tests with real SQL integration and 35 JavaScript tests. Gateway HTTP checks covered authenticated checkout, rejection of controls and other write methods, body limits and forwarding a closed-room response. Classroom tests cover retries after a lost response, concurrent retries, changed content, capacity and expiry.

## Mobile ordering design

The classroom menu now shows three illustrated choices from the first demo venue, each with its catalog price. Select a dish, enter a nickname and place the order. A progress timeline shows receipt, publication, travel and completion. The live roster uses matching thumbnails and nickname labels on the map. The interface uses self-hosted DM Sans and a liquid glass material with high-contrast and reduced-motion fallbacks.

Visual checks covered 320, 390, 768 and 1440-pixel layouts. A keyboard selection followed by a deliberately lost response and page reload produced one order on retry. Automated accessibility checks were run on the public mobile menu and live room, and the existing JavaScript suite passed 35 tests.

## Teach with a classmate’s order

Ask a classmate to order and find their nickname using the room search. Select that order to show its current state and location. Open **What reached ClickHouse?** or choose **See the ClickHouse row** beside the map. The SQL uses the actual selected run and order IDs. Its displayed fields come from the ClickHouse classroom response. Explain that events preserve history while the latest-state view supplies the current answer. The disclosure reuses the existing read snapshot.

Student-facing copy is short. The mobile receipt identifies receipt, publication, travel and completion. Once delivered, its action takes the participant to their drop-off. **Explore fleet** restores the generic courier details for a broader GPS demonstration.
