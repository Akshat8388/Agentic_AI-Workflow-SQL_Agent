const messages = document.getElementById("messages");
const inputBox = document.getElementById("inputBox");
const input = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const intro = document.getElementById("intro");
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const approvalModal = document.getElementById("approvalModal");
const approvalMessage = document.getElementById("approvalMessage");
const dbModal = document.getElementById("dbModal");
const dbConnectBtn = document.getElementById("dbConnectBtn");
const connectDbBtn = document.getElementById("connectDbBtn");
const cancelDbBtn = document.getElementById("cancelDbBtn");
const dbUriInput = document.getElementById("dbUriInput");
const sideBar = document.querySelector(".side-bar");
const toggleBtn = document.querySelector(".toggle-btn");
const chatcontainer = document.querySelector(".chat-container");
const chatList = document.getElementById("chatList");
const newChatBtn = document.getElementById("newChatBtn");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const mobileMenuBtn = document.getElementById("mobileMenuBtn");

let activated = false;
let db_path = "";
let db_type = ""; // "sample" or "custom"
let authToken = null;
let currentUsername = null;
let currentThreadId = crypto.randomUUID();

// --- Hide app layout until logged in ---
document.querySelector(".app-layout").style.display = "none";
document.querySelector(".header .buttons").style.display = "none";

// --- Typed.js ---
var typed = new Typed('.element', {
  strings: [
    'Connect your database and visualize insights instantly',
    'From SQL to smart charts — your AI data analyst',
    'Transform raw data into meaningful decisions',
  ],
  typeSpeed: 30,
  backSpeed: 30,
  loop: true
});

// --- Theme Toggle ---
const sunIcon = '<path d="M480-360q50 0 85-35t35-85q0-50-35-85t-85-35q-50 0-85 35t-35 85q0 50 35 85t85 35Zm0 80q-83 0-141.5-58.5T280-480q0-83 58.5-141.5T480-680q83 0 141.5 58.5T680-480q0 83-58.5 141.5T480-280ZM200-440H40v-80h160v80Zm720 0H760v-80h160v80ZM440-760v-160h80v160h-80Zm0 720v-160h80v160h-80ZM256-650l-101-97 57-59 96 100-52 56Zm492 496-97-101 53-55 101 97-57 59Zm-98-550 97-101 59 57-100 96-56-52ZM154-212l101-97 55 53-97 101-59-57Z"/>';
const moonIcon = '<path d="M480-120q-150 0-255-105T120-480q0-150 105-255t255-105q14 0 27.5 1t26.5 3q-41 29-65.5 75.5T444-660q0 90 63 153t153 63q55 0 101-24.5t75-65.5q2 13 3 26.5t1 27.5q0 150-105 255T480-120Z"/>';

// --- Password toggle ---
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  const isHidden = input.type === "password";
  input.type = isHidden ? "text" : "password";
  btn.querySelector(".eye-icon").style.display = isHidden ? "none" : "";
  btn.querySelector(".eye-off-icon").style.display = isHidden ? "" : "none";
}

// --- Tab switcher ---
function switchTab(tab) {
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const loginTab = document.getElementById("loginTab");
  const registerTab = document.getElementById("registerTab");

  if (tab === "login") {
    loginForm.style.display = "flex";
    registerForm.style.display = "none";
    loginTab.classList.add("active");
    registerTab.classList.remove("active");
  } else {
    loginForm.style.display = "none";
    registerForm.style.display = "flex";
    loginTab.classList.remove("active");
    registerTab.classList.add("active");
  }
}

// --- Login ---
async function handleLogin() {
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value.trim();
  const errorEl = document.getElementById("loginError");

  if (!username || !password) {
    errorEl.textContent = "Please fill in all fields";
    return;
  }

  try {
    const res = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (!res.ok) {
      errorEl.textContent = data.detail || "Login failed";
      return;
    }

    authToken = data.access_token;
    currentUsername = data.username;

    localStorage.setItem("authToken", authToken);
    localStorage.setItem("username", currentUsername);

    // Hide auth screen, show app
    document.getElementById("authScreen").style.display = "none";
    document.querySelector(".app-layout").style.display = "flex";
    document.querySelector(".header .buttons").style.display = "flex";
    document.getElementById("usernameDisplay").textContent = currentUsername;
    document.getElementById("sidebarAvatar").textContent = currentUsername.charAt(0).toUpperCase();

    loadThreads();

  } catch (err) {
    errorEl.textContent = "Server error. Try again.";
  }
}

