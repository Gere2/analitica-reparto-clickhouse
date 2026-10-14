'use strict';
// Miniapp comercial de Delivery Atlas.
// Registra cada acción con el contrato v1 (atlas/contract.py) en POST /api/events
// y confirma el pedido en POST /api/checkout, que lo entrega en la simulación.

const SOURCE = 'delivery-miniapp';
const KIND = 'demo_live';
const SOL = [40.4169, -3.7035];                       // Puerta del Sol
const STATUS_ORDER = ['created', 'preparing', 'picked_up', 'en_route', 'delivered'];
const $ = id => document.getElementById(id);
const money = minor => new Intl.NumberFormat('es-ES', {style: 'currency', currency: 'EUR'}).format(minor / 100);

const state = {
  restaurants: [], products: [], city: 'madrid',
  query: '', filters: new Set(),
  shop: null, product: null,
  cart: new Map(),                                     // product_id -> quantity (un solo restaurante)
  session: null, customer: null,
  order: null, poll: null, view: 'home',
};

// ── Identidad ─────────────────────────────────────────────
// customer_id se conserva en este navegador; session_id es nuevo en cada visita/pedido.
function customerId() {
  let id = null;
  try { id = localStorage.getItem('atlas_customer_id'); } catch (e) { /* almacenamiento bloqueado */ }
  if (!id) { id = crypto.randomUUID(); try { localStorage.setItem('atlas_customer_id', id); } catch (e) {} }
  return id;
}
function newSession() {
  state.session = crypto.randomUUID();
  $('session-id').textContent = state.session.slice(0, 8);
}

// ── Envío de eventos ──────────────────────────────────────
// Un evento se construye UNA vez: el reintento reutiliza el mismo objeto (mismo
// event_id y misma hora), así la API lo reconoce como duplicado y no cuenta dos veces.
const outbox = [];
let sending = false;

function track(type, section, extra = {}) {
  const event = {
    schema_version: 1, event_id: crypto.randomUUID(), session_id: state.session,
    event_time: new Date().toISOString(), event_type: type, section,
    city_id: state.city, user_id: state.customer, source: SOURCE, source_kind: KIND, ...extra,
  };
  const ticket = addTicket(type, extra);
  outbox.push({event, ticket, attempts: 0});
  flush();
  return event;
}

async function flush() {
  if (sending) return;
  sending = true;
  while (outbox.length) {
    const item = outbox[0];
    item.attempts += 1;
    setTicket(item.ticket, 'sending', item.attempts > 1 ? `Reintento ${item.attempts - 1}` : 'Enviando');
    let response = null, data = {};
    try {
      response = await fetch('/api/events', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({events: [item.event]}), cache: 'no-store'});
      data = await response.json().catch(() => ({}));
    } catch (e) { response = null; }
    if (response && (response.status === 202 || response.status === 200)) {
      setTicket(item.ticket, 'ok', response.status === 202 ? 'En cola · 202' : 'Ya registrado · 200');
      outbox.shift();
    } else if (response && response.status !== 503 && response.status < 500) {
      // 400/409: el evento no es válido. Reintentar no lo arregla; se muestra el motivo.
      setTicket(item.ticket, 'fail', `No guardado · ${response.status} ${data.error || ''}`.trim());
      outbox.shift();
    } else if (item.attempts >= 6) {
      setTicket(item.ticket, 'fail', 'No guardado · la API no responde');
      outbox.shift();
    } else {
      // Red caída o cola llena (503): esperar con backoff y reenviar el MISMO evento.
      setTicket(item.ticket, 'retry', `Sin respuesta · reintento en ${2 ** item.attempts} s`);
      await new Promise(r => setTimeout(r, 1000 * 2 ** item.attempts));
    }
  }
  sending = false;
}

