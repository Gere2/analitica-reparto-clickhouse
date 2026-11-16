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
    classMap,
    selectedOrder = query.get("order"),
    busy = false,
    feedKey = "",
    classroomData,
    lessonKey = "",
    initialMapLink = location.hash === "#tracking",
    discoveredAt = 0,
    discoveredRoomLink;
  const discoverRoom = readOnly && !room;
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
    document.querySelector(".brand").href =
      "/?room=" + encodeURIComponent(room) + "#classroom-panel";
    document.querySelectorAll(".table-wrap").forEach((table) => {
      table.tabIndex = 0;
      table.setAttribute("role", "region");
      table.setAttribute("aria-label", "Scrollable order details");
    });
    document.querySelector(".heading h1").textContent = "Live in Madrid.";
    document.querySelector(".heading p").textContent =
      "Orders, couriers and GPS, live from ClickHouse.";
    const nav = document.querySelector('nav[aria-label="Sections"]');
    nav.classList.add("room-nav");
    nav.innerHTML =
      '<a href="#classroom-panel">Orders</a><a href="#tracking">Live map</a><a href="/analytics.html?panel=performance">ClickHouse</a><a class="live-order-link" href="/classroom.html">Order lunch</a>';
    function markSection() {
      for (const link of nav.querySelectorAll('a[href^="#"]')) {
        if (link.hash === (location.hash || "#classroom-panel"))
          link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      }
    }
    addEventListener("hashchange", markSection);
    markSection();
  }
  const host = panel.querySelector(".classroom-host");
  host.hidden = readOnly;
  const feed = panel.querySelector(".classroom-feed"),
    note = document.getElementById("classroom-note");
  feed.tabIndex = 0;
  feed.setAttribute("role", "region");
  feed.setAttribute("aria-label", "Class order list");
  const toolbar = document.createElement("div");
  toolbar.className = "room-toolbar";
  const title = panel.querySelector("h2");
  title.before(toolbar);
  toolbar.append(title);
  if (room) title.textContent = "Class orders";
  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Find your name";
  search.setAttribute("aria-label", "Find an order by nickname");
  toolbar.append(search);
  const empty = document.createElement("p");
  empty.className = "room-empty";
  empty.hidden = true;
  empty.setAttribute("role", "status");
  empty.textContent = "No names match. Try a shorter name.";
  feed.after(empty);
  function filterOrders() {
    const term = search.value.trim().toLocaleLowerCase();
    let count = 0;
    for (const button of feed.querySelectorAll("button")) {
      button.hidden = !button.dataset.alias.toLocaleLowerCase().includes(term);
      if (!button.hidden) count++;
    }
    empty.hidden = Boolean(count) || !feed.children.length;
  }
  search.addEventListener("input", filterOrders);
  const lesson = document.createElement("details");
  lesson.className = "classroom-lesson";
  lesson.innerHTML =
    '<summary>What reached ClickHouse?<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg></summary><div class="lesson-body"><div class="lesson-route"><span>Your tap</span><i>→</i><span>Queue</span><i>→</i><span>Batch INSERT</span><i>→</i><b>Latest state</b></div><p id="lesson-selection">Place an order to inspect its row.</p><pre id="lesson-sql-wrap" hidden><code id="lesson-sql"></code></pre><dl id="lesson-result" hidden></dl><p class="lesson-takeaway">New events keep the history. The latest-state view answers the map.</p></div>';
  panel.append(lesson);
  const detail = document.querySelector(".detail");
  const focusClass = document.createElement("button");
  focusClass.type = "button";
  focusClass.className = "secondary";
  focusClass.textContent = "Fit class orders";
  focusClass.disabled = true;
  focusClass.hidden = true;
  document.querySelector(".map-tools > div").prepend(focusClass);
  focusClass.onclick = () => classMap?.focus();
  for (const id of ["fit-fleet", "follow-courier"])
    document.getElementById(id).addEventListener("click", () => {
      if (classMap) classMap.focused = false;
    });
  const own = document.createElement("section");
  own.className = "class-order-detail";
  own.hidden = true;
  own.innerHTML =
    '<div class="selected-meal meal-thumb" aria-hidden="true"></div><h3 id="selected-alias"></h3><strong id="selected-status"></strong><p id="selected-dish"></p><p id="selected-proof"></p><div class="selected-actions"><button id="selected-query" class="secondary" type="button">See the ClickHouse row</button><button id="selected-fleet" class="secondary" type="button">Explore fleet</button></div>';
  detail.prepend(own);
  document.getElementById("selected-query").onclick = () => {
    lesson.open = true;
    lesson.scrollIntoView({ behavior: "instant", block: "start" });
  };
  document.getElementById("selected-fleet").onclick = () => {
    selectedOrder = null;
    renderSelected();
    feed
      .querySelectorAll("button")
      .forEach((b) => b.setAttribute("aria-pressed", "false"));
  };
  function renderSelected() {
    const order = classroomData?.orders.find(
      (o) => o.order_id === selectedOrder,
    );
    own.hidden = !order;
    detail.dataset.classOrder = String(Boolean(order));
    const matchingCourier =
      order &&
      lastData?.couriers.some(
        (c) => c.courier_id === order.courier_id && c.order_id === order.order_id,
      );
    document.getElementById("follow-courier").hidden = Boolean(
      order && !matchingCourier,
    );
    document.querySelector(".map-tools > span").textContent = order
      ? order.alias +
        (matchingCourier ? " · courier on the move" : " · delivery destination")
      : "Select a courier to explore its delivery";
    if (!order) return;
    document.getElementById("selected-alias").textContent = order.alias;
    document.getElementById("selected-status").textContent = order.published
      ? statuses[order.status] || order.status
      : "Waiting for ClickHouse";
    document.getElementById("selected-dish").textContent = order.product_name;
    document.getElementById("selected-proof").textContent = order.published
      ? "Order " + order.order_id.slice(0, 8) + " · in ClickHouse"
      : "Waiting for publication";
    own
      .querySelector(".selected-meal")
      .style.setProperty(
        "--meal-position",
        /salad/i.test(order.product_name)
          ? "right"
          : /house|menu/i.test(order.product_name)
            ? "center"
            : "left",
      );
  }
  function renderLesson() {
    const order =
      classroomData?.orders.find((o) => o.order_id === selectedOrder) ||
      classroomData?.orders.at(-1);
    const selection = document.getElementById("lesson-selection"),
      code = document.getElementById("lesson-sql");
    const result = document.getElementById("lesson-result");
    if (!order) {
      selection.textContent = "Place an order to inspect its row.";
      result.hidden = true;
      document.getElementById("lesson-sql-wrap").hidden = true;
      return;
    }
    selection.textContent =
      order.alias +
      " · " +
      (order.published ? "Current order state" : "Waiting for ClickHouse");
    const sql =
      "SELECT status, courier_id, event_time\nFROM delivery_atlas.order_latest\nWHERE simulation_run_id = '" +
      classroomData.run_id +
      "'\n  AND order_id = '" +
      order.order_id +
      "';";
    if (code.textContent !== sql) code.textContent = sql;
    document.getElementById("lesson-sql-wrap").hidden = false;
    result.hidden = !order.published;
    const key = JSON.stringify([
      order.order_id,
      order.published,
      order.status,
      order.courier_id,
      order.event_time,
    ]);
    if (key === lessonKey) return;
    lessonKey = key;
    result.replaceChildren(
      ...["status", "courier_id", "event_time"].map((key) => {
        const group = document.createElement("div"),
          term = document.createElement("dt"),
          value = document.createElement("dd");
        term.textContent = key + (key === "event_time" ? " (UTC)" : "");
        value.textContent = order[key] ?? "—";
        group.append(term, value);
        return group;
      }),
    );
  }
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
    if (busy || document.hidden) return;
    busy = true;
    try {
      // The general map also carries class orders. Explicit room links stay
      // pinned to their receipt; the general view follows the active room.
      if (discoverRoom && (!room || Date.now() - discoveredAt >= 10000)) {
        const current = await request("/api/classroom");
        discoveredAt = Date.now();
        if (current.room_id && current.room_id !== room) {
          room = current.room_id;
          classroomData = undefined;
          selectedOrder = null;
          feedKey = "";
          lessonKey = "";
          markers?.clearLayers();
          classMap?.clear();
          if (classMap) classMap.focused = true;
          feed.replaceChildren();
          renderSelected();
          renderLesson();
          document.body.classList.add("classroom-live");
          title.textContent = "Class orders";
          if (!discoveredRoomLink) {
            discoveredRoomLink = document.createElement("a");
            discoveredRoomLink.textContent = "Class orders";
            document.querySelector('nav[aria-label="Sections"]')
              .append(discoveredRoomLink);
          }
          discoveredRoomLink.href =
            "/?room=" + encodeURIComponent(room) + "#classroom-panel";
        }
      }
      if (!room) return;
      const data = await request(
        "/api/classroom?room_id=" + encodeURIComponent(room),
      );
      panel.hidden = false;
      classroomData = data;
      note.textContent =
        data.orders.length +
        " " +
        (data.orders.length === 1 ? "order" : "orders") +
        " · " +
        (data.open ? "Kitchen open" : "Ordering paused");
      document.querySelector(".classroom-pipeline").hidden = true;
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
            button.dataset.alias = o.alias;
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
                  : "Waiting for ClickHouse",
              ) +
              "</span>";
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
              renderSelected();
              renderLesson();
              follow(o);
              location.hash = "tracking";
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
      filterOrders();
      renderSelected();
      renderLesson();
      if (data.run_id === lastData?.run_id && fleetMap.map) {
        classMap ||= new AtlasClassroomMap(fleetMap.map, () => fleetMap.setFollow(false));
        markers ||= L.layerGroup().addTo(fleetMap.map);
        markers.clearLayers();
        const classEntries = [];
        for (const o of data.orders.filter((o) => o.published)) {
          const c = lastData.couriers.find(
            (c) => c.courier_id === o.courier_id && c.order_id === o.order_id,
          );
          const lat = c?.latitude ?? o.dropoff_lat,
            lon = c?.longitude ?? o.dropoff_lon;
          if (!Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon)))
            continue;
          const label = document.createElement("span");
          label.textContent = o.alias;
          const active = o.order_id === selectedOrder;
          const initials = o.alias
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map((word) => word[0])
            .join("")
            .toLocaleUpperCase();
          const marker = L.marker([lat, lon], {
            icon: L.divIcon({
              className: "classroom-marker",
              html:
                '<span class="classroom-pin' +
                (active ? " is-selected" : "") +
                '">' + esc(initials) + "</span>",
              iconSize: [44, 44],
              iconAnchor: [22, 22],
            }),
            zIndexOffset: active ? 2400 : 1800,
            title: o.alias,
          })
            .bindTooltip(label, {
              permanent: true,
              direction: "center",
              offset: [0, 0],
              opacity: 1,
              className: "classroom-label" + (active ? " is-selected" : ""),
            })
            .on("click", () => {
              selectedOrder = o.order_id;
              renderSelected();
              renderLesson();
              follow(o);
            })
            .addTo(markers);
          marker.getElement()?.setAttribute(
            "aria-label",
            o.alias + " · " + (statuses[o.status] || o.status),
          );
          classEntries.push({id:o.order_id, marker});
        }
        focusClass.disabled = !classEntries.length;
        focusClass.hidden = !classEntries.length;
        classMap.setMarkers(classEntries);
        const selected = data.orders.find((o) => o.order_id === selectedOrder);
        if (selected) follow(selected, false);
      } else if (markers) {
        markers.clearLayers();
        classMap?.clear();
        focusClass.disabled = true;
        focusClass.hidden = true;
      }
      if (initialMapLink && lastData && fleetMap.map) {
        initialMapLink = false;
        document.getElementById("tracking").scrollIntoView({
          behavior: "instant",
          block: "start",
        });
      }
    } catch (e) {
      note.textContent = e.message + " Retrying…";
    } finally {
      busy = false;
    }
  }
  function follow(order, center = true) {
    if (
      order.courier_id &&
      lastData?.couriers.some(
        (c) =>
          c.courier_id === order.courier_id && c.order_id === order.order_id,
      )
    ) {
      selectCourier(order.courier_id);
    } else if (center && fleetMap.map && order.published && !classMap?.focused) {
      fleetMap.map.panTo([order.dropoff_lat, order.dropoff_lon], {
        animate: false,
      });
    }
  }
  if (room || discoverRoom) {
    if (!readOnly) join();
    pollClass();
  }
  setInterval(pollClass, 2500);
})();
