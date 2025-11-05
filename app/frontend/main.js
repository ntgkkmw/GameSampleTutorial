/**
 * Retro RPG frontend logic implemented with vanilla JavaScript.
 * TODO: Integrate WebAudio hooks when BGM/SE assets are ready.
 */

const SAVE_KEY = "dq_like_save_v1";
const MAX_LOG_LINES = 120;

// Placeholder spell and item data mirrors backend definitions for quick lookup.
const SPELL_BOOK = {
  heal: { name: "ヒール", mp: 3, type: "heal" },
  fire: { name: "ファイア", mp: 5, type: "attack" }
};

const ITEM_BOOK = {
  herb: { name: "薬草", description: "HPをそこそこ回復" },
  antidote: { name: "解毒薬", description: "毒をなおす" },
  ether: { name: "霊薬", description: "MPを少しかいふく" },
  holywater: { name: "聖水", description: "しぼうした仲間を復活" }
};

const state = {
  version: null,
  player: null,
  locationId: null,
  locationData: null,
  mapCache: {},
  progress: { boss_defeated: false },
  mode: "title",
  menuContext: null,
  logs: [],
  encounterCounter: 0,
  lastThreshold: 4,
  battle: null,
  busy: false,
  namePending: true
};

const elements = {
  location: document.getElementById("location-name"),
  stats: document.getElementById("status-stats"),
  log: document.getElementById("message-log"),
  commands: document.getElementById("command-area"),
  modal: document.getElementById("name-modal"),
  modalInput: document.getElementById("player-name"),
  modalForm: document.getElementById("name-form"),
  saveBtn: document.getElementById("save-btn"),
  loadBtn: document.getElementById("load-btn"),
  infoBar: document.getElementById("info-bar")
};

