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

## Classroom ordering and live room, 16 November

The classroom mini-app and room-specific live view use the liquid glass direction requested by Geremi. The ordering task leads on phones, with a short nickname field, three dishes from one demo venue, real radio controls and an order summary beside the primary action. Existing receipts retain their original product even when it belongs to another venue.

DM Sans is served locally with its font license. Pale sage, pearl and warm neutral backgrounds provide depth behind translucent surfaces. Main text uses dark forest green. Glass surfaces use an inset light edge, a soft offset shadow and bounded backdrop blur. Contrast mode makes surfaces opaque. Reduced-motion mode removes control transitions.

The received-order view explains the queue, publication in ClickHouse and delivery through a four-stage timeline. It retains the saved request across interrupted responses and reloads. Mobile map controls have generous touch targets. The class roster preserves keyboard focus when status changes and uses a scrollable region for large classes.

Food imagery is AI-generated illustrative photography, encoded as one WebP asset reused across the menu and live roster. A caption identifies the imagery and fictional prices. Product names and prices come from the actual demo catalog.

## Classroom focus and teaching disclosure

The mobile menu leads with “Lunch, meet Madrid.” A map-pin name, three dishes and the order action carry the task. Supporting sentences that repeat labels and status stages are removed. Completion uses the same Delivered stamp idea as the presentation.

The room defaults to class orders, nickname search and the map. Selecting a class order replaces the generic courier metadata with that participant’s dish and current state. Explore fleet restores the courier controls. A native disclosure titled “What reached ClickHouse?” shows the selected order’s query and returned status, courier ID and UTC event time. It reuses the classroom snapshot, and preserves text selection when values are unchanged.

## Phone visual refinement

`web/classroom-mobile.css` refines the existing glass system without replacing the desktop layout. Menu dishes use larger photographs, quiet separators and a sage selection state. The receipt carries the same dish photo. The room has a compact horizontal roster and a safe-area-aware bottom navigation. The selected order appears above the mobile map. Participant pins use gold initials with a white rim to stand apart from the blue courier numbers. Every class name is permanently visible on phones and desktop, with high-contrast forest labels measured and packed inside the map viewport. Thin connectors link displaced names to their unchanged GPS markers. Class orders are framed on arrival, and Fit class orders restores that frame after manual navigation. Every pin retains its full accessible name. Direct map links scroll after live data has made the layout ready.
