"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  let room = new URLSearchParams(location.hash.slice(1)).get("room");
  let client;
  try {
    client = localStorage.getItem("atlas-class-client");
    if (!client) {
      client = crypto.randomUUID();
      localStorage.setItem("atlas-class-client", client);
    }
  } catch {
    client = crypto.randomUUID();
  }
  let key = "atlas-class-order-" + room;
  let saved,
    posting = false;
  try {
    saved = JSON.parse(localStorage.getItem(key));
  } catch {
    /* storage unavailable */
  }
  let submission = saved;
  if (saved && !saved.order_id) {
    $("class-alias").value = saved.alias;
    saved = null;
  }
  const states = {
    created: "Waiting for a courier",
    preparing: "Preparing your dish",
    picked_up: "Your courier has collected it",
    en_route: "On the way through Madrid",
    delivered: "Delivered!",
    cancelled: "Cancelled in the simulation",
  };
  async function request(path, body) {
    const r = await fetch(path, {
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
      ...(body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : {}),
    });
    const d = await r.json();
    if (!r.ok) {
      const error = Error(d.error || "The class server could not respond.");
      error.status = r.status;
      throw error;
    }
    return d;
  }
  function receipt(row, data) {
    $("class-form").hidden = true;
    $("class-receipt").hidden = false;
    $("class-name").textContent =
      (row?.alias || submission.alias) + ", here’s your order.";
    $("class-dish").textContent =
      row?.product_name ||
      $("class-product").selectedOptions[0]?.textContent ||
      "Waiting for publication";
    $("class-state").textContent = row?.published
      ? states[row.status] || row.status
      : "Accepted into the durable queue";
    $("class-progress").textContent = row?.published
      ? "ClickHouse has published your order. Delivery and GPS positions are simulated."
      : "The publisher will insert your events into ClickHouse in a batch.";
    const map = new URL("/", location.origin);
    map.searchParams.set("room", room);
    map.searchParams.set("order", row?.order_id || saved?.order_id || "");
    map.hash = "tracking";
    $("class-map").href = map.href;
    $("class-id").textContent =
      "Order " + (row?.order_id || saved?.order_id || "").slice(0, 8);
  }
  async function refresh() {
    try {
      if (!room) {
        const active = await request("/api/classroom");
        if (!active.open)
          throw Error(
            "The classroom is getting ready. Keep this page open and we’ll retry.",
          );
        room = active.room_id;
        location.hash = "room=" + room;
        key = "atlas-class-order-" + room;
        try {
          submission = JSON.parse(localStorage.getItem(key));
          saved = submission?.order_id ? submission : null;
        } catch {}
        $("class-board").href =
          "/?room=" + encodeURIComponent(room) + "#tracking";
      }
      const data = await request(
        "/api/classroom?room_id=" + encodeURIComponent(room),
      );
      if ($("class-product").disabled) {
        $("class-product").replaceChildren(
          ...data.products.map((p) => {
            const o = document.createElement("option");
            o.value = p.product_id;
            o.textContent =
              p.product_name +
              " · " +
              (p.price_minor / 100).toFixed(2) +
              " EUR";
            return o;
          }),
        );
        $("class-product").disabled = false;
        if (submission?.product_id)
          $("class-product").value = submission.product_id;
      }
      const order = data.orders.find((o) => o.order_id === saved?.order_id);
      if (saved) receipt(order, data);
      $("class-submit").disabled =
        posting || !data.open || !data.products.length;
      if (!data.open && !saved)
        throw Error(
          "Ordering is paused. The presenter will open it when the delivery run starts.",
        );
      $("class-error").hidden = true;
    } catch (e) {
      $("class-error").hidden = false;
      $("class-error").textContent = e.message;
    } finally {
      setTimeout(() => {
        if (document.hidden) {
          refreshLater();
        } else refresh();
      }, 3000);
    }
  }
  function refreshLater() {
    setTimeout(() => (document.hidden ? refreshLater() : refresh()), 3000);
  }
  $("class-board").href =
    "/?room=" + encodeURIComponent(room || "") + "#tracking";
  $("class-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (posting) return;
    const alias = $("class-alias").value.trim();
    if (!/^[\p{L}\p{N}_ .'-]{1,24}$/u.test(alias)) {
      $("class-error").hidden = false;
      $("class-error").textContent =
        "Choose a nickname using letters, digits, spaces, dots or hyphens.";
      return;
    }
    posting = true;
    $("class-submit").disabled = true;
    // Freeze the request across lost responses. Editing is locked once submitted.
    submission ||= {
      room_id: room,
      client_id: client,
      alias: $("class-alias").value.trim(),
      product_id: $("class-product").value,
    };
    try {
      localStorage.setItem(key, JSON.stringify(submission));
    } catch {}
    $("class-alias").readOnly = true;
    $("class-product").disabled = true;
    try {
      const result = await request("/api/classroom-order", submission);
      saved = { ...submission, ...result };
      try {
        localStorage.setItem(key, JSON.stringify(saved));
      } catch {}
      receipt(null, null);
      $("class-error").hidden = true;
    } catch (e) {
      $("class-error").hidden = false;
      $("class-error").textContent =
        e.message + " You can retry the same order.";
      if (e.status === 400) {
        submission = null;
        $("class-alias").readOnly = false;
        $("class-product").disabled = false;
        try {
          localStorage.removeItem(key);
        } catch {}
      }
    } finally {
      posting = false;
      $("class-submit").disabled = false;
    }
  });
  refresh();
})();
