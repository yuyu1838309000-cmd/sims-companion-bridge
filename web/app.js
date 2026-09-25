"use strict";
const $ = (selector) => document.querySelector(selector);
let activeWorld = null;
let conversationId = null;

function selectConversation(world) {
  const key = `conversationId:${world.world_id}:${world.branch_id}`;
  conversationId = sessionStorage.getItem(key) || `conversation-${crypto.randomUUID()}`;
  sessionStorage.setItem(key, conversationId);
}

document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", async () => {
  document.querySelectorAll(".tab,.panel").forEach((node) => node.classList.remove("active"));
  button.classList.add("active"); $(`#${button.dataset.tab}`).classList.add("active");
  if (button.dataset.tab === "world" || button.dataset.tab === "now") await loadWorld(true);
  if (button.dataset.tab === "diagnostics") await loadDiagnostics();
}));

async function api(path, options) {
  const response = await fetch(`/api/v0.1/${path}`, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.message || data.error || "Request failed");
  return data;
}
function setText(selector, value) { $(selector).textContent = value; }
function addMessage(role, value) {
  const article = document.createElement("article"); article.className = `message ${role}`;
  const label = document.createElement("span"); label.textContent = role === "user" ? "You" : "Companion";
  const message = document.createElement("p"); message.textContent = value;
  article.append(label, message); $("#messages").append(article); article.scrollIntoView({behavior: "smooth"});
}
async function loadChatHistory() {
  if (!conversationId) return;
  try {
    const data = await api(`chat/history?conversation_id=${encodeURIComponent(conversationId)}`);
    const list = $("#messages"); list.replaceChildren();
    if (!data.turns.length) {
      addMessage(
        "companion",
        activeWorld && activeWorld.current_snapshot
          ? "Game world connected. This window is read-only for now."
          : "Hello! This is a fully local mock conversation. Ask me about the demo world."
      );
      return;
    }
    data.turns.forEach((turn) => {
      addMessage("user", turn.user_text);
      addMessage("companion", turn.assistant_text);
    });
  } catch (error) {
    // Keep the current conversation surface usable if persisted history is unavailable.
  }
}
async function loadWorld(refreshChat = false) {
  try {
    const data = await api("world"); const world = data.world;
    const previousScope = activeWorld ? `${activeWorld.world_id}:${activeWorld.branch_id}` : null;
    activeWorld = world; selectConversation(world);
    const currentScope = `${world.world_id}:${world.branch_id}`;
    setText("#game-status", world.status); setText("#zone", world.zone);
    setText("#player-state", world.player_state); setText("#companion-state", world.companion_state);
    setText("#world-id", world.world_id); setText("#branch-id", world.branch_id);
    setText("#mode-label", world.current_snapshot ? "GAME CONNECTED" : "LOCAL DEMO");
    setText(
      "#world-notice",
      world.current_snapshot
        ? "Read-only game snapshot received. Game actions remain disabled."
        : "The demo world is offline. No game actions or autonomy are enabled."
    );
    const list = $("#events"); list.replaceChildren();
    data.events.forEach((event) => {
      const item = document.createElement("li"); const title = document.createElement("strong");
      title.textContent = event.type; const detail = document.createElement("small");
      detail.textContent = `${event.source} · ${new Date(event.wallclock).toLocaleString()}`;
      item.append(title, detail); list.append(item);
    });
    if (refreshChat && previousScope !== null && previousScope !== currentScope) await loadChatHistory();
    return true;
  } catch (error) {
    setText("#events", "Could not load world events.");
    return false;
  }
}
async function loadDiagnostics() {
  try {
    const data = await api("diagnostics"); setText("#connection", "Gateway online"); $("#connection").classList.add("online");
    setText("#protocol", data.protocol_version); setText("#gateway-health", data.status); setText("#backend", data.backend.id);
    const enabled = Object.entries(data.backend.capabilities).filter(([, value]) => value === true).map(([key]) => key);
    setText("#capabilities", enabled.join(", ") || "none"); setText("#recall", data.cross_surface_recall.enabled ? "Enabled" : "Disabled");
  } catch (error) { setText("#connection", "Gateway unavailable"); }
}
$("#chat-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const input = $("#chat-input"); const value = input.value.trim(); if (!value) return;
  const button = event.currentTarget.querySelector("button"); button.disabled = true;
  try {
    if (!await loadWorld(true)) throw new Error("Could not refresh the active world");
    addMessage("user", value); input.value = "";
    const response = await api("chat", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
      protocol_version: "0.1", surface: "sims", turn_source: "user", request_id: `request-${crypto.randomUUID()}`,
      conversation_id: conversationId, world_id: activeWorld.world_id, branch_id: activeWorld.branch_id, message: value
    })}); addMessage("companion", response.text);
  } catch (error) { addMessage("companion", `The local gateway rejected this turn: ${error.message}`); }
  finally { button.disabled = false; input.focus(); }
});
async function bootstrap() {
  await loadWorld(false);
  await loadChatHistory();
  await loadDiagnostics();
}
bootstrap();