const LABELS = {
  search: 'Búsqueda', filter_applied: 'Filtro aplicado', restaurant_opened: 'Restaurante abierto',
  product_opened: 'Producto abierto', cart_added: 'Añadido al carrito', cart_removed: 'Quitado del carrito',
  session_abandoned: 'Sesión abandonada', order_submitted: 'Pedido confirmado',
};
function addTicket(type, extra) {
  const list = $('tape');
  list.querySelector('.empty')?.remove();
  const li = document.createElement('li');
  const detail = extra.product_id ? productName(extra.product_id) : extra.restaurant_id ? shopName(extra.restaurant_id) : '';
  li.innerHTML = `<time></time><strong></strong><span class="detail"></span><span class="state"></span>`;
  li.querySelector('time').textContent = new Date().toLocaleTimeString('es-ES');
  li.querySelector('strong').textContent = LABELS[type] || type;
  li.querySelector('.detail').textContent = [type, detail].filter(Boolean).join(' · ');
  list.prepend(li);
  return li;
}
function setTicket(li, kind, text) {
  li.dataset.state = kind;
  li.querySelector('.state').textContent = text;
}

// ── Catálogo ──────────────────────────────────────────────
const shopName = id => state.restaurants.find(r => r.restaurant_id === id)?.name || id;
const productName = id => state.products.find(p => p.product_id === id)?.product_name || id;
const menuOf = id => state.products.filter(p => p.restaurant_id === id);
const distance = (r) => Math.hypot((r.latitude - SOL[0]) * 111.3, (r.longitude - SOL[1]) * 84.3);   // km aprox.