// --- Register ---
async function handleRegister() {
  const username = document.getElementById("regUsername").value.trim();
  const email = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value.trim();
  const errorEl = document.getElementById("registerError");

  if (!username || !email || !password) {
    errorEl.textContent = "Please fill in all fields";
    return;
  }

  try {
    const res = await fetch("/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      errorEl.textContent = data.detail || "Registration failed";
      return;
    }

    errorEl.style.color = "#00bfa5";
    errorEl.textContent = "Registered! Please login.";
    setTimeout(() => switchTab("login"), 1000);

  } catch (err) {
    errorEl.textContent = "Server error. Try again.";
  }
}

// --- Logout ---
function handleLogout() {
  authToken = null;
  currentUsername = null;
  currentThreadId = crypto.randomUUID();
  messages.innerHTML = "";
  chatList.innerHTML = "";
  intro.style.display = "block";
  inputBox.classList.add("centered-input");
  inputBox.classList.remove("bottom-input");
  activated = false;
  db_path = "";

  localStorage.removeItem("authToken");
  localStorage.removeItem("username");

  // Hide app, show auth screen
  document.querySelector(".app-layout").style.display = "none";
  document.querySelector(".header .buttons").style.display = "none";
  document.getElementById("authScreen").style.display = "flex";
}

// --- Auth fetch wrapper ---
async function authFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      "Authorization": `Bearer ${authToken}`
    }
  });

  if (res.status === 401) {
    handleLogout();
    throw new Error("Unauthorized");
  }

  return res;
}

themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("light-mode");
  const isLight = document.body.classList.contains("light-mode");
  themeIcon.innerHTML = isLight ? sunIcon : moonIcon;
  themeIcon.setAttribute("fill", isLight ? "#1a1a1a" : "#FFFFFF");
});

// --- Helpers ---
function appendMessage(text, sender) {
  const msg = document.createElement("div");
  msg.classList.add("message", sender);
  msg.innerHTML = sender === "ai" ? marked.parse(text) : text;
  messages.appendChild(msg);
  messages.scrollTop = messages.scrollHeight;
  return msg;
}

function addTyping() {
  const typingDiv = document.createElement("div");
  typingDiv.classList.add("message", "ai");
  typingDiv.innerHTML = `
    <div class="typing">
      <div class="dot"></div>
      <div class="dot"></div>
      <div class="dot"></div>
    </div>`;
  messages.appendChild(typingDiv);
  messages.scrollTop = messages.scrollHeight;
  return typingDiv;
}

// --- Sample DB Toggle ---
document.querySelector(".db_btn").addEventListener("click", async () => {
    const btn = document.querySelector(".db_btn");
    const indicator = document.querySelector(".db_indicator");
    const label = btn.querySelector("p");

    if (db_path && db_type === "sample") {
        // disconnect sample DB
        db_path = "";
        db_type = "";
        indicator.style.backgroundColor = "red";
        label.textContent = "Try Sample DB";
        btn.style.background = "";
    } else if (db_type === "custom") {
        // custom DB is active, do nothing — user must disconnect via modal
        return;
    } else {
        try {
            const res = await authFetch("/sample-db");
            const data = await res.json();
            db_path = data.db_path;
            db_type = "sample";
            indicator.style.backgroundColor = "#32ff5e";
            label.textContent = "Try Sample DB";
            btn.style.transform = "scale(0.97)";
            setTimeout(() => (btn.style.transform = "scale(1)"), 200);
        } catch (err) {
            console.error("Failed to get sample DB:", err);
        }
    }
});

