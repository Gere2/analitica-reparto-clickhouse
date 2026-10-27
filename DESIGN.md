# Delivery Atlas: operations dashboard design

It extends the lab's existing visual family: light grey background, white surfaces, green accent and blue for data. The earlier lab is kept. New dashboard: `web/atlas-dashboard.html`.

## Scene and priority

Operate mode: during a class, on a laptop or projector in ambient light, Jere starts the simulation, selects a courier and shows that its published position changes. Light background and readable contrast; statuses do not depend on colour alone.

## Structure

The structure combines operations and inventory: a header with the simulation control; compact counters; an interactive Madrid street map and the selected detail; current orders; browsing; inventory and catalog. Historical data appears separately below, without competing with tracking. Routes and positions are labelled as synthetic. At the user’s request (21 October), Leaflet displays real OpenStreetMap streets, with visible attribution, pan, zoom, fit-fleet and opt-in courier following. Positions and sample-to-sample paths remain synthetic, not road routing. Leaflet is served locally; street tiles need network access. The map initializes near the viewport and reuses marker layers on refresh.

The 27 October analytics extension inherits the same visual system. A single English portal at `analytics.html` uses a desktop dashboard menu and a horizontally scrollable menu on mobile. Figures show meaningful data, with accessible exact-value tables. Each dashboard exposes fixed SQL and measured server work. Storage metadata, source history and synthetic session metrics keep their different scopes. The map implementation and its lifecycle stay in `atlas-map.js`.

Seven structures were considered (full map, list with map, status lanes, timeline, historical comparison, operations with inventory, individual session). The structure selection pointed to operations with inventory. The visual-alternatives service was not available; the existing system was inherited. The work was not delegated: the user asked Rayo to work alone.

## System

- System font for controls and data, avoiding downloads in a local demo.
- Dark green `#24553d` for the main action and selection; blue `#244e77` for GPS; red `#9f3131` for errors; dark orange for delays.
- Main text `#18242d`, secondary `#52645b`, background `#f6f7f3`, lines `#dfe4df`.
- Separate sections with space and lines; do not nest cards. Buttons and controls with visible focus, explicit loading and error states.
- Two columns for tracking on desktop; one on mobile, with a horizontally scrollable table and the map visible.
- No decorative animation. The marker only changes when positions are received from the server. Reduced motion keeps the same behaviour.
