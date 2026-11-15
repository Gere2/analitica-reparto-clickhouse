"use strict";
(() => {
  const panel = document.getElementById("classroom-panel"),
    query = new URLSearchParams(location.search);
  const esc = (t) =>
    String(t).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  let room = query.get("room"),
    markers,
    selectedOrder = query.get("order"),
    busy = false;
  if (!readOnly && !room) {
    try {
      room = localStorage.getItem("atlas-host-room");
    } catch {}
  }
  panel.hidden = readOnly && !room;
  const host = panel.querySelector(".classroom-host");
  host.hidden = readOnly;
  const feed = panel.querySelector(".classroom-feed"),
    note = document.getElementById("classroom-note");
  const statuses = {
    created: "Waiting for a courier",
    preparing: "Preparing",
    picked_up: "Collected",
    en_route: "On the way",
    delivered: "Delivered",
    cancelled: "Cancelled",
  };
  function join() {
    const base = document.getElementById("classroom-origin").value;
    const u = new URL("/classroom.html", base);
    u.hash = "room=" + room;
    const a = document.getElementById("classroom-link");
    a.href = u.href;
    a.textContent = u.href;
    const qr = qrcode(0, "M");
    qr.addData(u.href);
    qr.make();
    document.getElementById("classroom-qr").innerHTML = qr.createSvgTag({
      cellSize: 5,
      margin: 20,
      scalable: true,
    });
    document.getElementById("classroom-join").hidden = false;
  }
  document.getElementById("classroom-origin").addEventListener("change", () => {
    if (room) {
      try {
        join();
      } catch {
        note.textContent = "Enter a valid public URL.";
      }
    }
  });
  async function manage(action) {
    document.getElementById("classroom-open").disabled = true;
    try {
      const r = await request("/api/classroom-" + action, {});
      if (action === "open") {
        room = r.room_id;
        try {
          localStorage.setItem("atlas-host-room", room);
        } catch {}
        join();
        pollClass();
      } else
        note.textContent =
          "Ordering closed. Existing deliveries remain visible.";
    } catch (e) {
      note.textContent = e.message;
    } finally {
      document.getElementById("classroom-open").disabled = false;
    }
  }
  document.getElementById("classroom-open").onclick = () => manage("open");
  document.getElementById("classroom-close").onclick = () => manage("close");
  async function pollClass() {
    if (busy || !room || document.hidden) return;
    busy = true;
    try {
      const data = await request(
        "/api/classroom?room_id=" + encodeURIComponent(room),
      );
      panel.hidden = false;
      note.textContent =
        data.orders.length +
        " class orders · " +
        data.orders.filter((o) => o.published).length +
        " published in ClickHouse · " +
        (data.open ? "ordering open" : "ordering paused or closed");
      feed.replaceChildren(
        ...data.orders.map((o) => {
          const button = document.createElement("button");
          button.className = "classroom-ticket";
          button.dataset.order = o.order_id;
          button.innerHTML =
            "<b>" +
            esc(o.alias) +
            "</b><span>" +
            esc(o.product_name) +
            '</span><span class="ticket-state">' +
            esc(
              o.published
                ? statuses[o.status] || o.status
                : "Accepted · waiting for ClickHouse",
            ) +
            "</span><small>Order " +
            esc(o.order_id.slice(0, 8)) +
            "</small>";
          button.onclick = () => {
            selectedOrder = o.order_id;
            follow(o);
            document
              .getElementById("tracking")
              .scrollIntoView({ behavior: "instant", block: "start" });
          };
          return button;
        }),
      );
      if (data.run_id === lastData?.run_id && fleetMap.map) {
        markers ||= L.layerGroup().addTo(fleetMap.map);
        markers.clearLayers();
        for (const o of data.orders.filter((o) => o.published)) {
          const c = lastData.couriers.find(
            (c) => c.courier_id === o.courier_id && c.order_id === o.order_id,
          );
          const lat = c?.latitude ?? o.dropoff_lat,
            lon = c?.longitude ?? o.dropoff_lon;
          if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon)))
            continue;
          const label = document.createElement("span");
          label.textContent = o.alias + (c ? "" : " · destination");
          L.marker([lat, lon], {
            icon: L.divIcon({
              className: "classroom-marker",
              html: '<span class="classroom-pin">★</span>',
              iconSize: [30, 30],
            }),
            zIndexOffset: 1800,
            title: o.alias,
          })
            .bindTooltip(label, {
              permanent: true,
              direction: "top",
              className: "classroom-label",
            })
            .on("click", () => {
              selectedOrder = o.order_id;
              follow(o);
            })
            .addTo(markers);
        }
        const selected = data.orders.find((o) => o.order_id === selectedOrder);
        if (selected) follow(selected);
      } else if (markers) {
        markers.clearLayers();
      }
    } catch (e) {
      note.textContent = e.message + " Retrying…";
    } finally {
      busy = false;
    }
  }
  function follow(order) {
    if (
      order.courier_id &&
      lastData?.couriers.some(
        (c) =>
          c.courier_id === order.courier_id && c.order_id === order.order_id,
      )
    ) {
      selectCourier(order.courier_id);
    } else if (fleetMap.map && order.published) {
      fleetMap.map.panTo([order.dropoff_lat, order.dropoff_lon], {
        animate: false,
      });
    }
  }
  if (room) {
    if (!readOnly) join();
    pollClass();
  }
  setInterval(pollClass, 2500);
})();