// --- DB Modal ---
dbConnectBtn.addEventListener("click", () => {
  const disconnectBtn = document.getElementById("disconnectDbBtn");
  const successEl = document.getElementById("dbConnectSuccess");
  const connectBtn = document.getElementById("connectDbBtn");
  const errorEl = document.getElementById("dbConnectError");

  // Show current state in modal
  if (db_type === "custom") {
    disconnectBtn.style.display = "inline-block";
    connectBtn.style.display = "none";
    successEl.style.display = "block";
    errorEl.style.display = "none";
    dbUriInput.disabled = true;
  } else {
    disconnectBtn.style.display = "none";
    connectBtn.style.display = "inline-block";
    successEl.style.display = "none";
    dbUriInput.disabled = false;
  }
  dbModal.style.display = "flex";
});

document.getElementById("disconnectDbBtn").addEventListener("click", () => {
  db_path = "";
  db_type = "";
  const indicator = document.querySelector(".db_indicator");
  indicator.style.backgroundColor = "red";
  document.querySelector(".db_btn").classList.remove("custom-db-active");
  document.querySelector(".db_btn p").textContent = "Try Sample DB";
  dbModal.style.display = "none";
  dbUriInput.value = "";
  dbUriInput.disabled = false;
});

cancelDbBtn.addEventListener("click", () => { dbModal.style.display = "none"; });
connectDbBtn.addEventListener("click", async () => {
  const uri = dbUriInput.value.trim();
  if (!uri) return;

  const errorEl = document.getElementById("dbConnectError");
  errorEl.style.display = "none";
  errorEl.textContent = "";
  connectDbBtn.textContent = "Connecting...";
  connectDbBtn.disabled = true;

  try {
    const res = await authFetch("/connect-db", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ db_uri: uri })
    });

    const data = await res.json();

    if (res.ok && data.success) {
      db_path = data.db_path;
      db_type = "custom";
      const indicator = document.querySelector(".db_indicator");
      const label = document.querySelector(".db_btn p");
      indicator.style.backgroundColor = "#32ff5e";
      label.textContent = "Database Connected";
      document.querySelector(".db_btn").classList.add("custom-db-active");
      dbModal.style.display = "none";
      dbUriInput.value = "";
    } else {
      errorEl.style.display = "block";
      errorEl.textContent = data.detail || "Connection failed. Check your URI.";
    }
  } catch (e) {
    errorEl.style.display = "block";
    errorEl.textContent = "Network error. Please try again.";
  } finally {
    connectDbBtn.textContent = "Connect";
    connectDbBtn.disabled = false;
  }
});

// --- Approval Modal ---
function showApprovalPopup(warningText) {
  approvalMessage.innerHTML = marked.parse(warningText);
  approvalModal.style.display = "flex";
}

async function approval_is_yes() {
  approvalModal.style.display = "none";
  const aiMsgElement = addTyping();
  let accumulatedText = "";

  try {
    const response = await authFetch("/resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "yes", thread_id: currentThreadId }),
    });

    if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);
          if (data.agent) {
            accumulatedText += data.agent;
            aiMsgElement.innerHTML = marked.parse(accumulatedText);
          } else if (data.error) {
            aiMsgElement.innerText = `❌ Error: ${data.error}`;
          }
        } catch (e) { console.error("Parse error:", line, e); }
      }
      messages.scrollTop = messages.scrollHeight;
    }
  } catch (err) {
    if (err.name !== "AbortError") {
      aiMsgElement.innerText = "❌ Error connecting to the server.";
      console.error(err);
    }
  }
}

async function approval_is_no() {
  approvalModal.style.display = "none";
  const aiMsgElement = addTyping();

  try {
    const response = await authFetch("/resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "no", thread_id: currentThreadId }),
    });

    if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);
          if (data.agent) {
            aiMsgElement.innerHTML = data.agent;
          } else if (data.done) {
            // stream finished
          } else if (data.error) {
            aiMsgElement.innerText = `❌ Error: ${data.error}`;
          }
        } catch (e) { console.error("Parse error:", line, e); }
      }
      messages.scrollTop = messages.scrollHeight;
    }
  } catch (err) {
    if (err.name !== "AbortError") {
      aiMsgElement.innerText = "❌ Error connecting to the server.";
      console.error(err);
    }
  }
}

