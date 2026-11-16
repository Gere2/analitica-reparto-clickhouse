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
    busy = false,
    feedKey = "";
  if (!readOnly && !room) {
    try {
      room = localStorage.getItem("atlas-host-room");
    } catch {}
  }
  panel.hidden = readOnly && !room;
  if (room || !readOnly) document.body.classList.add("classroom-live");
  document.getElementById("rate").setAttribute("role", "img");
  if (room) {
    document.body.dataset.classroomView = "room";
    document.querySelectorAll(".table-wrap").forEach((table) => {
      table.tabIndex = 0;
      table.setAttribute("role", "region");
      table.setAttribute("aria-label", "Scrollable order details");
    });
    document.querySelector(".heading h1").textContent = "Live in Madrid.";
    document.querySelector(".heading p").textContent =
      "Orders, couriers and GPS, live from ClickHouse.";
    const nav = document.querySelector('nav[aria-label="Sections"]');
    nav.innerHTML =
      '<a href="#classroom-panel">Class orders</a><a href="#tracking">Live map</a><a href="/analytics.html?panel=performance">ClickHouse</a><a class="live-order-link" href="/classroom.html">Place an order</a>';
  }
  const host = panel.querySelector(".classroom-host");
  host.hidden = readOnly;
  const feed = panel.querySelector(".classroom-feed"),
    note = document.getElementById("classroom-note");
  feed.tabIndex = 0;
  feed.setAttribute("role", "region");
  feed.setAttribute("aria-label", "Class order list");
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
      const newKey = JSON.stringify(
        data.orders.map((o) => [
          o.order_id,
          o.alias,
          o.product_name,
          o.published,
          o.status,
        ]),
      );
      const focusId = feed.contains(document.activeElement)
        ? document.activeElement.dataset.order
        : null;
      if (newKey !== feedKey) {
        feedKey = newKey;
        feed.replaceChildren(
          ...data.orders.map((o) => {
            const button = document.createElement("button");
            button.className = "classroom-ticket";
            button.dataset.order = o.order_id;
            button.setAttribute(
              "aria-pressed",
              String(o.order_id === selectedOrder),
            );
            const position = /salad/i.test(o.product_name)
              ? "right"
              : /house|menu/i.test(o.product_name)
                ? "center"
                : "left";
            button.innerHTML =
              '<span class="meal-thumb" style="--meal-position:' +
              position +
              '" aria-hidden="true"></span><b>' +
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
              feed
                .querySelectorAll("button")
                .forEach((item) =>
                  item.setAttribute(
                    "aria-pressed",
                    String(item.dataset.order === selectedOrder),
                  ),
                );
              follow(o);
              document
                .getElementById("tracking")
                .scrollIntoView({ behavior: "instant", block: "start" });
            };
            return button;
          }),
        );
        if (focusId)
          feed
            .querySelector('[data-order="' + focusId + '"]')
            ?.focus({ preventScroll: true });
      }
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
