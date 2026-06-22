(() => {
  "use strict";

  const configElement = document.getElementById("dashboard-config");
  if (!configElement) return;

  const config = JSON.parse(configElement.textContent);
  const t = config.translations;
  const eventsBody = document.getElementById("events-body");
  const openStorageKey = "ebpf-monitor-open-details";
  let storedOpenEventIds = [];
  try {
    storedOpenEventIds = JSON.parse(sessionStorage.getItem(openStorageKey) || "[]");
  } catch {
    sessionStorage.removeItem(openStorageKey);
  }
  let openEventIds = new Set(storedOpenEventIds);
  let requestInFlight = false;

  const text = (value) => document.createTextNode(String(value));

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.append(text(value));
    return node;
  }

  function technicalValue(value) {
    return value === null || value === undefined || value === "" ? t.not_available : value;
  }

  function detailItem(label, value, wide = false) {
    const wrapper = element("div", wide ? "detail-wide" : "");
    wrapper.append(element("dt", "", label));
    wrapper.append(element("dd", "technical-value", technicalValue(value)));
    return wrapper;
  }

  function processRow(event) {
    const row = document.createElement("tr");
    row.dataset.eventId = event.event_id;

    const commandCell = document.createElement("td");
    commandCell.append(element("span", "command-cell technical-value", event.command));
    row.append(commandCell);

    const statusCell = document.createElement("td");
    statusCell.append(
      element(
        "span",
        `process-status process-status-${event.status}`,
        event.status === "running" ? t.status_running : t.status_exited,
      ),
    );
    row.append(statusCell);

    row.append(element("td", "technical-value pid-cell", event.pid));

    const userCell = document.createElement("td");
    userCell.append(element("span", "user-cell", event.username));
    userCell.append(element("small", "technical-value", `UID ${event.uid}`));
    row.append(userCell);

    row.append(element("td", "technical-value timestamp-cell", event.duration));

    const detailsCell = document.createElement("td");
    const details = element("details", "process-details");
    details.dataset.eventId = event.event_id;
    details.open = openEventIds.has(event.event_id);
    details.addEventListener("toggle", () => {
      if (details.open) openEventIds.add(event.event_id);
      else openEventIds.delete(event.event_id);
      sessionStorage.setItem(openStorageKey, JSON.stringify([...openEventIds]));
    });
    details.append(element("summary", "", t.details));

    const list = document.createElement("dl");
    list.append(detailItem(t.pid, event.pid));
    list.append(detailItem(t.ppid, event.ppid));
    list.append(detailItem(t.uid, event.uid));
    list.append(detailItem(t.started_at, event.timestamp));
    list.append(detailItem(t.finished_at, event.exit_timestamp));
    list.append(detailItem(t.exit_code, event.exit_code));
    list.append(detailItem(t.signal, event.signal));
    list.append(detailItem(t.executable, event.executable, true));
    list.append(detailItem(t.arguments, event.arguments, true));
    details.append(list);
    detailsCell.append(details);
    row.append(detailsCell);

    return row;
  }

  function emptyRow() {
    const row = document.createElement("tr");
    const cell = element("td", "empty-state");
    cell.colSpan = 6;
    cell.append(element("span", "empty-icon", "⌁"));
    cell.append(element("strong", "", t.empty_title));

    const help = element("small");
    help.append(text(`${t.empty_help} `));
    help.append(element("code", "", "ls"));
    help.append(text(` ${t.or} `));
    help.append(element("code", "", "whoami"));
    help.append(text(` ${t.empty_suffix}`));
    cell.append(help);
    row.append(cell);
    return row;
  }

  function updateMonitor(payload) {
    const badge = document.getElementById("monitor-status");
    badge.className = `monitor-badge monitor-badge-${payload.monitor_status}`;
    badge.replaceChildren(element("span", "status-dot"));
    const labels = {
      active: t.status_active,
      starting: t.status_starting,
      error: t.status_error,
    };
    badge.append(text(labels[payload.monitor_status] || t.status_error));

    const errorPanel = document.getElementById("monitor-error");
    document.getElementById("monitor-error-message").textContent = payload.monitor_error || "";
    errorPanel.classList.toggle("is-hidden", !payload.monitor_error);
  }

  function updateDashboard(payload) {
    const stats = payload.stats;
    document.getElementById("total-events").textContent = stats.total_events;
    document.getElementById("retained-events").textContent = stats.retained_events;
    document.getElementById("max-events").textContent = stats.max_events;
    document.getElementById("running-processes").textContent = stats.running_processes;
    document.getElementById("last-update").textContent =
      stats.retained_events === 0 ? t.waiting : stats.last_update;
    document.getElementById("latest-command").textContent = stats.latest_command;
    const metrics = payload.monitor_metrics;
    document.getElementById("event-rate").textContent = metrics.event_rate;
    document.getElementById("kernel-events").textContent = metrics.kernel_events;
    document.getElementById("exec-events").textContent = metrics.exec_events;
    document.getElementById("exit-events").textContent = metrics.exit_events;
    document.getElementById("lost-events").textContent = metrics.lost_events;
    const bufferHealth = document.getElementById("buffer-health");
    bufferHealth.textContent = metrics.buffer_healthy ? t.buffer_healthy : t.buffer_degraded;
    bufferHealth.className = `buffer-health ${
      metrics.buffer_healthy ? "buffer-healthy" : "buffer-degraded"
    }`;
    updateMonitor(payload);

    const currentIds = new Set(payload.events.map((event) => event.event_id));
    openEventIds = new Set([...openEventIds].filter((eventId) => currentIds.has(eventId)));
    sessionStorage.setItem(openStorageKey, JSON.stringify([...openEventIds]));

    const fragment = document.createDocumentFragment();
    if (payload.events.length === 0) fragment.append(emptyRow());
    else payload.events.forEach((event) => fragment.append(processRow(event)));
    eventsBody.replaceChildren(fragment);
  }

  async function poll() {
    if (requestInFlight || document.hidden) return;
    requestInFlight = true;
    try {
      const response = await fetch(config.api_url, {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      updateDashboard(await response.json());
    } catch (error) {
      console.error("Dashboard update failed", error);
    } finally {
      requestInFlight = false;
    }
  }

  document.querySelectorAll(".process-details").forEach((details) => {
    if (openEventIds.has(details.dataset.eventId)) details.open = true;
    details.addEventListener("toggle", () => {
      if (details.open) openEventIds.add(details.dataset.eventId);
      else openEventIds.delete(details.dataset.eventId);
      sessionStorage.setItem(openStorageKey, JSON.stringify([...openEventIds]));
    });
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) poll();
  });
  poll();
  window.setInterval(poll, config.poll_interval_ms);
})();