// --- Send Message ---
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  if (!activated) {
    inputBox.classList.remove("centered-input");
    inputBox.classList.add("bottom-input");
    intro.style.display = "none";
    document.body.style.overflow = "auto";
    activated = true;
  }

  appendMessage(text, "user");
  input.value = "";
  const aiMsgElement = addTyping();
  let accumulatedText = "";

  try {
    const response = await authFetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_message: text,
        db_path: db_path || "",
        thread_id: currentThreadId,
      }),
    });

    if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let isFirstMessage = true;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);

          if (data.node_executed) {
            const ai_flow = document.createElement("div");
            ai_flow.style.fontSize = "13px";
            ai_flow.style.opacity = "0.8";
            ai_flow.innerText = `⚙️ ${data.node_executed.replace(/_/g, " ")}`;
            messages.insertBefore(ai_flow, aiMsgElement);

          } else if (data.warning) {
            aiMsgElement.remove();
            showApprovalPopup(data.warning);
            await loadThreads();
            return;

          } else if (data.token) {
            accumulatedText += data.token;
            aiMsgElement.innerHTML = marked.parse(accumulatedText);

          } else if (data.img_url) {
            const img = document.createElement("img");
            img.src = data.img_url;
            img.style.maxWidth = "100%";
            img.style.borderRadius = "8px";
            img.style.marginTop = "10px";
            img.style.display = "block";
            aiMsgElement.appendChild(img);

          } else if (data.error) {
            aiMsgElement.innerText = `❌ Error: ${data.error}`;
          }

          if (isFirstMessage && (data.token || data.node_executed)) {
            isFirstMessage = false;
            await loadThreads();
          }

        } catch (e) { console.error("Parse error:", line, e); }
      }
      messages.scrollTop = messages.scrollHeight;
    }

    await loadThreads();

  } catch (err) {
    if (err.name !== "AbortError") {
      aiMsgElement.innerText = "❌ Error connecting to the server.";
      console.error(err);
    }
  }
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });

// --- Sidebar ---
toggleBtn.addEventListener("click", () => {
  if (window.innerWidth <= 768) {
    sideBar.classList.toggle("sidebar-open");
    sidebarOverlay.classList.toggle("active", sideBar.classList.contains("sidebar-open"));
  } else {
    sideBar.classList.toggle("collapsed");
    chatcontainer.style.margin = "auto";
  }
});

sidebarOverlay.addEventListener("click", () => {
  sideBar.classList.remove("sidebar-open");
  sidebarOverlay.classList.remove("active");
});

sideBar.addEventListener("click", () => {
  sideBar.classList.remove("sidebar-open");
  sidebarOverlay.classList.remove("active");
});

mobileMenuBtn.addEventListener("click", () => {
  sideBar.classList.toggle("sidebar-open");
  sidebarOverlay.classList.toggle("active", sideBar.classList.contains("sidebar-open"));
});

window.addEventListener("resize", () => {
  if (window.innerWidth > 768) {
    sideBar.classList.remove("sidebar-open");
    sideBar.classList.remove("collapsed");
    sidebarOverlay.classList.remove("active");
  } else {
    sideBar.classList.remove("sidebar-open");
    sidebarOverlay.classList.remove("active");
  }
});

// --- Threads ---
async function loadThreads() {
  try {
    const res = await authFetch("/threads");
    const data = await res.json();
    renderHistory(data.threads || []);
  } catch (err) {
    console.error("Failed to load threads:", err);
  }
}

