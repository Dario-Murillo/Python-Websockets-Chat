const BACKEND_WS = "ws://localhost:8000";

// ─── STATE ───────────────────────────────────────────────
let ws = null;
let username = "";
let roomId = "";
const clientId = Date.now();
const members = new Set();

// ─── DOM REFS ─────────────────────────────────────────────
const lobbyScreen = document.getElementById("lobby");
const chatScreen = document.getElementById("chat");
const joinForm = document.getElementById("joinForm");
const usernameInput = document.getElementById("usernameInput");
const roomInput = document.getElementById("roomInput");
const lobbyError = document.getElementById("lobbyError");

const roomLabel = document.getElementById("roomLabel");
const userLabel = document.getElementById("userLabel");
const headerRoom = document.getElementById("headerRoom");
const memberList = document.getElementById("memberList");
const messages = document.getElementById("messages");
const messageForm = document.getElementById("messageForm");
const messageInput = document.getElementById("messageInput");
const connStatus = document.getElementById("connectionStatus");
const leaveBtn = document.getElementById("leaveBtn");

// ─── LOBBY ───────────────────────────────────────────────
joinForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const u = usernameInput.value.trim();
  const r = roomInput.value.trim();

  if (!u || !r) {
    lobbyError.classList.remove("hidden");
    return;
  }

  lobbyError.classList.add("hidden");
  username = u;
  roomId = r;
  enterChat();
});

// ─── CHAT SETUP ──────────────────────────────────────────
function enterChat() {
  // Update UI labels
  roomLabel.textContent = roomId;
  userLabel.textContent = username;
  headerRoom.textContent = roomId;

  // Switch screens
  lobbyScreen.classList.remove("active");
  chatScreen.classList.add("active");

  // Connect WebSocket
  connectWS();

  // Focus input
  messageInput.focus();
}

function leaveChat() {
  if (ws) {
    ws.close();
    ws = null;
  }
  members.clear();
  renderMembers();
  messages.innerHTML = "";

  chatScreen.classList.remove("active");
  lobbyScreen.classList.add("active");
  usernameInput.value = "";
  roomInput.value = "";
}

leaveBtn.addEventListener("click", leaveChat);

// ─── WEBSOCKET ───────────────────────────────────────────
function connectWS() {
  setStatus("connecting");

  ws = new WebSocket(`${BACKEND_WS}/ws/${roomId}/${clientId}`);

  ws.onopen = () => {
    setStatus("connected");
    addMember(username, true);

    // Announce arrival
    ws.send(JSON.stringify({ type: "join", username }));
  };

  ws.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }
    handleMessage(data);
  };

  ws.onclose = () => {
    setStatus("disconnected");
    appendSystemMessage("Disconnected from room.");
  };

  ws.onerror = () => {
    setStatus("disconnected");
    appendSystemMessage("Connection error. Is the server running?");
  };
}

// ─── MESSAGE HANDLING ────────────────────────────────────
function handleMessage(data) {
  // System events
  if (data.event === "disconnect") {
    removeMember(data.username);
    appendSystemMessage(`${data.username ?? "Someone"} left the room.`);
    return;
  }

  if (data.type === "join") {
    addMember(data.username);
    appendSystemMessage(`${data.username} joined the room.`);
    return;
  }

  // Regular message — ignore echo of own messages (we optimistically render them)
  if (data.client_id === clientId) return;

  appendMessage({
    author: data.username ?? `user_${data.client_id}`,
    text: data.message,
    time: data.timestamp,
    own: false,
  });
}

// ─── SEND MESSAGE ────────────────────────────────────────
messageForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

  const payload = {
    type: "message",
    username,
    message: text,
    client_id: clientId,
    room_id: roomId,
    timestamp: new Date().toISOString(),
  };

  ws.send(JSON.stringify(payload));

  // Optimistic render
  appendMessage({ author: username, text, time: payload.timestamp, own: true });

  messageInput.value = "";
});

// ─── RENDER HELPERS ──────────────────────────────────────
function appendMessage({ author, text, time, own }) {
  const el = document.createElement("div");
  el.className = `msg${own ? " own" : ""}`;

  const t = time
    ? new Date(time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  el.innerHTML = `
    <div class="msg-meta">
      <span class="msg-author">${escHtml(author)}</span>
      <span class="msg-time">${t}</span>
    </div>
    <div class="msg-divider"></div>
    <div class="msg-text">${escHtml(text)}</div>
  `;

  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function appendSystemMessage(text) {
  const el = document.createElement("div");
  el.className = "msg system";
  el.innerHTML = `<div class="msg-text">${escHtml(text)}</div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

// ─── MEMBER LIST ─────────────────────────────────────────
function addMember(name, isSelf = false) {
  if (!name || members.has(name)) return;
  members.add(name);
  renderMembers(isSelf ? name : null);
}

function removeMember(name) {
  members.delete(name);
  renderMembers();
}

function renderMembers(selfName) {
  memberList.innerHTML = "";
  members.forEach((name) => {
    const li = document.createElement("li");
    const isSelf = name === username;
    if (isSelf) li.classList.add("self");
    li.textContent = isSelf ? `${name} (you)` : name;
    memberList.appendChild(li);
  });
}

// ─── STATUS ──────────────────────────────────────────────
function setStatus(state) {
  connStatus.className = `conn-status ${state}`;
  connStatus.querySelector(".status-text").textContent = state;
}

// ─── UTILS ───────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