/**
 * Perform an API request to the backend.
 * @param {string} path API path including /api prefix.
 * @param {RequestInit} options fetch options.
 * @returns {Promise<any>} parsed JSON response.
 */
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API error ${response.status}: ${text}`);
  }
  return response.json();
}

/**
 * Append a message to the log and trim to the maximum length.
 * @param {string} message line to append.
 */
function addLog(message) {
  state.logs.push(message);
  if (state.logs.length > MAX_LOG_LINES) {
    state.logs.splice(0, state.logs.length - MAX_LOG_LINES);
  }
  renderMessages();
}

/**
 * Render the status bar, message window, and command area.
 */
function render() {
  renderStatus();
  renderMessages();
  renderCommands();
  toggleModal();
}

/**
 * Update the status display.
 */
function renderStatus() {
  if (!state.player) {
    elements.location.textContent = "-";
    elements.stats.textContent = "---";
    return;
  }
  const locName = state.locationData ? state.locationData.name : "-";
  elements.location.textContent = `${locName}`;
  const p = state.player;
  elements.stats.textContent = `LV${p.level} HP ${p.hp}/${p.max_hp} MP ${p.mp}/${p.max_mp} EXP ${p.exp}/${p.next_exp} GOLD ${p.gold}`;
  elements.infoBar.textContent = state.mode === "battle" ? "戦闘中" : `次のエンカウントまであと ${Math.max(0, state.lastThreshold - state.encounterCounter)} 歩`;
}

/**
 * Refresh the message log DOM.
 */
function renderMessages() {
  elements.log.innerHTML = "";
  state.logs.forEach((line) => {
    const p = document.createElement("p");
    p.textContent = line;
    elements.log.appendChild(p);
  });
  elements.log.scrollTop = elements.log.scrollHeight;
}

/**
 * Build command buttons appropriate for the current mode/context.
 */
function renderCommands() {
  elements.commands.innerHTML = "";
  const disable = state.busy;

  /** @type {{label: string, handler: () => void}[]} */
  let commands = [];
  if (!state.player) {
    commands = [{ label: "ニューゲーム", handler: () => showNameModal() }];
  } else if (state.mode === "battle") {
    if (state.menuContext?.type === "battle_items") {
      const items = Object.entries(state.player.inventory || {}).filter(([, count]) => count > 0);
      items.forEach(([id, count]) => {
        const book = ITEM_BOOK[id] || { name: id };
        commands.push({ label: `${book.name} x${count}`, handler: () => handleBattleItem(id) });
      });
      commands.push({ label: "キャンセル", handler: () => clearMenu() });
    } else if (state.menuContext?.type === "battle_spells") {
      state.player.spells.forEach((spellId) => {
        const spell = SPELL_BOOK[spellId] || { name: spellId, mp: 0 };
        commands.push({ label: `${spell.name} (MP${spell.mp})`, handler: () => handleBattleSpell(spellId) });
      });
      commands.push({ label: "キャンセル", handler: () => clearMenu() });
    } else {
      commands = [
        { label: "たたかう", handler: () => handleBattleAction("attack") },
        { label: "まほう", handler: () => openMenu("battle_spells") },
        { label: "アイテム", handler: () => openMenu("battle_items") },
        { label: "にげる", handler: () => handleBattleAction("run") }
      ];
    }
  } else if (state.mode === "gameover") {
    commands = [
      { label: "ロード", handler: () => loadFromStorage() },
      { label: "ニューゲーム", handler: () => showNameModal() }
    ];
  } else if (state.menuContext?.type === "move") {
    state.menuContext.options.forEach((neighbor) => {
      const info = state.mapCache[neighbor] || { name: neighbor };
      commands.push({ label: `${info.name}へ`, handler: () => moveTo(neighbor) });
    });
    commands.push({ label: "やめる", handler: () => clearMenu() });
  } else if (state.mode === "town") {
    commands = [
      { label: "すすむ", handler: () => openMoveMenu() },
      { label: "ショップ", handler: () => openShopDialog() },
      { label: "しゅくや", handler: () => restAtInn() },
      { label: "ステータス", handler: () => showStatusDetail() }
    ];
  } else if (state.mode === "boss") {
    commands = [
      { label: "ボスに挑む", handler: () => challengeBoss() },
      { label: "もどる", handler: () => openMoveMenu() },
      { label: "ステータス", handler: () => showStatusDetail() }
    ];
  } else {
    // field / dungeon exploration
    commands = [
      { label: "すすむ", handler: () => exploreStep() },
      { label: "もどる", handler: () => openMoveMenu() },
      { label: "ステータス", handler: () => showStatusDetail() }
    ];
  }

  commands.forEach((cmd) => {
    const btn = document.createElement("button");
    btn.textContent = cmd.label;
    btn.disabled = disable;
    btn.addEventListener("click", () => cmd.handler());
    elements.commands.appendChild(btn);
  });
}

/**
 * Show the name entry modal.
 */
function showNameModal() {
  state.namePending = true;
  toggleModal();
  elements.modalInput.focus();
}

/**
 * Hide sub menu context.
 */
function clearMenu() {
  state.menuContext = null;
  render();
}

/**
 * Switch to a sub menu.
 * @param {string} type menu identifier.
 */
function openMenu(type) {
  state.menuContext = { type };
  render();
}

/**
 * Toggle modal visibility based on state.
 */
function toggleModal() {
  if (state.namePending) {
    elements.modal.classList.remove("hidden");
  } else {
    elements.modal.classList.add("hidden");
  }
}

/**
 * Load location metadata and update state.
 * @param {string} locationId identifier.
 */
async function loadLocation(locationId) {
  const info = await api(`/api/world/location/${locationId}`);
  state.locationId = locationId;
  state.locationData = info;
  state.mapCache[locationId] = info;
  state.encounterCounter = 0;
  state.mode = info.type === "town" ? "town" : info.type === "boss" ? "boss" : "field";
  addLog(`${info.name} に たどりついた。`);
  autoSave();
  render();
}

/**
 * Move to an adjacent location.
 * @param {string} locationId target location.
 */
async function moveTo(locationId) {
  clearMenu();
  await withBusy(async () => {
    await loadLocation(locationId);
  });
}

/**
 * Open the move menu using current neighbors.
 */
function openMoveMenu() {
  if (!state.locationData) return;
  state.menuContext = { type: "move", options: state.locationData.neighbors || [] };
  render();
}

/**
 * Fetch encounter result after stepping in the field.
 */
async function exploreStep() {
  if (!state.locationData?.encounter) {
    addLog("ここでは てきは でてこないようだ。");
    return;
  }
  await withBusy(async () => {
    state.encounterCounter += 1;
    const response = await api("/api/encounter/roll", {
      method: "POST",
      body: JSON.stringify({ areaId: state.locationData.encounter, counter: state.encounterCounter })
    });
    state.lastThreshold = response.threshold;
    if (response.encounter && response.enemy) {
      state.encounterCounter = 0;
      await startBattle(response.enemy);
    } else {
      addLog("しずかな まま すぎていった...");
      render();
    }
    autoSave();
  });
}

/**
 * Display detailed status information in the log.
 */
function showStatusDetail() {
  if (!state.player) return;
  const s = state.player.stats;
  addLog(`ATK:${s.atk} DEF:${s.defense} MAG:${s.mag} AGI:${s.agi}`);
}

/**
 * Attempt to rest at the current town inn.
 */
async function restAtInn() {
  if (state.mode !== "town" || !state.locationData?.innPrice) {
    addLog("ここには しゅくやが ない。");
    return;
  }
  if (state.player.gold < state.locationData.innPrice) {
    addLog("おかねが たりない!");
    return;
  }
  await withBusy(async () => {
    const result = await api("/api/inn/rest", {
      method: "POST",
      body: JSON.stringify({ player: state.player, price: state.locationData.innPrice })
    });
    state.player = result;
    addLog("ゆっくり やすんだ。HPとMPが かいふくした!");
    autoSave();
  });
}

/**
 * Open a simple shop dialog for buying items.
 */
async function openShopDialog() {
  if (state.mode !== "town") {
    addLog("ここには しょうにんが いない。");
    return;
  }
  const options = state.locationData.shop || [];
  if (!options.length) {
    addLog("なにも うっていないようだ。");
    return;
  }
  const list = options
    .map((id) => {
      const item = ITEM_BOOK[id] || { name: id };
      return `${item.name}`;
    })
    .join(", ");
  addLog(`ならんでいるのは: ${list}`);
}

/**
 * Initiate a battle with the final boss.
 */
async function challengeBoss() {
  await withBusy(async () => {
    const response = await api("/api/encounter/roll", {
      method: "POST",
      body: JSON.stringify({ areaId: "boss", counter: 9 })
    });
    if (response.enemy) {
      await startBattle(response.enemy);
    }
  });
}

/**
 * Start a battle session using backend state.
 * @param {object} enemyData enemy payload from backend.
 */
async function startBattle(enemyData) {
  const enemyName = enemyData.name || "モンスター";
  addLog(`${enemyName} が あらわれた!`);
  const result = await api("/api/battle/start", {
    method: "POST",
    body: JSON.stringify({ player: state.player, enemy: enemyData })
  });
  state.battle = result;
  state.player = result.player;
  state.mode = "battle";
  state.menuContext = null;
  addBattleLogs(result.log, 0);
  autoSave();
  render();
}

/**
 * Add new log lines from a battle response.
 * @param {string[]} logEntries full log from backend.
 * @param {number} previousLength number of lines already rendered.
 */
function addBattleLogs(logEntries, previousLength) {
  const fresh = logEntries.slice(previousLength);
  fresh.forEach((line) => addLog(line));
}

/**
 * Handle a high-level battle command.
 * @param {"attack"|"run"|"item"|"spell"} action battle command.
 * @param {object} [payload] optional payload.
 */
async function handleBattleAction(action, payload = {}) {
  await withBusy(async () => {
    if (!state.battle) return;
    const prevLen = state.battle.log.length;
    const result = await api("/api/battle/act", {
      method: "POST",
      body: JSON.stringify({ battleId: state.battle.id, action, payload })
    });
    state.battle = result;
    state.player = result.player;
    addBattleLogs(result.log, prevLen);
    if (result.ended) {
      finishBattle(result);
    }
    render();
    autoSave();
  });
}

/**
 * Handle using an item during battle.
 * @param {string} itemId item identifier.
 */
function handleBattleItem(itemId) {
  clearMenu();
  handleBattleAction("item", { itemId });
}

/**
 * Handle casting a spell during battle.
 * @param {string} spellId spell identifier.
 */
function handleBattleSpell(spellId) {
  clearMenu();
  handleBattleAction("spell", { spellId });
}

/**
 * Perform logic once a battle ends.
 * @param {object} battle battle payload.
 */
function finishBattle(battle) {
  state.battle = null;
  if (battle.enemy.hp <= 0) {
    if (battle.enemy.is_boss) {
      state.progress.boss_defeated = true;
      addLog("まおうを たおした! せかいに へいわが もどった!");
      state.mode = "gameover";
      addLog("エンディング (仮)");
    } else {
      state.mode = state.locationData?.type === "town" ? "town" : "field";
    }
  } else if (state.player.hp <= 0) {
    state.mode = "gameover";
    addLog("ゆうしゃは たおれてしまった...");
  } else {
    state.mode = state.locationData?.type === "town" ? "town" : "field";
  }
}

/**
 * Centralized busy state wrapper for async UI actions.
 * @param {() => Promise<void>} fn async callback.
 */
async function withBusy(fn) {
  if (state.busy) return;
  state.busy = true;
  render();
  try {
    await fn();
  } catch (error) {
    console.error(error);
    addLog("なにか ふしぎな ことが おこった...");
  } finally {
    state.busy = false;
    render();
  }
}

/**
 * Persist the current state into localStorage.
 */
function autoSave() {
  if (!state.player || !state.locationId) return;
  const payload = {
    version: state.version,
    player: state.player,
    location: state.locationId,
    progress: state.progress,
    encounterCounter: state.encounterCounter,
    logs: state.logs.slice(-20)
  };
  localStorage.setItem(SAVE_KEY, JSON.stringify(payload));
}

/**
 * Restore the latest save from localStorage if present.
 */
async function loadFromStorage() {
  const raw = localStorage.getItem(SAVE_KEY);
  if (!raw) {
    addLog("セーブデータが みつからない。");
    showNameModal();
    return;
  }
  try {
    const data = JSON.parse(raw);
    state.version = data.version;
    state.player = data.player;
    state.progress = data.progress || state.progress;
    state.logs = data.logs || [];
    state.encounterCounter = data.encounterCounter || 0;
    state.namePending = false;
    await loadLocation(data.location || "start_town");
    addLog("セーブデータを よみこんだ。");
  } catch (error) {
    console.error(error);
    addLog("セーブデータが こわれている!");
    showNameModal();
  }
}

/**
 * Manually trigger a save.
 */
function manualSave() {
  autoSave();
  addLog("セーブした。");
}

/**
 * Handle form submission for player name.
 * @param {SubmitEvent} event submit event.
 */
async function handleNameSubmit(event) {
  event.preventDefault();
  const name = elements.modalInput.value.trim();
  await withBusy(async () => {
    const response = await api("/api/new_game", {
      method: "POST",
      body: JSON.stringify({ name })
    });
    state.version = response.version;
    state.player = response.player;
    state.progress = response.progress || state.progress;
    state.logs = [];
    state.encounterCounter = 0;
    state.namePending = false;
    await loadLocation(response.location);
    addLog(`${state.player.name}の ぼうけんが はじまる!`);
    autoSave();
  });
}

/**
 * Entry point once DOM is ready.
 */
function bootstrap() {
  elements.modalForm.addEventListener("submit", handleNameSubmit);
  elements.saveBtn.addEventListener("click", manualSave);
  elements.loadBtn.addEventListener("click", () => {
    withBusy(async () => {
      await loadFromStorage();
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.menuContext) {
      clearMenu();
    }
  });
  const raw = localStorage.getItem(SAVE_KEY);
  if (raw) {
    loadFromStorage();
  } else {
    showNameModal();
  }
  render();
}

// React/TypeScript migration hint: keep state mutations centralized and expose
// render(state) style functions to match a component-based architecture later.

window.addEventListener("DOMContentLoaded", bootstrap);

