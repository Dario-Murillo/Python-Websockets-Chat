const API = "http://localhost:8000";
const WS = "ws://localhost:8000";

// Fixed rooms — swap these out for API calls once GET /rooms is wired to the DB
const FIXED_ROOMS = [
  {
    id: "general",
    name: "General",
    topic: "Chat",
    description: "Open conversation for everyone.",
  },
  {
    id: "tech",
    name: "Tech",
    topic: "Dev",
    description: "Programming, tools, and everything code.",
  },
  {
    id: "random",
    name: "Random",
    topic: "Off-topic",
    description: "Anything goes. No rules here.",
  },
  {
    id: "ideas",
    name: "Ideas",
    topic: "Product",
    description: "Share what you're building or thinking about.",
  },
  {
    id: "help",
    name: "Help",
    topic: "Support",
    description: "Ask questions, get unstuck.",
  },
];

function app() {
  return {
    // ── State ──────────────────────────────────────────
    screen: "auth", // 'auth' | 'rooms' | 'chat'
    authMode: "login", // 'login' | 'register'

    loginData: { username: "", password: "" },
    registerData: { username: "", password: "" },

    error: "",
    isLoading: false,

    token: null,
    currentUser: null,

    rooms: FIXED_ROOMS,
    activeRoom: null,

    ws: null,
    wsStatus: "disconnected",
    messages: [],
    members: new Set(),
    messageText: "",

    // ── Init ───────────────────────────────────────────
    init() {
      const token = localStorage.getItem("relay_token");
      const user = localStorage.getItem("relay_user");
      if (token && user) {
        this.token = token;
        this.currentUser = user;
        this.screen = "rooms";
      }
    },

    // ── Auth ───────────────────────────────────────────
    async login() {
      if (!this.loginData.username || !this.loginData.password) {
        this.error = "Please fill in all fields.";
        return;
      }

      this.isLoading = true;
      this.error = "";

      try {
        // OAuth2PasswordRequestForm expects form-encoded data
        const form = new URLSearchParams();
        form.append("username", this.loginData.username);
        form.append("password", this.loginData.password);

        const res = await fetch(`${API}/users/token`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: form,
        });

        const data = await res.json();

        if (!res.ok) {
          this.error = data.detail ?? "Login failed.";
          return;
        }

        this.token = data.access_token;
        this.currentUser = this.loginData.username.toLowerCase();

        localStorage.setItem("relay_token", this.token);
        localStorage.setItem("relay_user", this.currentUser);

        this.loginData = { username: "", password: "" };
        this.screen = "rooms";
      } catch (e) {
        this.error = "Could not reach the server.";
      } finally {
        this.isLoading = false;
      }
    },

    async register() {
      if (!this.registerData.username || !this.registerData.password) {
        this.error = "Please fill in all fields.";
        return;
      }

      if (this.registerData.password.length < 8) {
        this.error = "Password must be at least 8 characters.";
        return;
      }

      this.isLoading = true;
      this.error = "";

      try {
        const res = await fetch(`${API}/users/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: this.registerData.username,
            password: this.registerData.password,
          }),
        });

        const data = await res.json();

        if (!res.ok) {
          this.error = data.detail ?? "Registration failed.";
          return;
        }

        // Auto-login after registration
        this.loginData = {
          username: this.registerData.username,
          password: this.registerData.password,
        };
        this.registerData = { username: "", password: "" };
        this.authMode = "login";
        await this.login();
      } catch (e) {
        this.error = "Could not reach the server.";
      } finally {
        this.isLoading = false;
      }
    },

    logout() {
      if (this.ws) this.ws.close();
      localStorage.removeItem("relay_token");
      localStorage.removeItem("relay_user");
      this.token = null;
      this.currentUser = null;
      this.activeRoom = null;
      this.messages = [];
      this.members = new Set();
      this.screen = "auth";
    },

    // ── Rooms ──────────────────────────────────────────
    joinRoom(room) {
      this.activeRoom = room;
      this.messages = [];
      this.members = new Set();
      this.screen = "chat";
      this.$nextTick(() => {
        this.connectWS();
        this.$refs.messageInput?.focus();
      });
    },

    leaveRoom() {
      if (this.ws) this.ws.close();
      this.ws = null;
      this.activeRoom = null;
      this.messages = [];
      this.members = new Set();
      this.screen = "rooms";
    },

    // ── WebSocket ──────────────────────────────────────
    connectWS() {
      this.wsStatus = "connecting";

      // Pass token as query param since WS handshake can't send Auth headers
      this.ws = new WebSocket(
        `${WS}/ws/${this.activeRoom.id}?token=${this.token}`,
      );

      this.ws.onopen = () => {
        this.wsStatus = "connected";
        // Announce join
        this.ws.send(
          JSON.stringify({
            type: "join",
            username: this.currentUser,
          }),
        );
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          this.handleMessage(data);
        } catch {
          /* ignore malformed */
        }
      };

      this.ws.onclose = () => {
        this.wsStatus = "disconnected";
        this.appendSystem("Disconnected from room.");
      };

      this.ws.onerror = () => {
        this.wsStatus = "disconnected";
        this.appendSystem("Connection error. Is the server running?");
      };
    },

    handleMessage(data) {
      // Someone left
      if (data.event === "disconnect") {
        this.members.delete(data.username);
        this.members = new Set(this.members); // trigger Alpine reactivity
        this.appendSystem(`${data.username ?? "Someone"} left the room.`);
        return;
      }

      // Someone joined
      if (data.type === "join") {
        this.members.add(data.username);
        this.members = new Set(this.members);
        this.appendSystem(`${data.username} joined the room.`);
        return;
      }

      // Regular message — skip own echo since we render optimistically
      if (data.username === this.currentUser) return;

      this.appendMessage({
        author: data.username ?? `user_${data.client_id}`,
        text: data.message,
        time: data.timestamp,
        own: false,
      });
    },

    // ── Send ───────────────────────────────────────────
    sendMessage() {
      const text = this.messageText.trim();
      if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;

      const timestamp = new Date().toISOString();

      this.ws.send(
        JSON.stringify({
          type: "message",
          username: this.currentUser,
          message: text,
          room_id: this.activeRoom.id,
          timestamp,
        }),
      );

      // Optimistic render
      this.appendMessage({
        author: this.currentUser,
        text,
        time: timestamp,
        own: true,
      });
      this.messageText = "";
    },

    // ── Message helpers ────────────────────────────────
    appendMessage({ author, text, time, own }) {
      const t = time
        ? new Date(time).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })
        : "";
      this.messages.push({ author, text, time: t, own, system: false });
      this.scrollToBottom();
    },

    appendSystem(text) {
      this.messages.push({
        text,
        system: true,
        own: false,
        author: "",
        time: "",
      });
      this.scrollToBottom();
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = this.$refs.messages;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },
  };
}