async function loadCatalog() {
  try {
    const response = await fetch('/api/demo-catalog', {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    state.restaurants = data.restaurants; state.products = data.products;
    const cities = [...new Set(state.restaurants.map(r => r.city_id))];
    $('city').replaceChildren(...cities.map(c => new Option(c[0].toUpperCase() + c.slice(1), c)));
    state.city = cities[0] || 'madrid';
    renderHome();
  } catch (error) {
    $('restaurants').innerHTML = '';
    notice(`No se pudo cargar el catálogo (${error.message}). Comprueba que la API Atlas está arrancada.`);
  }
}

function visibleRestaurants() {
  const q = state.query.toLowerCase();
  let list = state.restaurants.filter(r => r.city_id === state.city);
  if (q) list = list.filter(r => r.name.toLowerCase().includes(q) || menuOf(r.restaurant_id).some(p => p.product_name.toLowerCase().includes(q)));
  if (state.filters.has('cheap')) list = list.filter(r => menuOf(r.restaurant_id).some(p => p.price_minor <= 1000));
  if (state.filters.has('near')) list = [...list].sort((a, b) => distance(a) - distance(b));
  return list;
}

function monogram(name) {
  const hue = [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);
  return {text: name.split(' ').filter(w => w.length > 2).map(w => w[0]).join('').slice(0, 2).toUpperCase(),
          style: `--mono:${hue}`};
}

function renderHome() {
  const list = visibleRestaurants();
  const parts = [];
  if (state.query) parts.push(`«${state.query}»`);
  if (state.filters.has('cheap')) parts.push('platos hasta 10 €');
  if (state.filters.has('near')) parts.push('ordenados por cercanía a Sol');
  $('result-note').textContent = `${list.length} restaurantes${parts.length ? ' · ' + parts.join(', ') : ''}`;
  $('restaurants').replaceChildren(...list.map(r => {
    const menu = menuOf(r.restaurant_id);
    const from = Math.min(...menu.map(p => p.price_minor));
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    const mono = monogram(r.name);
    button.innerHTML = `<span class="monogram" style="${mono.style}"></span><span class="info"><strong></strong><small></small></span><span class="from"></span>`;
    button.querySelector('.monogram').textContent = mono.text;
    button.querySelector('strong').textContent = r.name;
    button.querySelector('small').textContent = `${menu.length} platos · ${distance(r).toFixed(1).replace('.', ',')} km de Sol`;
    button.querySelector('.from').textContent = `desde ${money(from)}`;
    button.addEventListener('click', () => openShop(r.restaurant_id));
    li.append(button);
    return li;
  }));
  if (!list.length) $('restaurants').innerHTML = '<li class="empty">Ningún restaurante coincide. Prueba otra búsqueda o quita un filtro.</li>';
}

// ── Navegación ────────────────────────────────────────────
function show(view) {
  state.view = view;
  for (const v of ['home', 'restaurant', 'cart', 'order']) $('view-' + v).hidden = v !== view;
  $('back').hidden = view === 'home' || view === 'order';
  $('city').disabled = state.cart.size > 0 || view === 'order';
  renderCartBar();
  window.scrollTo({top: 0});
}

function openShop(id) {
  state.shop = state.restaurants.find(r => r.restaurant_id === id);
  track('restaurant_opened', 'restaurants', {restaurant_id: id});
  const mono = monogram(state.shop.name);
  $('shop-mono').textContent = mono.text; $('shop-mono').style = mono.style;
  $('shop-name').textContent = state.shop.name;
  $('shop-meta').textContent = `${distance(state.shop).toFixed(1).replace('.', ',')} km de Sol · restaurante ficticio`;
  renderMenu();
  show('restaurant');
}

function renderMenu() {
  $('menu').replaceChildren(...menuOf(state.shop.restaurant_id).map(p => {
    const li = document.createElement('li');
    const qty = state.cart.get(p.product_id) || 0;
    li.innerHTML = `<button type="button" class="dish"><strong></strong><span></span></button><span class="in-cart"></span>`;
    li.querySelector('strong').textContent = p.product_name;
    li.querySelector('.dish span').textContent = money(p.price_minor);
    li.querySelector('.in-cart').textContent = qty ? `${qty} en el carrito` : '';
    li.querySelector('.dish').addEventListener('click', () => openProduct(p.product_id));
    return li;
  }));
}

function openProduct(id) {
  state.product = state.products.find(p => p.product_id === id);
  track('product_opened', 'menu', {restaurant_id: state.product.restaurant_id, product_id: id});
  $('product-name').textContent = state.product.product_name;
  $('product-price').textContent = money(state.product.price_minor);
  $('product-origin').textContent = state.product.name_kind === 'public_historical'
    ? 'Nombre tomado del catálogo público de Glovo; precio ficticio.' : 'Plato y precio ficticios.';
  $('product').showModal();
}

// ── Carrito ───────────────────────────────────────────────
function cartShop() { return state.cart.size ? state.products.find(p => p.product_id === state.cart.keys().next().value).restaurant_id : null; }
function cartTotal() { let t = 0; for (const [id, q] of state.cart) t += state.products.find(p => p.product_id === id).price_minor * q; return t; }
function cartUnits() { let n = 0; for (const q of state.cart.values()) n += q; return n; }

function addToCart(product) {
  const owner = cartShop();
  if (owner && owner !== product.restaurant_id) {
    notice(`Tu carrito es de ${shopName(owner)}. Termina ese pedido o vacía el carrito para pedir aquí.`);
    return false;
  }
  if ((state.cart.get(product.product_id) || 0) >= 10 || cartUnits() >= 20) {
    notice('Máximo 10 unidades de un plato y 20 por pedido.');
    return false;
  }
  state.cart.set(product.product_id, (state.cart.get(product.product_id) || 0) + 1);
  pendingCheckout = null;                               // otra cesta = otro pedido
  track('cart_added', 'cart', {restaurant_id: product.restaurant_id, product_id: product.product_id});
  notice('');
  return true;
}
function removeFromCart(id) {
  const product = state.products.find(p => p.product_id === id);
  const left = (state.cart.get(id) || 0) - 1;
  if (left > 0) state.cart.set(id, left); else state.cart.delete(id);
  pendingCheckout = null;
  track('cart_removed', 'cart', {restaurant_id: product.restaurant_id, product_id: id});
}

function renderCartBar() {
  const show = state.cart.size > 0 && (state.view === 'home' || state.view === 'restaurant');
  $('cart-bar').hidden = !show;
  $('cart-count').textContent = `${cartUnits()} ${cartUnits() === 1 ? 'producto' : 'productos'}`;
  $('cart-bar-total').textContent = money(cartTotal());
}

function renderCart() {
  const owner = cartShop();
  $('cart-shop').textContent = owner ? shopName(owner) : 'El carrito está vacío.';
  $('cart-lines').replaceChildren(...[...state.cart].map(([id, q]) => {
    const p = state.products.find(x => x.product_id === id);
    const li = document.createElement('li');
    li.innerHTML = `<span class="name"></span><span class="qty"><button type="button" aria-label="Quitar uno">−</button><output></output><button type="button" aria-label="Añadir uno">+</button></span><span class="sub"></span>`;
    li.querySelector('.name').textContent = p.product_name;
    li.querySelector('output').textContent = q;
    li.querySelector('.sub').textContent = money(p.price_minor * q);
    const [minus, plus] = li.querySelectorAll('button');
    minus.addEventListener('click', () => { removeFromCart(id); renderCart(); });
    plus.addEventListener('click', () => { if (addToCart(p)) renderCart(); });
    return li;
  }));
  $('cart-total').textContent = money(cartTotal());
  $('checkout').disabled = !state.cart.size;
  $('abandon').disabled = !state.cart.size;
  if (!state.cart.size && state.view === 'cart') { show(state.shop ? 'restaurant' : 'home'); if (state.shop) renderMenu(); }
}

function abandon() {
  if (state.cart.size) track('session_abandoned', 'session');
  state.cart.clear(); state.shop = null; state.query = ''; state.filters.clear();
  $('search').value = '';
  document.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', 'false'));
  newSession();
  renderHome(); show('home');
}

// ── Checkout ──────────────────────────────────────────────
// El pedido (order_id, checkout_event_id, hora) se fija una vez. Si la red falla y se
// vuelve a pulsar, se reenvía el mismo pedido: la API responde 200 y no crea otro.
let pendingCheckout = null;

async function checkout() {
  const owner = cartShop();
  if (!owner) return;
  pendingCheckout ??= {
    order_id: crypto.randomUUID(), customer_id: state.customer, session_id: state.session,
    checkout_event_id: crypto.randomUUID(), event_time: new Date().toISOString(), restaurant_id: owner,
    items: [...state.cart].map(([product_id, quantity]) => ({product_id, quantity})),
  };
  const body = pendingCheckout;
  $('checkout').disabled = true; $('checkout').textContent = 'Confirmando…';
  const ticket = addTicket('order_submitted', {restaurant_id: owner});
  setTicket(ticket, 'sending', 'Enviando a /api/checkout');
  try {
    const response = await fetch('/api/checkout', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body), cache: 'no-store'});
    const data = await response.json().catch(() => ({}));
    if (response.status === 202 || response.status === 200) {
      setTicket(ticket, 'ok', response.status === 202 ? 'Pedido en cola · 202' : 'Pedido ya registrado · 200');
      pendingCheckout = null;
      state.order = {...data, items: body.items, restaurant_id: owner, created: new Date()};
      state.cart.clear();
      startTracking();
      return;
    }
    if (response.status === 409 && data.code === 'no_customer_run') {
      // Nada se ha creado: se puede volver a confirmar con los mismos datos.
      setTicket(ticket, 'fail', 'No guardado · no hay reparto activo');
      notice('Para repartir tu pedido hace falta la simulación de reparto. Abre el panel (enlace abajo), elige «Política local de prueba» o «IA local» y pulsa «Iniciar clientes y reparto». Después vuelve a confirmar.', true);
    } else {
      // 400 = cesta no válida para el catálogo actual: se descarta este intento.
      if (response.status < 500) pendingCheckout = null;
      setTicket(ticket, 'fail', `No guardado · ${response.status}`);
      notice(`El pedido no se ha confirmado: ${data.error || 'error ' + response.status}.`);
    }
  } catch (e) {
    setTicket(ticket, 'retry', 'Sin respuesta · vuelve a confirmar');
    notice('No hay conexión con la API. Tu pedido no está confirmado; pulsa «Confirmar pedido» otra vez y se reenviará el mismo.');
  } finally {
    $('checkout').disabled = !state.cart.size; $('checkout').textContent = 'Confirmar pedido';
  }
}

