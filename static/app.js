/* Celebration Planner front end.
 * All server-provided and user-provided text is inserted as DOM text nodes only (never as
 * HTML strings), which keeps the page safe from script injection under the strict CSP.
 */
(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);

  const FIELDS = ["event_type", "event_name", "event_date", "guest_count", "total_budget", "currency", "city", "preferences"];
  const FIELD_LABELS = {
    event_type: "Type of event",
    event_name: "Event name",
    event_date: "Event date",
    guest_count: "Number of guests",
    total_budget: "Total budget",
    currency: "Currency",
    city: "City",
    preferences: "Style, theme or special wishes",
  };
  const CATEGORY_LABEL = { wedding: "Wedding", birthday: "Birthday", community: "Community event" };
  const PRIORITY_LABEL = { high: "High priority", medium: "Medium priority", low: "Low priority" };

  const state = { plan: null, request: null, aiEnabled: false, busy: false };

  /* ---------- small helpers ---------- */

  function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else node.setAttribute(key, value === true ? "" : String(value));
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function money(amount, currency) {
    try {
      return new Intl.NumberFormat(currency === "INR" ? "en-IN" : undefined, {
        style: "currency",
        currency,
        maximumFractionDigits: Number.isInteger(amount) ? 0 : 2,
      }).format(amount);
    } catch {
      return `${amount} ${currency}`;
    }
  }

  function parseISODate(iso) {
    const [year, month, day] = iso.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  function formatDate(iso, withWeekday = true) {
    return parseISODate(iso).toLocaleDateString(undefined, {
      weekday: withWeekday ? "short" : undefined,
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function todayISO() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  }

  class ApiError extends Error {
    constructor(status, body) {
      super(typeof body?.detail === "string" ? body.detail : "Request failed");
      this.status = status;
      this.detail = body?.detail;
    }
  }

  async function api(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 45000);
    try {
      const response = await fetch(path, {
        ...options,
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      });
      let body = null;
      try {
        body = await response.json();
      } catch {
        /* non-JSON body */
      }
      if (!response.ok) throw new ApiError(response.status, body);
      return body;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("The request took too long. Please try again.");
      if (error instanceof ApiError) throw error;
      throw new Error("Could not reach the server. Check your connection and try again.");
    } finally {
      clearTimeout(timer);
    }
  }

  function friendlyApiMessage(error) {
    if (error instanceof ApiError) {
      if (error.status === 429) return "You are going a little fast. Please wait a moment and try again.";
      if (error.status === 413) return "That request was too large.";
      if (typeof error.detail === "string") return error.detail;
    }
    return error.message || "Something went wrong. Please try again.";
  }

  /* ---------- form handling ---------- */

  function setFieldError(name, message) {
    const input = $(`#${name}`);
    const error = $(`#${name}-error`);
    if (!input || !error) return;
    if (message) {
      error.textContent = message;
      error.hidden = false;
      input.setAttribute("aria-invalid", "true");
    } else {
      error.textContent = "";
      error.hidden = true;
      input.removeAttribute("aria-invalid");
    }
  }

  function clearFormErrors() {
    FIELDS.forEach((name) => setFieldError(name, ""));
    const summary = $("#form-errors");
    summary.hidden = true;
    clear(summary);
  }

  function showFormErrors(errors) {
    // errors: [{ field, message }]
    errors.forEach(({ field, message }) => setFieldError(field, message));
    const summary = $("#form-errors");
    clear(summary);
    summary.append(
      h("p", {}, "Please fix the following:"),
      h(
        "ul",
        {},
        errors.map(({ field, message }) =>
          h("li", {}, h("a", { href: `#${field}` }, `${FIELD_LABELS[field] || field}: ${message}`))
        )
      )
    );
    summary.hidden = false;
    summary.focus();
    summary.querySelectorAll("a").forEach((link) =>
      link.addEventListener("click", (event) => {
        event.preventDefault();
        $(link.getAttribute("href"))?.focus();
      })
    );
  }

  function readForm() {
    const value = (id) => $(`#${id}`).value.trim();
    return {
      event_type: value("event_type"),
      event_name: value("event_name"),
      event_date: value("event_date"),
      guest_count: value("guest_count") === "" ? null : Number(value("guest_count")),
      total_budget: value("total_budget") === "" ? null : Number(value("total_budget")),
      currency: value("currency"),
      city: value("city"),
      preferences: value("preferences"),
    };
  }

  function validate(data) {
    const errors = [];
    if (!data.event_name) errors.push({ field: "event_name", message: "Enter a name for your event." });
    if (!data.event_date) errors.push({ field: "event_date", message: "Choose the event date." });
    else if (data.event_date < todayISO()) errors.push({ field: "event_date", message: "The date cannot be in the past." });
    if (!Number.isInteger(data.guest_count) || data.guest_count < 1 || data.guest_count > 5000)
      errors.push({ field: "guest_count", message: "Enter a whole number of guests from 1 to 5000." });
    if (!Number.isFinite(data.total_budget) || data.total_budget <= 0)
      errors.push({ field: "total_budget", message: "Enter a budget greater than zero." });
    return errors;
  }

  function errorsFromServer(error) {
    if (!(error instanceof ApiError) || !Array.isArray(error.detail)) return null;
    const mapped = error.detail
      .map((item) => {
        const loc = Array.isArray(item.loc) ? item.loc : [];
        const field = loc[loc.length - 1];
        return FIELDS.includes(field) ? { field, message: String(item.msg || "Invalid value.") } : null;
      })
      .filter(Boolean);
    return mapped.length ? mapped : null;
  }

  function setBusy(isBusy, button, idleText, busyText) {
    state.busy = isBusy;
    button.disabled = isBusy;
    button.textContent = isBusy ? busyText : idleText;
    button.setAttribute("aria-busy", String(isBusy));
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (state.busy) return;
    clearFormErrors();
    const data = readForm();
    const errors = validate(data);
    if (errors.length) {
      showFormErrors(errors);
      return;
    }

    const button = $("#submit-btn");
    const status = $("#form-status");
    setBusy(true, button, "Create my plan", "Creating your plan…");
    status.textContent = "Creating your plan…";
    try {
      const plan = await api("/api/plan", { method: "POST", body: JSON.stringify(data) });
      state.plan = plan;
      state.request = data;
      renderPlan(plan);
      status.textContent = "Your plan is ready.";
      const results = $("#results");
      results.hidden = false;
      results.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
      $("#results-heading").setAttribute("tabindex", "-1");
      $("#results-heading").focus();
    } catch (error) {
      const serverErrors = errorsFromServer(error);
      if (serverErrors) showFormErrors(serverErrors);
      else status.textContent = friendlyApiMessage(error);
    } finally {
      setBusy(false, button, "Create my plan", "Creating your plan…");
    }
  }

  /* ---------- rendering ---------- */

  function renderPlan(plan) {
    renderSummary(plan);
    renderBudget(plan);
    renderTimeline(plan);
    renderVendors(plan);
    renderIdeas(plan.ideas, "offline", false);
    clear($("#chat-log"));
    selectTab("tab-budget", false);
  }

  function renderSummary(plan) {
    const { summary, budget } = plan;
    const days = summary.days_until_event;
    const items = [
      ["Event", summary.event_name],
      ["Type", CATEGORY_LABEL[summary.event_type] || summary.event_type],
      ["Date", formatDate(summary.event_date)],
      ["Time to go", days === 0 ? "Today" : `${days} day${days === 1 ? "" : "s"}`],
      ["Guests", String(summary.guest_count)],
      ["Budget", money(budget.total, budget.currency)],
      ["Per guest", money(budget.per_guest, budget.currency)],
    ];
    if (summary.city) items.push(["City", summary.city]);

    const list = $("#summary");
    clear(list);
    items.forEach(([term, detail]) => list.append(h("div", {}, h("dt", {}, term), h("dd", {}, detail))));

    const notes = $("#notes");
    clear(notes);
    plan.notes.forEach((note) => notes.append(h("li", {}, note)));
  }

  function renderBudget(plan) {
    const { budget } = plan;
    const maxPercent = Math.max(...budget.lines.map((line) => line.percent));
    const panel = $("#panel-budget");
    clear(panel);

    const body = h("tbody");
    budget.lines.forEach((line) => {
      const bar = h("div", { class: "bar" });
      bar.style.width = `${Math.round((line.percent / maxPercent) * 100)}%`;
      body.append(
        h(
          "tr",
          {},
          h("th", { scope: "row" }, line.category),
          h("td", { class: "num" }, `${line.percent}%`),
          h("td", { class: "num" }, money(line.amount, budget.currency)),
          h("td", { class: "bar-cell", "aria-hidden": "true" }, bar)
        )
      );
    });

    panel.append(
      h("h3", {}, "Suggested budget split"),
      h(
        "table",
        {},
        h("caption", {}, `Where your ${money(budget.total, budget.currency)} could go`),
        h(
          "thead",
          {},
          h(
            "tr",
            {},
            h("th", { scope: "col" }, "Category"),
            h("th", { scope: "col", class: "num" }, "Share"),
            h("th", { scope: "col", class: "num" }, "Amount"),
            h("th", { scope: "col", class: "bar-cell", "aria-hidden": "true" }, "")
          )
        ),
        body,
        h(
          "tfoot",
          {},
          h(
            "tr",
            {},
            h("th", { scope: "row" }, "Total"),
            h("td", { class: "num" }, "100%"),
            h("td", { class: "num" }, money(budget.total, budget.currency)),
            h("td", { class: "bar-cell", "aria-hidden": "true" })
          )
        )
      )
    );
  }

  function renderTimeline(plan) {
    const panel = $("#panel-timeline");
    clear(panel);
    const list = h("ol", { class: "timeline" });
    plan.timeline.forEach((milestone) => {
      list.append(
        h(
          "li",
          {},
          h(
            "p",
            {},
            h("span", { class: "date" }, formatDate(milestone.due_date)),
            milestone.urgent ? h("span", { class: "badge badge-urgent" }, "Do now: behind schedule") : null
          ),
          h("p", { class: "title" }, milestone.title),
          h("p", { class: "hint" }, milestone.detail)
        )
      );
    });
    panel.append(h("h3", {}, "Your timeline"), list);
  }

  function checklistKey(plan) {
    const s = plan.summary;
    return `celebration-planner:v1:${s.event_type}|${s.event_name}|${s.event_date}`;
  }

  function loadChecked(key) {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || "[]");
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch {
      return new Set();
    }
  }

  function saveChecked(key, checked) {
    try {
      localStorage.setItem(key, JSON.stringify([...checked]));
    } catch {
      /* storage unavailable: ticks just will not persist */
    }
  }

  function renderVendors(plan) {
    const panel = $("#panel-vendors");
    clear(panel);
    const key = checklistKey(plan);
    const checked = loadChecked(key);
    const progress = h("p", { class: "progress", role: "status", "aria-live": "polite" });

    const updateProgress = () => {
      progress.textContent = `${checked.size} of ${plan.vendors.length} tasks done`;
    };

    const groups = new Map();
    plan.vendors.forEach((task, index) => {
      if (!groups.has(task.category)) groups.set(task.category, []);
      groups.get(task.category).push({ task, id: `v${index}` });
    });

    panel.append(h("h3", {}, "Vendor and task checklist"), progress);
    groups.forEach((entries, category) => {
      const fieldset = h("fieldset", {}, h("legend", {}, category));
      entries.forEach(({ task, id }) => {
        const taskId = `${category}|${task.task}`;
        const input = h("input", { type: "checkbox", id: `check-${id}` });
        input.checked = checked.has(taskId);
        input.addEventListener("change", () => {
          if (input.checked) checked.add(taskId);
          else checked.delete(taskId);
          saveChecked(key, checked);
          updateProgress();
        });
        fieldset.append(
          h(
            "label",
            { class: "check", for: `check-${id}` },
            input,
            h("span", {}, task.task, h("span", { class: `badge badge-${task.priority}` }, PRIORITY_LABEL[task.priority]))
          )
        );
      });
      panel.append(fieldset);
    });
    updateProgress();
  }

  function renderIdeas(ideas, source, announce) {
    const list = $("#ideas-list");
    clear(list);
    ideas.forEach((idea) => list.append(h("li", {}, h("h4", {}, idea.title), h("p", {}, idea.description))));
    $("#ideas-source").textContent =
      source === "ai" ? "Personalised for you by AI." : "Built-in suggestions based on your event details.";
    if (announce) {
      $("#ideas-status").textContent = source === "ai" ? "AI ideas are ready." : "AI is not available right now, so built-in ideas are shown.";
    }
  }

  /* ---------- tabs ---------- */

  function tabs() {
    return [...document.querySelectorAll('[role="tab"]')];
  }

  function selectTab(id, moveFocus = true) {
    tabs().forEach((tab) => {
      const selected = tab.id === id;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      const panel = document.getElementById(tab.getAttribute("aria-controls"));
      if (panel) panel.hidden = !selected;
      if (selected && moveFocus) tab.focus();
    });
  }

  function onTabKeydown(event) {
    const all = tabs();
    const index = all.indexOf(document.activeElement);
    if (index === -1) return;
    let next = null;
    if (event.key === "ArrowRight") next = all[(index + 1) % all.length];
    else if (event.key === "ArrowLeft") next = all[(index - 1 + all.length) % all.length];
    else if (event.key === "Home") next = all[0];
    else if (event.key === "End") next = all[all.length - 1];
    if (next) {
      event.preventDefault();
      selectTab(next.id);
    }
  }

  /* ---------- AI ideas and chat ---------- */

  async function onAiIdeas() {
    if (state.busy || !state.request) return;
    const button = $("#ai-ideas-btn");
    const status = $("#ideas-status");
    setBusy(true, button, "Personalise ideas with AI", "Thinking…");
    status.textContent = "Generating ideas…";
    try {
      const result = await api("/api/ideas", { method: "POST", body: JSON.stringify(state.request) });
      renderIdeas(result.ideas, result.source, true);
    } catch (error) {
      status.textContent = friendlyApiMessage(error);
    } finally {
      setBusy(false, button, "Personalise ideas with AI", "Thinking…");
    }
  }

  function addMessage(role, text) {
    const log = $("#chat-log");
    const speaker = role === "user" ? "You" : "Planner";
    log.append(h("p", { class: `msg msg-${role === "user" ? "user" : "bot"}` }, h("strong", {}, `${speaker}: `), text));
    log.scrollTop = log.scrollHeight;
  }

  async function onChat(event) {
    event.preventDefault();
    if (state.busy || !state.request) return;
    const input = $("#chat-input");
    const error = $("#chat-error");
    const question = input.value.trim();
    error.hidden = true;
    input.removeAttribute("aria-invalid");
    if (!question) {
      error.textContent = "Type a question first.";
      error.hidden = false;
      input.setAttribute("aria-invalid", "true");
      input.focus();
      return;
    }
    const button = $("#chat-send");
    addMessage("user", question);
    input.value = "";
    setBusy(true, button, "Send", "Thinking…");
    try {
      const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ plan: state.request, question }) });
      addMessage("bot", result.answer);
    } catch (err) {
      addMessage("bot", friendlyApiMessage(err));
    } finally {
      setBusy(false, button, "Send", "Thinking…");
      input.focus();
    }
  }

  /* ---------- export ---------- */

  function onDownload() {
    if (!state.plan) return;
    const blob = new Blob([JSON.stringify(state.plan, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = h("a", { href: url, download: "celebration-plan.json" });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /* ---------- init ---------- */

  async function init() {
    $("#event_date").min = todayISO();

    const prefs = $("#preferences");
    const count = $("#preferences-count");
    prefs.addEventListener("input", () => {
      count.textContent = String(prefs.value.length);
    });

    $("#plan-form").addEventListener("submit", onSubmit);
    $("#chat-form").addEventListener("submit", onChat);
    $("#ai-ideas-btn").addEventListener("click", onAiIdeas);
    $("#download-btn").addEventListener("click", onDownload);
    $("#print-btn").addEventListener("click", () => window.print());
    tabs().forEach((tab) => {
      tab.addEventListener("click", () => selectTab(tab.id));
      tab.addEventListener("keydown", onTabKeydown);
    });

    try {
      const health = await api("/api/health");
      state.aiEnabled = Boolean(health.ai_enabled);
    } catch {
      state.aiEnabled = false;
    }
    if (!state.aiEnabled) {
      $("#ask-hint").textContent =
        "Ask about your budget, timeline, vendors or ideas. Open-ended AI answers need an API key; until then you get answers from your plan.";
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
