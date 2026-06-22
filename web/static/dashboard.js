(() => {
  "use strict";

  const configElement = document.getElementById("dashboard-config");
  if (!configElement) return;

  const config = JSON.parse(configElement.textContent);
  const t = config.translations;
  const eventsBody = document.getElementById("events-body");
  const openStorageKey = "ebpf-monitor-open-details";
  let selectedEventId = sessionStorage.getItem(openStorageKey);
  let requestInFlight = false;
  let knownEventIds = new Set(
    [...eventsBody.querySelectorAll("tr[data-event-id]")].map((row) => row.dataset.eventId),
  );
  let knownStatuses = new Map(
    [...eventsBody.querySelectorAll("tr[data-event-id]")].map((row) => [
      row.dataset.eventId,
      row.dataset.status,
    ]),
  );
  let eventSignature = [...eventsBody.querySelectorAll("tr[data-event-id]")]
    .map((row) => `${row.dataset.eventId}:${row.dataset.status}`)
    .join("|");

  const text = (value) => document.createTextNode(String(value));

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined && value !== null) node.append(text(value));
    return node;
  }

  function updateText(id, value, animate = true) {
    const node = document.getElementById(id);
    const nextValue = String(value);
    if (node.textContent === nextValue) return;
    node.textContent = nextValue;
    if (!animate) return;
    node.classList.remove("value-pop");
    void node.offsetWidth;
    node.classList.add("value-pop");
  }

  function updateLiveDurations(events) {
    events.forEach((event) => {
      const row = eventsBody.querySelector(`tr[data-event-id="${CSS.escape(event.event_id)}"]`);
      const duration = row?.querySelector(".timestamp-cell");
      if (duration) duration.textContent = event.duration;
    });
  }

  function technicalValue(value) {
    return value === null || value === undefined || value === "" ? t.not_available : value;
  }

  function chartPoints(values, maxValue = 100) {
    if (values.length === 0) return "";
    const width = 300;
    const height = 72;
    const denominator = Math.max(1, values.length - 1);
    return values
      .map((value, index) => {
        const x = (index / denominator) * width;
        const y = height - Math.min(maxValue, Math.max(0, value)) / maxValue * height + 5;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }

  function areaPath(points) {
    if (!points) return "";
    const pairs = points.split(" ");
    return `M ${pairs[0]} L ${pairs.slice(1).join(" L ")} L 300,82 L 0,82 Z`;
  }

  function updateUsage(usage) {
    const current = usage.current;
    updateText("monitor-cpu", current.monitor_cpu);
    updateText("monitor-memory", current.monitor_memory_mb);
    updateText("system-cpu", current.system_cpu);
    updateText("system-memory", current.system_memory);
    updateText("load-average", current.load_average);

    const monitorValues = usage.history.map((sample) => sample.monitor_cpu);
    const monitorMax = Math.max(100, ...monitorValues);
    const monitorPoints = chartPoints(monitorValues, monitorMax);
    document.getElementById("monitor-cpu-line").setAttribute("points", monitorPoints);
    document.getElementById("monitor-cpu-area").setAttribute("d", areaPath(monitorPoints));
    document.getElementById("system-cpu-line").setAttribute(
      "points",
      chartPoints(usage.history.map((sample) => sample.system_cpu)),
    );
    document.getElementById("system-memory-line").setAttribute(
      "points",
      chartPoints(usage.history.map((sample) => sample.system_memory)),
    );
  }

  function detailItem(label, value, wide = false) {
    const wrapper = element("div", wide ? "detail-wide" : "");
    wrapper.append(element("dt", "", label));
    wrapper.append(element("dd", "technical-value", technicalValue(value)));
    return wrapper;
  }

  function closeSelectedDetails() {
    document.querySelectorAll(".process-details[open]").forEach((details) => {
      details.open = false;
    });
    selectedEventId = null;
    sessionStorage.removeItem(openStorageKey);
    document.body.classList.remove("detail-overlay-open");
  }

  function bindDetails(details) {
    details.open = details.dataset.eventId === selectedEventId;
    if (details.open) {
      details.classList.add("restored-selection");
      document.body.classList.add("detail-overlay-open");
    }

    details.addEventListener("toggle", () => {
      if (details.open) {
        details.classList.remove("restored-selection");
        document.querySelectorAll(".process-details[open]").forEach((other) => {
          if (other !== details) other.open = false;
        });
        selectedEventId = details.dataset.eventId;
        sessionStorage.setItem(openStorageKey, selectedEventId);
        document.body.classList.add("detail-overlay-open");
      } else if (selectedEventId === details.dataset.eventId) {
        selectedEventId = null;
        sessionStorage.removeItem(openStorageKey);
        document.body.classList.remove("detail-overlay-open");
      }
    });

    details.addEventListener("click", (event) => {
      if (event.target === details) closeSelectedDetails();
    });
  }

  function processRow(event) {
    const row = document.createElement("tr");
    row.dataset.eventId = event.event_id;
    row.dataset.status = event.status;
    if (!knownEventIds.has(event.event_id)) row.classList.add("is-new-event");
    else if (knownStatuses.get(event.event_id) !== event.status) row.classList.add("is-status-change");

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
    bindDetails(details);
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
    updateText("total-events", stats.total_events);
    updateText("retained-events", stats.retained_events);
    updateText("max-events", stats.max_events, false);
    updateText("running-processes", stats.running_processes);
    updateText("last-update", stats.retained_events === 0 ? t.waiting : stats.last_update, false);
    updateText("latest-command", stats.latest_command);
    const metrics = payload.monitor_metrics;
    updateText("event-rate", metrics.event_rate);
    updateText("kernel-events", metrics.kernel_events);
    updateText("exec-events", metrics.exec_events);
    updateText("exit-events", metrics.exit_events);
    updateText("lost-events", metrics.lost_events);
    const bufferHealth = document.getElementById("buffer-health");
    bufferHealth.textContent = metrics.buffer_healthy ? t.buffer_healthy : t.buffer_degraded;
    bufferHealth.className = `buffer-health ${
      metrics.buffer_healthy ? "buffer-healthy" : "buffer-degraded"
    }`;
    updateUsage(payload.usage);
    updateMonitor(payload);

    const currentIds = new Set(payload.events.map((event) => event.event_id));
    const nextEventSignature = payload.events
      .map((event) => `${event.event_id}:${event.status}`)
      .join("|");
    const listChanged = nextEventSignature !== eventSignature;
    if (selectedEventId && !currentIds.has(selectedEventId)) closeSelectedDetails();

    if (listChanged) {
      const fragment = document.createDocumentFragment();
      if (payload.events.length === 0) fragment.append(emptyRow());
      else payload.events.forEach((event) => fragment.append(processRow(event)));
      eventsBody.replaceChildren(fragment);
    } else {
      updateLiveDurations(payload.events);
    }

    knownEventIds = currentIds;
    knownStatuses = new Map(payload.events.map((event) => [event.event_id, event.status]));
    eventSignature = nextEventSignature;
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
    bindDetails(details);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSelectedDetails();
  });

  document.querySelector(".language-switch")?.addEventListener("click", (event) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    const destination = event.currentTarget.href;
    document.documentElement.classList.add("language-leaving");
    window.setTimeout(() => {
      window.location.assign(destination);
    }, 65);
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) poll();
  });
  poll();
  window.setInterval(poll, config.poll_interval_ms);
})();
