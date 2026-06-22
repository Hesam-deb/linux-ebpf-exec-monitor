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
  let pendingEvents = null;
  let usageHistory = [];
  const chartAnimations = new Map();
  const chartGeometry = new Map();
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

  function chartCoordinates(values, maxValue = 100) {
    if (values.length === 0) return [];
    const width = 300;
    const height = 72;
    const denominator = Math.max(1, values.length - 1);
    return values
      .map((value, index) => {
        const x = (index / denominator) * width;
        const y = height - Math.min(maxValue, Math.max(0, value)) / maxValue * height + 5;
        return [x, y];
      });
  }

  function coordinatesToPoints(coordinates) {
    return coordinates.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  }

  function areaPath(coordinates) {
    if (coordinates.length === 0) return "";
    const pairs = coordinates.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`);
    return `M ${pairs[0]} L ${pairs.slice(1).join(" L ")} L 300,82 L 0,82 Z`;
  }

  function normalizedCoordinates(coordinates, length) {
    if (coordinates.length === length) return coordinates;
    if (coordinates.length === 0) return Array.from({ length }, () => [0, 77]);
    return Array.from({ length }, (_, index) => {
      const sourceIndex = Math.min(coordinates.length - 1, index);
      return coordinates[sourceIndex];
    });
  }

  function animateChart(id, nextCoordinates, areaId = null) {
    const element = document.getElementById(id);
    const previous = chartGeometry.get(id) || nextCoordinates;
    const length = Math.max(previous.length, nextCoordinates.length);
    const from = normalizedCoordinates(previous, length);
    const to = normalizedCoordinates(nextCoordinates, length);
    const priorAnimation = chartAnimations.get(id);
    if (priorAnimation) cancelAnimationFrame(priorAnimation);

    const start = performance.now();
    const duration = 260;
    function frame(now) {
      const progress = Math.min(1, (now - start) / duration);
      const eased = progress < 0.5
        ? 2 * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 2) / 2;
      const current = from.map(([fromX, fromY], index) => {
        const [toX, toY] = to[index];
        return [
          fromX + (toX - fromX) * eased,
          fromY + (toY - fromY) * eased,
        ];
      });
      element.setAttribute("points", coordinatesToPoints(current));
      if (areaId) document.getElementById(areaId).setAttribute("d", areaPath(current));
      if (progress < 1) chartAnimations.set(id, requestAnimationFrame(frame));
      else {
        chartGeometry.set(id, nextCoordinates);
        chartAnimations.delete(id);
      }
    }
    chartAnimations.set(id, requestAnimationFrame(frame));
  }

  function updateUsage(usage) {
    usageHistory = usage.history;
    const current = usage.current;
    updateText("monitor-cpu", current.monitor_cpu);
    updateText("monitor-memory", current.monitor_memory_mb);
    updateText("system-cpu", current.system_cpu);
    updateText("system-memory", current.system_memory);
    updateText("load-average", current.load_average);

    const monitorValues = usage.history.map((sample) => sample.monitor_cpu);
    const monitorMax = Math.max(100, ...monitorValues);
    animateChart(
      "monitor-cpu-line",
      chartCoordinates(monitorValues, monitorMax),
      "monitor-cpu-area",
    );
    animateChart(
      "system-cpu-line",
      chartCoordinates(usage.history.map((sample) => sample.system_cpu)),
    );
    animateChart(
      "system-memory-line",
      chartCoordinates(usage.history.map((sample) => sample.system_memory)),
    );
  }

  function inspectChart(shell, event) {
    if (usageHistory.length === 0) return;
    const rect = shell.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const index = Math.round(ratio * Math.max(0, usageHistory.length - 1));
    const sample = usageHistory[index];
    const x = usageHistory.length === 1 ? 0 : index / (usageHistory.length - 1) * 300;
    const kind = shell.dataset.chart;
    const crosshair = shell.querySelector(".chart-crosshair");
    crosshair.setAttribute("x1", x);
    crosshair.setAttribute("x2", x);

    const tooltip = shell.querySelector(".chart-tooltip");
    const left = Math.min(rect.width - 145, Math.max(0, ratio * rect.width - 70));
    tooltip.style.left = `${left}px`;

    if (kind === "monitor") {
      const max = Math.max(100, ...usageHistory.map((item) => item.monitor_cpu));
      const point = chartCoordinates(usageHistory.map((item) => item.monitor_cpu), max)[index];
      const marker = shell.querySelector(".monitor-marker");
      marker.setAttribute("cx", point[0]);
      marker.setAttribute("cy", point[1]);
      tooltip.textContent = `${t.cpu_usage}: ${sample.monitor_cpu}% · ${t.memory_usage}: ${sample.monitor_memory_mb} MB`;
    } else {
      const cpuPoint = chartCoordinates(usageHistory.map((item) => item.system_cpu))[index];
      const memoryPoint = chartCoordinates(usageHistory.map((item) => item.system_memory))[index];
      const cpuMarker = shell.querySelector(".system-marker");
      const memoryMarker = shell.querySelector(".memory-marker");
      cpuMarker.setAttribute("cx", cpuPoint[0]);
      cpuMarker.setAttribute("cy", cpuPoint[1]);
      memoryMarker.setAttribute("cx", memoryPoint[0]);
      memoryMarker.setAttribute("cy", memoryPoint[1]);
      tooltip.textContent = `${t.cpu_usage}: ${sample.system_cpu}% · ${t.memory_usage}: ${sample.system_memory}% · ${t.load_average}: ${sample.load_average}`;
    }
    shell.classList.add("is-inspecting");
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
    if (pendingEvents) {
      renderEventRows(pendingEvents);
      pendingEvents = null;
    }
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

  function renderEventRows(events) {
    const fragment = document.createDocumentFragment();
    if (events.length === 0) fragment.append(emptyRow());
    else events.forEach((event) => fragment.append(processRow(event)));
    eventsBody.replaceChildren(fragment);
    knownEventIds = new Set(events.map((event) => event.event_id));
    knownStatuses = new Map(events.map((event) => [event.event_id, event.status]));
    eventSignature = events.map((event) => `${event.event_id}:${event.status}`).join("|");
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
      if (selectedEventId) {
        pendingEvents = payload.events;
        updateLiveDurations(payload.events);
      } else {
        renderEventRows(payload.events);
      }
    } else {
      updateLiveDurations(payload.events);
    }
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

  document.querySelectorAll(".chart-shell").forEach((shell) => {
    shell.addEventListener("pointermove", (event) => inspectChart(shell, event));
    shell.addEventListener("pointerdown", (event) => inspectChart(shell, event));
    shell.addEventListener("pointerleave", () => shell.classList.remove("is-inspecting"));
    shell.addEventListener("pointercancel", () => shell.classList.remove("is-inspecting"));
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