// ── Seguimiento ───────────────────────────────────────────
function startTracking() {
  const o = state.order;
  $('order-title').textContent = `Pedido de ${shopName(o.restaurant_id)}`;
  $('order-meta').textContent = `${money(o.amount_minor)} · pedido ${o.order_id.slice(0, 8)} · precio calculado por la API con el catálogo`;
  $('order-live').textContent = 'Pedido aceptado en la cola. Esperando a que ClickHouse lo publique…';
  paintSteps(null);
  show('order');
  clearInterval(state.poll);
  state.poll = setInterval(pollOrder, 2000);
  pollOrder();
}

function paintSteps(status) {
  const reached = STATUS_ORDER.indexOf(status);
  const finished = status === 'delivered';             // entregado = todos los pasos completados
  document.querySelectorAll('#steps li').forEach((li, i) => {
    li.dataset.done = i < reached || (finished && i === reached) ? 'yes' : 'no';
    if (i === reached && !finished) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
  });
}

async function pollOrder() {
  const o = state.order;
  if (!o) return;
  try {
    const response = await fetch(`/api/operations?run_id=${encodeURIComponent(o.run_id)}`, {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || response.status);
    const row = (data.orders || []).find(r => r.order_id === o.order_id);
    if (!row) return;
    paintSteps(row.status);
    const courier = row.courier_id && !/^0{8}-/.test(row.courier_id) ? `repartidor ${row.courier_id.slice(0, 8)}` : 'buscando repartidor';
    $('order-live').textContent = row.status === 'cancelled' ? 'Pedido cancelado en la simulación.'
      : `Leído de ClickHouse a las ${new Date().toLocaleTimeString('es-ES')} · ${courier}`;
    if (row.status === 'delivered' || row.status === 'cancelled') clearInterval(state.poll);
  } catch (error) {
    $('order-live').textContent = `No se pudo consultar el estado (${error.message}). Se reintenta cada 2 s.`;
  }
}

// ── Utilidades e inicio ───────────────────────────────────
function notice(text, withLink = false) {
  $('notice').hidden = !text;
  $('notice').textContent = text;
  if (withLink && text) {
    const a = document.createElement('a');
    a.href = '/'; a.target = '_blank'; a.rel = 'noopener'; a.textContent = 'Abrir el panel de operación';
    $('notice').append(' ', a);
  }
}

function bind() {
  $('search-form').addEventListener('submit', event => {
    event.preventDefault();
    state.query = $('search').value.trim().slice(0, 80);
    track('search', 'search');
    renderHome();
  });
  document.querySelectorAll('.chip').forEach(chip => chip.addEventListener('click', () => {
    const name = chip.dataset.filter;
    const on = !state.filters.has(name);
    on ? state.filters.add(name) : state.filters.delete(name);
    chip.setAttribute('aria-pressed', String(on));
    if (on) track('filter_applied', 'search');          // quitar un filtro no es "aplicar"
    renderHome();
  }));
  $('city').addEventListener('change', () => { state.city = $('city').value; renderHome(); });
  $('back').addEventListener('click', () => {
    if (state.view === 'cart' && state.shop) { renderMenu(); show('restaurant'); }
    else { renderHome(); show('home'); }
  });
  $('add').addEventListener('click', () => {
    if (addToCart(state.product)) { $('product').close(); renderMenu(); renderCartBar(); }
    else $('product').close();
  });
  $('cart-bar').addEventListener('click', () => { renderCart(); show('cart'); });
  $('checkout').addEventListener('click', checkout);
  $('abandon').addEventListener('click', abandon);
  $('again').addEventListener('click', () => {
    clearInterval(state.poll); state.order = null; state.shop = null;
    newSession(); renderHome(); show('home');
  });
  // Cerrar la pestaña con productos en el carrito = abandono. sendBeacon sobrevive al cierre.
  window.addEventListener('pagehide', () => {
    if (!state.cart.size || state.view === 'order') return;
    const event = {schema_version: 1, event_id: crypto.randomUUID(), session_id: state.session,
      event_time: new Date().toISOString(), event_type: 'session_abandoned', section: 'session',
      city_id: state.city, user_id: state.customer, source: SOURCE, source_kind: KIND};
    navigator.sendBeacon?.('/api/events', new Blob([JSON.stringify({events: [event]})], {type: 'application/json'}));
  });
}

state.customer = customerId();
newSession();
bind();
loadCatalog();
