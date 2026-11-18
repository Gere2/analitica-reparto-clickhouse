"use strict";
const steps = [
  {
    title: "Madrid, live from ClickHouse",
    route: "/?view=simulated#tracking",
    selector: "#map",
    instruction: "Point to the Madrid map. Let a few courier positions update.",
  },
  {
    title: "Find a classmate’s order",
    route: "/?view=simulated#classroom-panel",
    selector: ".classroom-feed",
    instruction: "Click a classmate’s name. Their courier and order appear on the map.",
    empty: "No class orders are visible yet. You can continue and come back after someone orders."
  },
  {
    title: "Show the stored order",
    route: "/?view=simulated#classroom-panel",
    selector: ".classroom-lesson",
    open: ".classroom-lesson",
    instruction: "Read the selected order’s status and courier. If needed, choose a name above first.",
  },
  {
    title: "A model makes a decision",
    route: "/?view=ai#customers",
    selector: "#customers-body tr:first-child td:nth-child(2)",
    fallback: "#customers",
    instruction: "Point to one customer’s action and reason in the AI agents view.",
  },
  {
    title: "Two public datasets",
    route: "/?view=real#datasets",
    selector: "#datasets .datasets",
    instruction: "Compare Criteo and Glovo: rows, query times and contents.",
  },
  {
    title: "Customer Journey",
    route: "/analytics.html?panel=journey",
    selector: ".analysis-figure",
    instruction: "Read the ordered session funnel from its first step to checkout.",
  },
  {
    title: "Open the funnel query",
    route: "/analytics.html?panel=journey",
    selector: ".query-detail",
    text: "windowFunnel",
    openTarget: true,
    instruction: "Show the windowFunnel SQL and the query’s server measurement.",
  },
  {
    title: "ClickHouse Performance",
    route: "/analytics.html?panel=performance",
    selector: ".analysis-figure",
    text: "Storage by table",
    instruction: "Point to GPS history in Storage by table and compare its size with the other tables.",
  },
  {
    title: "Explain the table design",
    route: "/analytics.html?panel=performance",
    selector: "#analytics-content tr",
    text: "delivery_atlas.courier_positions",
    instruction: "Point to the GPS table’s engine, row count and sorting key.",
  },
  {
    title: "Completed query performance",
    route: "/analytics.html?panel=performance",
    selector: ".analysis-figure",
    text: "Completed query families",
    instruction: "Point to the recorded query times, then return to slide 9.",
  }
];
const frame = document.getElementById("demo");
const picker = document.getElementById("step-picker");
const status = document.getElementById("status");
const guide = document.querySelector(".guide");
const desktop = matchMedia("(min-width: 1200px)");
let index = 0;
let observer, timer, generation = 0;
let highlighted = null;
let currentRoute = "";
let ready = false;
let focusUntil = 0;
for (const [i, step] of steps.entries()) {
  const option = document.createElement("option");
  option.value = String(i);
  option.textContent = `${i + 1}. ${step.title}`;
  picker.append(option);
}
let layoutFrame = 0;
let programmaticScroll = false;
let targetResize;
function guideCandidates(rect) {
  const margin = 20, gap = 20;
  const width = guide.offsetWidth, height = guide.offsetHeight;
  return [
    {x: rect.right + gap, y: rect.top},
    {x: rect.left - width - gap, y: rect.top},
    {x: rect.left, y: rect.bottom + gap},
    {x: rect.right - width, y: rect.top - height - gap},
    {x: innerWidth - width - margin, y: margin},
    {x: margin, y: innerHeight - height - margin},
    {x: innerWidth - width - margin, y: innerHeight - height - margin},
    {x: margin, y: margin}
  ].map(p => ({
    x: Math.max(margin, Math.min(innerWidth - width - margin, p.x)),
    y: Math.max(margin, Math.min(innerHeight - height - margin, p.y))
  }));
}
function intersects(p, rect) {
  const gap = 12;
  return p.x < rect.right + gap && p.x + guide.offsetWidth > rect.left - gap
    && p.y < rect.bottom + gap && p.y + guide.offsetHeight > rect.top - gap;
}
function placeGuide(p) {
  guide.style.left = Math.round(p.x) + "px";
  guide.style.top = Math.round(p.y) + "px";
}
function positionGuide() {
  if (!desktop.matches) return;
  const rect = highlighted?.getBoundingClientRect();
  if (!rect) {
    placeGuide({x: innerWidth - guide.offsetWidth - 20, y:20});
    return;
  }
  const free = guideCandidates(rect).find(p => !intersects(p, rect));
  if (free) {
    guide.hidden = false;
    placeGuide(free);
  } else if (index === 4) {
    // Keep the bubble floating; never move the page while the user scrolls.
    placeGuide({x: innerWidth - guide.offsetWidth - 20, y:20});
  } else {
    // Reframe the page so the guide sits above a large target, never on its content.
    const win = frame.contentWindow;
    const desiredTop = guide.offsetHeight + 44;
    programmaticScroll = true;
    win.scrollBy({top: rect.top - desiredTop, behavior:"instant"});
    placeGuide({x: innerWidth - guide.offsetWidth - 20, y:20});
    programmaticScroll = false;
  }
}
function schedulePosition() {
  if (layoutFrame || programmaticScroll) return;
  layoutFrame = requestAnimationFrame(() => {
    layoutFrame = 0;
    positionGuide();
  });
}
function clearHighlight() {
  highlighted?.removeAttribute("data-tour-highlight");
  highlighted = null;
  targetResize?.disconnect();
}
function targetFor(step) {
  const doc = frame.contentDocument;
  const candidates = [...doc.querySelectorAll(step.selector)];
  return candidates.find(el => (!step.text || el.textContent.includes(step.text)) && el.getClientRects().length)
    || (step.fallback && doc.querySelector(step.fallback));
}
function reveal(scroll = false) {
  if (!ready) return false;
  const step = steps[index];
  const target = targetFor(step);
  if (!target) return false;
  if (step.open) {
    const details = frame.contentDocument.querySelector(step.open);
    if (details) details.open = true;
  }
  if (step.openTarget) target.open = true;
  if (highlighted !== target) {
    clearHighlight();
    highlighted = target;
    target.setAttribute("data-tour-highlight", "");
    targetResize?.disconnect();
    targetResize = new ResizeObserver(schedulePosition);
    targetResize.observe(target);
  }
  const rect = target.getBoundingClientRect();
  if (scroll || (index !== 4 && Date.now() < focusUntil && (rect.top >= innerHeight || rect.bottom <= 0))) {
    target.scrollIntoView({behavior: "instant", block: index === 4 ? "start" : "center"});
    if (index === 4 && scroll) {
      frame.contentWindow.scrollBy({top: -(guide.offsetHeight + 44), behavior: "instant"});
    }
  }
  const doc = frame.contentDocument;
  const error = [...doc.querySelectorAll("#error, #analytics-error")].find(el => !el.hidden && el.textContent.trim());
  if (error) {
    status.textContent = "The dashboard cannot load data. Check its error message, then retry.";
  } else if (index === 0 && doc.querySelector("#freshness")?.textContent === "No positions") {
    status.textContent = "Waiting for published positions. You can continue while the map loads.";
  } else if (index === 1 && !target.querySelector("button")) {
    status.textContent = step.empty;
  } else if (index === 2 && frame.contentDocument.querySelector("#lesson-result")?.hidden) {
    status.textContent = "Choose a class order to display its ClickHouse row.";
  } else {
    status.textContent = "";
  }
  schedulePosition();
  return true;
}
function bindDocument() {
  if (!desktop.matches || frame.src === "about:blank") return;
  if (!frame.contentDocument) {
    ready = false;
    currentRoute = "";
    status.textContent = "Return to a demo step using the route menu.";
    return;
  }
  ready = true;
  observer?.disconnect();
  const doc = frame.contentDocument;
  currentRoute = frame.contentWindow.location.pathname + frame.contentWindow.location.search + frame.contentWindow.location.hash;
  const style = doc.createElement("style");
  style.textContent = '.guided-demo-link{display:none!important}body::before,body::after{content:;display:block;height:360px;pointer-events:none}[data-tour-highlight]{outline:3px solid #a17a27!important;outline-offset:5px!important;scroll-margin:25px}';
  doc.head.append(style);
  for (const link of doc.querySelectorAll('a[href^="https://"]')) {
    link.target = "_blank";
    link.rel = "noopener";
  }
  doc.addEventListener("keydown", shortcuts);
  frame.contentWindow.addEventListener("scroll", schedulePosition, {passive: true});
  let queued = false;
  observer = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {queued = false; reveal(false);});
  });
  observer.observe(doc.body, {childList: true, subtree: true});
  waitForTarget();
}
function waitForTarget() {
  clearTimeout(timer);
  const run = ++generation;
  const until = Date.now() + 15000;
  const check = () => {
    if (run !== generation) return;
    if (reveal(true)) return;
    if (Date.now() < until) {
      timer = setTimeout(check, 350);
    } else {
      status.textContent = steps[index].empty || "This section has no data yet. Check the dashboard message, retry, or continue.";
    }
  };
  check();
}
function showStep(next) {
  index = Math.max(0, Math.min(steps.length - 1, next));
  clearTimeout(timer);
  generation++;
  clearHighlight();
  focusUntil = Date.now() + 5000;
  const step = steps[index];
  picker.value = String(index);
  document.getElementById("step-title").textContent = step.title;
  document.getElementById("instruction").textContent = step.instruction;
  document.getElementById("step-count").textContent = `Step ${index + 1} of ${steps.length}`;
  document.getElementById("progress").value = index + 1;
  document.getElementById("back").disabled = index === 0;
  document.getElementById("next").textContent = index === steps.length - 1 ? "Finish" : "Next";
  status.textContent = "Opening the dashboard…";
  document.querySelector(".route-menu").open = false;
  positionGuide();
  const wanted = new URL(step.route, location.origin);
  const loaded = new URL(currentRoute || "/unloaded", location.origin);
  if (ready && loaded.pathname === wanted.pathname && loaded.search === wanted.search) {
    currentRoute = step.route;
    frame.contentWindow.history.replaceState(null, "", step.route);
    waitForTarget();
  } else {
    ready = false;
    observer?.disconnect();
    currentRoute = step.route;
    frame.src = step.route;
  }
}
function nextStep() {
  if (index < steps.length - 1) {
    showStep(index + 1);
    document.getElementById("step-content").focus();
  } else {
    location.href = "/?tour=off";
  }
}
function shortcuts(event) {
  if (!event.altKey || event.ctrlKey || event.metaKey) return;
  if (event.key === "ArrowRight") { event.preventDefault(); nextStep(); }
  if (event.key === "ArrowLeft") { event.preventDefault(); showStep(index - 1); }
}
frame.addEventListener("load", bindDocument);
document.getElementById("next").addEventListener("click", nextStep);
document.getElementById("back").addEventListener("click", () => showStep(index - 1));
document.getElementById("reveal").addEventListener("click", waitForTarget);
picker.addEventListener("change", () => showStep(Number(picker.value)));
document.addEventListener("keydown", shortcuts);
window.addEventListener("resize", schedulePosition);
new ResizeObserver(schedulePosition).observe(guide);
window.addEventListener("pagehide", () => {clearTimeout(timer); observer?.disconnect(); targetResize?.disconnect(); cancelAnimationFrame(layoutFrame);});
desktop.addEventListener("change", () => {
  clearTimeout(timer);
  generation++;
  observer?.disconnect();
  ready = false;
  currentRoute = "";
  if (desktop.matches) showStep(index);
  else frame.src = "about:blank";
});
if (desktop.matches) showStep(index);
