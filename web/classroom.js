"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const money = (value) =>
    new Intl.NumberFormat("en-IE", {
      style: "currency",
      currency: "EUR",
    }).format(value / 100);
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
  let submission,
    saved,
    posting = false,
    open = false,
    products = [],
    menuKey = "";
  const states = {
    created: "Finding your courier",
    preparing: "Your dish is being prepared",
    picked_up: "Your courier has collected it",
    en_route: "On the way through Madrid",
    delivered: "Delivered. Enjoy your virtual lunch!",
    cancelled: "Cancelled in the simulation",
  };

  function restore() {
    try {
      const stored = JSON.parse(localStorage.getItem(key));
      if (
        stored &&
        typeof stored.alias === "string" &&
        stored.room_id === room
      ) {
        submission = stored;
        saved = stored.order_id ? stored : null;
        $("class-alias").value = stored.alias;
        $("class-alias").readOnly = true;
      }
    } catch {
      /* A new visitor can still order without browser storage. */
    }
  }
  restore();

  async function request(path, body) {
    const controller = new AbortController(),
      timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(path, {
        cache: "no-store",
        signal: controller.signal,
        ...(body
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            }
          : {}),
      });
      const data = await response.json();
      if (!response.ok) {
        const error = Error(
          data.error || "The kitchen could not respond. Please try again.",
        );
        error.status = response.status;
        throw error;
      }
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  function showError(message) {
    $("class-error").hidden = !message;
    if ($("class-error").textContent !== (message || ""))
      $("class-error").textContent = message || "";
  }

  function dishPosition(name) {
    return /salad/i.test(name)
      ? "right"
      : /house|menu/i.test(name)
        ? "center"
        : "left";
  }

  function updateAction() {
    const selected = products.find(
      (product) => product.product_id === $("class-product").value,
    );
    $("class-choice").textContent =
      selected?.product_name || "Choose your dish";
    $("class-total").textContent = selected ? money(selected.price_minor) : "—";
    $("class-submit").disabled = posting || !open || !selected;
    $("class-submit").firstChild.textContent = posting
      ? "Placing your order… "
      : "Place my order ";
  }

  function menu(data) {
    products = data.products;
    const signature = JSON.stringify(products);
    if (signature === menuKey) return;
    menuKey = signature;
    const old = submission?.product_id || $("class-product").value;
    // A concise menu from one venue, with the original submitted dish retained on reload.
    const firstVenue = products[0]?.restaurant_id;
    const choices = products.filter((p) => p.restaurant_id === firstVenue);
    const original = products.find((p) => p.product_id === old);
    if (original && !choices.some((p) => p.product_id === old))
      choices.push(original);
    $("class-product").replaceChildren(
      new Option("Choose your dish", ""),
      ...choices.map(
        (product) => new Option(product.product_name, product.product_id),
      ),
    );
    $("class-product").disabled = false;
    if (old) $("class-product").value = old;
    $("class-menu").replaceChildren(
      ...choices.map((product) => {
        const label = document.createElement("label");
        label.className = "dish-option";
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "class-dish";
        radio.value = product.product_id;
        radio.required = true;
        radio.checked = product.product_id === old;
        radio.disabled = posting || !!submission;
        const face = document.createElement("span");
        face.className = "dish-face";
        const image = document.createElement("span");
        image.className = "meal-thumb";
        image.setAttribute("aria-hidden", "true");
        image.style.setProperty(
          "--meal-position",
          dishPosition(product.product_name),
        );
        const text = document.createElement("span");
        text.className = "dish-copy";
        const title = document.createElement("b");
        title.textContent = product.product_name;
        const description = document.createElement("small");
        description.textContent = /salad/i.test(product.product_name)
          ? "Crisp, colourful and fresh"
          : /house|menu/i.test(product.product_name)
            ? "A lunch-time favourite"
            : "A bowl full of good things";
        const price = document.createElement("strong");
        price.textContent = money(product.price_minor);
        text.append(title, description, price);
        face.append(image, text);
        label.append(radio, face);
        radio.addEventListener("change", () => {
          $("class-product").value = product.product_id;
          updateAction();
        });
        return label;
      }),
    );
    $("class-menu").setAttribute("aria-busy", "false");
    if (!choices.length)
      $("class-menu").textContent =
        "The menu is getting ready. We’ll retry shortly.";
  }

  function receipt(row) {
    const first = $("class-receipt").hidden;
    $("class-form").hidden = true;
    $("class-receipt").hidden = false;
    document.body.dataset.orderState = "receipt";
    $("class-name").textContent =
      "Order received, " + (row?.alias || submission.alias) + ".";
    const product = products.find((p) => p.product_id === saved?.product_id);
    $("class-dish").textContent =
      (row?.product_name || product?.product_name || "Your class order") +
      (product ? " · " + money(product.price_minor) : "");
    const status = row?.published
      ? states[row.status] || row.status
      : "Accepted. Joining the live view…";
    if ($("class-state").textContent !== status)
      $("class-state").textContent = status;
    $("class-progress").textContent = row?.published
      ? "Published in ClickHouse. Your courier and delivery are simulated."
      : "Your order is safely queued. The publisher will add it to ClickHouse in the next batch.";
    const complete = new Set(["queued"]);
    if (row?.published) complete.add("published");
    if (["picked_up", "en_route", "delivered"].includes(row?.status))
      complete.add("travelling");
    if (row?.status === "delivered") complete.add("delivered");
    document.querySelectorAll("[data-stage]").forEach((item) => {
      item.classList.toggle("complete", complete.has(item.dataset.stage));
    });
    $("class-map").href =
      "/?room=" +
      encodeURIComponent(room) +
      "&order=" +
      encodeURIComponent(row?.order_id || saved?.order_id || "") +
      "#tracking";
    $("class-id").textContent =
      "Your reference · " +
      (row?.order_id || saved?.order_id || "").slice(0, 8);
    if (first) {
      $("class-alias").blur();
      $("class-name").focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: "instant" });
    }
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
        restore();
      }
      $("class-board").href =
        "/?room=" + encodeURIComponent(room) + "#tracking";
      const data = await request(
        "/api/classroom?room_id=" + encodeURIComponent(room),
      );
      open = data.open;
      menu(data);
      if (saved)
        receipt(data.orders.find((order) => order.order_id === saved.order_id));
      updateAction();
      if (!open && !saved)
        throw Error(
          "Ordering is paused. The presenter will open the kitchen shortly.",
        );
      showError("");
    } catch (error) {
      showError(
        error.name === "AbortError"
          ? "The connection is taking a moment. We’ll keep trying."
          : error.message,
      );
    } finally {
      setTimeout(refreshWhenVisible, 3000);
    }
  }
  function refreshWhenVisible() {
    if (document.hidden) setTimeout(refreshWhenVisible, 3000);
    else refresh();
  }

  $("class-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (posting) return;
    const alias = $("class-alias").value.trim();
    if (!/^[\p{L}\p{N}_ .'-]{1,24}$/u.test(alias)) {
      showError(
        "Choose a nickname with letters, digits, spaces, dots or hyphens.",
      );
      $("class-alias").focus();
      return;
    }
    if (!$("class-product").value) {
      showError("Choose a dish to start your delivery.");
      return;
    }
    submission ||= {
      room_id: room,
      client_id: client,
      alias,
      product_id: $("class-product").value,
    };
    posting = true;
    updateAction();
    $("class-alias").readOnly = true;
    document.querySelectorAll('[name="class-dish"]').forEach((input) => {
      input.disabled = true;
    });
    try {
      localStorage.setItem(key, JSON.stringify(submission));
    } catch {}
    try {
      const result = await request("/api/classroom-order", submission);
      saved = { ...submission, ...result };
      try {
        localStorage.setItem(key, JSON.stringify(saved));
      } catch {}
      receipt(null);
      showError("");
    } catch (error) {
      showError(error.message + " Your selection is saved. Try again.");
      if (error.status === 400) {
        submission = null;
        $("class-alias").readOnly = false;
        document.querySelectorAll('[name="class-dish"]').forEach((input) => {
          input.disabled = false;
        });
        try {
          localStorage.removeItem(key);
        } catch {}
      }
    } finally {
      posting = false;
      updateAction();
    }
  });
  $("class-board").href =
    "/?room=" + encodeURIComponent(room || "") + "#tracking";
  refresh();
})();