function renderHistory(threads) {
  chatList.innerHTML = "";
  threads.forEach(chat => {
    const item = document.createElement("div");
    item.classList.add("chat-item");

    if (chat.id === currentThreadId) {
      item.classList.add("active");
    }

    item.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" height="18" viewBox="0 -960 960 960" width="18" fill="currentColor" style="min-width:18px">
        <path d="M240-400h480v-80H240v80Zm0-120h480v-80H240v80Zm0-120h480v-80H240v80ZM120-80v-720q0-33 23.5-56.5T200-880h560q33 0 56.5 23.5T840-800v480q0 33-23.5 56.5T760-240H280L120-80Z"/>
      </svg>
      <span style="flex:1;overflow:hidden;text-overflow:ellipsis">${chat.title}</span>
      <button class="delete-chat-btn" title="Delete this chat" data-id="${chat.id}">
        <svg xmlns="http://www.w3.org/2000/svg" height="16" viewBox="0 -960 960 960" width="16" fill="currentColor">
          <path d="M280-120q-33 0-56.5-23.5T200-200v-520h-40v-80h200v-40h240v40h200v80h-40v520q0 33-23.5 56.5T680-120H280Zm400-600H280v520h400v-520ZM360-280h80v-360h-80v360Zm160 0h80v-360h-80v360ZM280-720v520-520Z"/>
        </svg>
      </button>`;

    item.addEventListener("click", (e) => {
      if (!e.target.closest(".delete-chat-btn")) loadChatHistory(chat.id);
    });

    item.querySelector(".delete-chat-btn").addEventListener("click", async (e) => {
      e.stopPropagation();
      await deleteChat(chat.id);
    });

    chatList.appendChild(item);
  });
}

async function deleteChat(id) {
  try {
    await authFetch(`/threads/${id}`, { method: "DELETE" });
  } catch (err) {
    console.error("Delete failed:", err);
    return;
  }

  if (id === currentThreadId) {
    currentThreadId = crypto.randomUUID();
    messages.innerHTML = "";
    intro.style.display = "block";
    inputBox.classList.add("centered-input");
    inputBox.classList.remove("bottom-input");
    activated = false;
  }

  await loadThreads();
}

async function loadChatHistory(id) {
  currentThreadId = id;
  messages.innerHTML = "";
  intro.style.display = "none";
  inputBox.classList.remove("centered-input");
  inputBox.classList.add("bottom-input");
  activated = true;
  await loadThreads();

  try {
    const response = await authFetch(`/chat_history/${id}`);
    if (!response.ok) throw new Error("Failed to load history");
    const data = await response.json();

    let lastAiBubble = null;

    data.messages.forEach(msg => {
      if (msg.type === "image") {
        const target = lastAiBubble || (() => {
          const b = document.createElement("div");
          b.classList.add("message", "ai");
          messages.appendChild(b);
          return b;
        })();
        const img = document.createElement("img");
        img.src = msg.img_url;
        img.style.maxWidth = "100%";
        img.style.borderRadius = "8px";
        img.style.marginTop = "10px";
        img.style.display = "block";
        target.appendChild(img);
      } else {
        const bubble = appendMessage(msg.text, msg.sender);
        if (msg.sender === "ai") lastAiBubble = bubble;
        else lastAiBubble = null;
      }
    });

  } catch (err) {
    console.error("Error loading chat:", err);
    appendMessage("⚠️ Could not load chat history.", "ai");
  }
}

newChatBtn.addEventListener("click", () => {
  currentThreadId = crypto.randomUUID();
  messages.innerHTML = "";
  intro.style.display = "block";
  inputBox.classList.add("centered-input");
  inputBox.classList.remove("bottom-input");
  activated = false;
  loadThreads();
});

const savedToken = localStorage.getItem("authToken");
const savedUsername = localStorage.getItem("username");

if (savedToken && savedUsername) {
  authToken = savedToken;
  currentUsername = savedUsername;
  document.getElementById("authScreen").style.display = "none";
  document.querySelector(".app-layout").style.display = "flex";
  document.querySelector(".header .buttons").style.display = "flex";
  document.getElementById("usernameDisplay").textContent = currentUsername;
  document.getElementById("sidebarAvatar").textContent = currentUsername.charAt(0).toUpperCase();
  loadThreads();
}
