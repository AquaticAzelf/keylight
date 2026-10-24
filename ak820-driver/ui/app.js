/* The Keylight front end.
 *
 * Reads the app's own JSON API on the loopback server and keeps the shell in
 * step with the keyboard: the bar shows what the board is doing, the preview
 * shows what the board looks like, and every change goes straight to the
 * hardware so the two are never out of step.
 */

'use strict';

/* The five sections, in the order the sidebar shows them. The titles are
   here because the page's own title follows the section; the notes under
   each heading live in the page itself. */
const SECTIONS = [
  { id: 'lighting', title: 'Lighting' },
  { id: 'per-key', title: 'Per-key' },
  { id: 'macros', title: 'Macros' },
  { id: 'profiles', title: 'Profiles' },
  { id: 'settings', title: 'Settings' },
];

const APPLY_DELAY_MS = 120;

const DIRECTIONS = [
  { id: 0, name: 'Left to right' },
  { id: 1, name: 'Right to left' },
];

/* Modes whose effect does not move, so a direction would do nothing. */
const NO_DIRECTION = new Set([0x05, 0x06, 0x14, 0x1D, 0x1E]);

/* The colours the vendor's own app offers, in the order it lists them. */
const PALETTE = [
  [255, 0, 0], [255, 114, 0], [255, 240, 5], [0, 215, 15],
  [0, 153, 255], [49, 83, 255], [94, 1, 210], [255, 22, 169],
  [255, 0, 138], [255, 168, 0], [141, 255, 141], [61, 239, 255],
  [0, 72, 145], [255, 255, 255],
];

/* The preview moves the way the board does, so what you see is what the
   keyboard is doing. */
const MOTION = {
  0x00: 'off', 0x01: 'wave', 0x02: 'cloud', 0x03: 'vortex', 0x04: 'spectrum',
  0x05: 'breath', 0x06: 'static', 0x07: 'reaction', 0x08: 'ripples',
  0x09: 'traverse', 0x0A: 'stars', 0x0B: 'fireworks', 0x0C: 'roll',
  0x0D: 'wave-bar', 0x0E: 'cartoon', 0x0F: 'rain', 0x10: 'scan',
  0x11: 'surmount', 0x12: 'speed', 0x14: 'custom', 0x1D: 'audio',
  0x1E: 'capture',
};

const dom = {
  readout: document.getElementById('readout'),
  mode: document.getElementById('readout-mode'),
  chip: document.getElementById('readout-chip'),
  rgb: document.getElementById('readout-rgb'),
  tabDot: document.querySelector('.topbar-tab-dot'),
  topbarRefresh: document.getElementById('topbar-refresh'),
  themeToggle: document.getElementById('theme-toggle'),
  deviceState: document.getElementById('device-state'),
  deviceConnection: document.getElementById('device-connection'),
  deviceVersion: document.getElementById('device-version'),
  banner: document.getElementById('banner'),
  bannerText: document.getElementById('banner-text'),
  checkAgain: document.getElementById('check-again'),
  lighting: document.getElementById('section-lighting'),
  perKey: document.getElementById('section-per-key'),
  profilesSection: document.getElementById('section-profiles'),
  settingsSection: document.getElementById('section-settings'),
  macrosSection: document.getElementById('section-macros'),
  board: document.getElementById('board'),
  deckState: document.getElementById('deck-state'),
  modes: document.getElementById('modes'),
  brightness: document.getElementById('brightness'),
  speed: document.getElementById('speed'),
  direction: document.getElementById('direction'),
  picker: document.getElementById('picker'),
  palette: document.getElementById('palette'),
  favourites: document.getElementById('favourites'),
  perkeyFavourites: document.getElementById('perkey-favourites'),
  colourSwatch: document.getElementById('colour-swatch'),
  colourRgb: document.getElementById('colour-rgb'),
  valueMode: document.getElementById('value-mode'),
  valueColour: document.getElementById('value-colour'),
  directionNote: document.getElementById('direction-note'),
  applied: document.getElementById('applied'),
  /* per-key */
  perkeyBoard: document.getElementById('perkey-board'),
  perkeyValue: document.getElementById('perkey-value'),
  perkeyState: document.getElementById('perkey-state'),
  perkeyPicker: document.getElementById('perkey-picker'),
  perkeyPalette: document.getElementById('perkey-palette'),
  perkeySwatch: document.getElementById('perkey-swatch'),
  perkeyRgb: document.getElementById('perkey-rgb'),
  perkeyColour: document.getElementById('perkey-colour'),
  perkeyAll: document.getElementById('perkey-all'),
  perkeyClear: document.getElementById('perkey-clear'),
  perkeyInvert: document.getElementById('perkey-invert'),
  perkeyBrush: document.getElementById('perkey-brush'),
  /* profiles */
  profilesList: document.getElementById('profiles-list'),
  profilesEmpty: document.getElementById('profiles-empty'),
  profilesCount: document.getElementById('profiles-count'),
  profileSave: document.getElementById('profile-save'),
  profileRename: document.getElementById('profile-rename'),
  profileDelete: document.getElementById('profile-delete'),
  profileDuplicate: document.getElementById('profile-duplicate'),
  profileExport: document.getElementById('profile-export'),
  profileImport: document.getElementById('profile-import'),
  boardProfiles: document.getElementById('board-profiles'),
  boardProfileSave: document.getElementById('board-profile-save'),
  profilesFolder: document.getElementById('profiles-folder'),
  /* settings */
  appSettings: document.getElementById('app-settings'),
  deviceSettings: document.getElementById('device-settings'),
  deviceSettingsEmpty: document.getElementById('device-settings-empty'),
  settingsFolders: document.getElementById('settings-folders'),
  /* macros */
  macrosList: document.getElementById('macros-list'),
  macrosEmpty: document.getElementById('macros-empty'),
  macrosCount: document.getElementById('macros-count'),
  macroRecord: document.getElementById('macro-record'),
  macroRecordStop: document.getElementById('macro-record-stop'),
  macroRecordCancel: document.getElementById('macro-record-cancel'),
  macroPlay: document.getElementById('macro-play'),
  macroRename: document.getElementById('macro-rename'),
  macroDelete: document.getElementById('macro-delete'),
  recorder: document.getElementById('recorder'),
  recorderKeys: document.getElementById('recorder-keys'),
  macroRepeat: document.getElementById('macro-repeat'),
  macroDelay: document.getElementById('macro-delay'),
  remapActive: document.getElementById('remap-active'),
  remapList: document.getElementById('remap-list'),
  remapEmpty: document.getElementById('remap-empty'),
  remapKey: document.getElementById('remap-key'),
  remapMacro: document.getElementById('remap-macro'),
  remapAdd: document.getElementById('remap-add'),
  boardFacts: document.getElementById('board-facts'),
  settingsBoard: document.getElementById('settings-board'),
  settingsReset: document.getElementById('settings-reset'),
  lightingReset: document.getElementById('lighting-reset'),
};

const state = {
  section: 'lighting',
  connected: false,
  deviceState: 'missing',
  failure: null,
  checking: false,
  refreshing: false,
  modes: [],
  geometry: null,
  lighting: { mode: 0x06, brightness: 4, speed: 3, direction: 0, color: [255, 0, 0] },
  applyTimer: null,
  appliedTimer: null,
  pending: false,
  sent: false,
  lastSent: null,
  checkInterval: 2,
  rememberSection: true,
  confirmDelete: true,
  showConfirmations: true,
  /* per-key */
  keyColors: [],
  selectedKey: null,
  paintColour: [255, 0, 0],
  /* the colours the user has pinned */
  favourites: [],
  /* macros and the keys that play them */
  macros: [],
  selectedMacro: null,
  recording: false,
  recordedEvents: [],
  remapMapping: {},
  remapKeyNames: {},
  /* profiles */
  profiles: [],
  selectedProfile: null,
  boardProfiles: [],
  selectedBoardProfile: null,
  /* the app's own settings */
  appSettings: [],
  deviceSettings: [],
  systemStages: null,
};

/* The board keeps one colour for every slot in its chain. The board's
   capabilities say how many that is; the app falls back to the number the
   board's own driver uses for this model. */
const COLOR_SLOTS = 126;

let board = null;
let perKeyBoard = null;
let settingsBoard = null;

/* The timer that checks the keyboard. It is declared up here because the
   app checks the keyboard as it starts, which is before the polling code
   at the foot of this file has been reached. */
let pollTimer = null;

/* -- the theme ---------------------------------------------------------- */

const THEME_KEY = 'ak820-theme';

function currentTheme() {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
}

function setTheme(theme, remember) {
  document.documentElement.dataset.theme = theme;
  if (remember) {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (err) {
      /* No storage; the theme just will not be remembered. */
    }
  }
  const next = theme === 'dark' ? 'the light theme' : 'the dark theme';
  dom.themeToggle.title = 'Switch to ' + next;
  dom.themeToggle.setAttribute('aria-label', 'Switch to ' + next);
}

/* The app's own settings file is where the theme really lives. The
   browser's storage only holds a copy, so the page can pick the right
   theme before the first paint - without it, the app would flash the
   light theme on every start. */
function resolveTheme(value) {
  if (value !== 'light' && value !== 'dark') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return value;
}

function applyTheme(value) {
  setTheme(resolveTheme(value), true);
}

/* -- the API ------------------------------------------------------------ */

async function api(path, options) {
  const response = await fetch(path, Object.assign({ headers: { Accept: 'application/json' } }, options || {}));
  let payload = {};
  try {
    payload = await response.json();
  } catch (err) {
    payload = {};
  }
  if (!response.ok) {
    const error = new Error(payload.error || `The service answered ${response.status}.`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function post(path, body) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
}

async function loadModes() {
  try {
    const payload = await api('/api/modes');
    state.modes = payload.modes || [];
    buildModes();
    syncModes();
    scrollToChosenMode();
  } catch (err) {
    state.modes = [];
  }
}

async function loadGeometry() {
  try {
    const response = await fetch('assets/ak820-caps.json');
    state.geometry = await response.json();
  } catch (err) {
    state.geometry = null;
  }
}

async function refresh() {
  if (state.refreshing) return;
  state.refreshing = true;
  const chosenBefore = state.lighting.mode;
  try {
    const status = await api('/api/status');
    state.connected = Boolean(status.connected);
    state.deviceState = status.device_state || (state.connected ? 'connected' : 'missing');
    state.failure = status.connected ? null : (status.message || null);
    if (status.version) {
      dom.deviceVersion.textContent = `Keylight v${status.version}`;
    }
    if (state.connected) {
      try {
        const live = await api('/api/lighting');
        if (live && typeof live.mode === 'number') {
          if (state.pending) {
            /* Our change is on its way to the board, so the board is still
               behind. Keep what was chosen rather than taking the old value
               back - otherwise the first change after the app opens is lost. */
          } else if (!state.sent || !sameState(live, state.lastSent)) {
            /* Nothing of ours is in flight, or the board did not take what we
               sent. Either way the board is right. */
            state.sent = false;
            state.lastSent = null;
            state.lighting = live;
            setColourFromRgb(live.color || [255, 0, 0], false);
          }
        }
      } catch (err) {
        /* Keep what we know and carry on. */
      }
      if (!state.systemStages) {
        /* The board was not there when the settings were first read, so
           its rows never appeared. They load the moment it is. */
        loadSystemStages();
      }
    }
  } catch (err) {
    state.connected = false;
    state.failure = 'The app\'s service stopped answering.';
  }
  state.refreshing = false;
  render();
  if (state.lighting.mode !== chosenBefore) {
    /* The effect on the board is not the one on show, so bring it into
       view. When it is the same one the list is left where it is. */
    scrollToChosenMode();
  }
}

function sameState(a, b) {
  if (!a || !b) return false;
  if (a.mode !== b.mode || a.brightness !== b.brightness
    || a.speed !== b.speed || a.direction !== b.direction) {
    return false;
  }
  const left = a.color || [];
  const right = b.color || [];
  return left.length === 3 && right.length === 3
    && left[0] === right[0] && left[1] === right[1] && left[2] === right[2];
}

/* -- the lighting colour ------------------------------------------------ */

function setColourFromRgb(color, apply) {
  state.lighting.color = color;
  lightingPicker.set(color);
  renderColour(color);
  if (apply) scheduleApply();
}

function renderColour(color) {
  const hex = AkPicker.toHex(color);
  dom.valueColour.textContent = hex;
  dom.colourRgb.textContent = color.join(', ');
  dom.colourSwatch.style.setProperty('--swatch', `rgb(${color[0]} ${color[1]} ${color[2]})`);
  syncPalette(dom.palette, color);
  syncPalette(dom.favourites, color);
  renderPreview();
  renderConnection();
}

/* The colours the user has pinned. They are in the app's own folder, so
   they are still there next time. */
async function loadFavourites() {
  try {
    const payload = await api('/api/colours/favourites');
    state.favourites = payload.favourites || [];
  } catch (err) {
    state.favourites = [];
  }
  renderFavourites();
}

function renderFavourites() {
  buildPalette(dom.favourites, (color) => {
    lightingPicker.set(color);
    state.lighting.color = color;
    renderColour(color);
    scheduleApply();
  }, state.favourites);
  buildPalette(dom.perkeyFavourites, (color) => {
    perKeyPicker.set(color);
    state.paintColour = color;
    renderPerKeyColour();
    if (state.selectedKey) paintKey(state.selectedKey, color);
  }, state.favourites);
}

async function toggleFavourite(colour) {
  try {
    const payload = await post('/api/colours/favourites', { color: colour });
    state.favourites = payload.favourites || [];
    renderFavourites();
    showApplied(payload.added
      ? `Pinned ${AkPicker.toHex(colour)}.`
      : `Unpinned ${AkPicker.toHex(colour)}.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

/* -- the keyboard preview ------------------------------------------------ */

function renderPreview() {
  if (!board) return;
  const color = state.lighting.color || [0, 0, 0];
  const css = `rgb(${color[0]} ${color[1]} ${color[2]})`;
  const mode = state.lighting.mode;
  const motion = MOTION[mode] || 'static';
  const off = mode === 0x00;

  board.light(off ? null : css);
  board.root.dataset.motion = motion;
  board.root.style.setProperty('--anim-duration', `${(0.7 + (state.lighting.speed || 0) * 0.45).toFixed(2)}s`);
  board.root.setAttribute('aria-label', `The AK820 in ${modeName(mode)} mode`);
}

function modeName(id) {
  const found = state.modes.find((mode) => mode.id === id);
  return found ? found.name : 'Lighting';
}

/* -- the controls -------------------------------------------------------- */

/* The controls are built once and then only updated in place. Rebuilding
   them on every poll would take the focus away from whatever the user is
   doing. */
function buildModes() {
  const fragment = document.createDocumentFragment();
  for (const mode of state.modes) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'list-row';
    button.setAttribute('role', 'radio');
    button.dataset.mode = String(mode.id);
    button.innerHTML = '<span class="list-dot" aria-hidden="true"></span>'
      + '<span class="list-name"></span>';
    button.querySelector('.list-name').textContent = mode.name;
    button.addEventListener('click', () => {
      state.lighting.mode = mode.id;
      syncModes();
      scrollToChosenMode();
      renderControls();
      renderPreview();
      scheduleApply();
    });
    fragment.appendChild(button);
  }
  dom.modes.replaceChildren(fragment);
}

function syncModes() {
  for (const button of dom.modes.querySelectorAll('.list-row')) {
    const on = Number(button.dataset.mode) === state.lighting.mode;
    button.setAttribute('aria-checked', String(on));
  }
}

/* Bring the chosen effect into view - but only when it changes. The list is
   refreshed on every poll, and a list that moves back under the mouse makes
   the wrong effect get chosen. */
function scrollToChosenMode() {
  const list = dom.modes;
  let active = null;
  for (const button of list.querySelectorAll('.list-row')) {
    if (button.getAttribute('aria-checked') === 'true') active = button;
  }
  if (!active) return;
  // Scroll the list itself, never the page: scrollIntoView would drag the
  // whole window along with it.
  const top = active.offsetTop - list.offsetTop;
  const bottom = top + active.offsetHeight;
  if (top < list.scrollTop) {
    list.scrollTop = top;
  } else if (bottom > list.scrollTop + list.clientHeight) {
    list.scrollTop = bottom - list.clientHeight;
  }
}

function buildTrack(container, options, onPick) {
  const fragment = document.createDocumentFragment();
  for (const option of options) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'track-option';
    button.setAttribute('role', 'radio');
    button.dataset.value = String(option.value);
    button.textContent = option.name;
    button.addEventListener('click', () => onPick(option.value));
    fragment.appendChild(button);
  }
  container.replaceChildren(fragment);
}

function syncTrack(container, value) {
  for (const button of container.querySelectorAll('.track-option')) {
    button.setAttribute('aria-checked', String(Number(button.dataset.value) === value));
  }
}

function buildBrightness() {
  const options = [];
  for (let level = 0; level <= 4; level += 1) {
    options.push({ value: level, name: String(level) });
  }
  buildTrack(dom.brightness, options, (value) => {
    state.lighting.brightness = value;
    syncBrightness();
    scheduleApply();
  });
}

function syncBrightness() {
  syncTrack(dom.brightness, state.lighting.brightness);
}

function buildSpeed() {
  const options = [];
  for (let level = 0; level <= 5; level += 1) {
    options.push({ value: level, name: String(level) });
  }
  buildTrack(dom.speed, options, (value) => {
    state.lighting.speed = value;
    syncSpeed();
    renderPreview();
    scheduleApply();
  });
}

function syncSpeed() {
  syncTrack(dom.speed, state.lighting.speed);
}

function buildDirection() {
  buildTrack(dom.direction, DIRECTIONS.map((d) => ({ value: d.id, name: d.name })), (value) => {
    state.lighting.direction = value;
    syncDirection();
    scheduleApply();
  });
}

function syncDirection() {
  const allowed = !NO_DIRECTION.has(state.lighting.mode);
  for (const button of dom.direction.querySelectorAll('.track-option')) {
    /* An effect that does not move has no direction, so nothing is
       chosen - the control is off, not set to "Left". */
    const active = allowed && Number(button.dataset.value) === state.lighting.direction;
    button.setAttribute('aria-checked', String(active));
    button.disabled = !allowed;
  }
  dom.directionNote.textContent = allowed
    ? 'Which way it travels'
    : 'This effect does not move.';
}

function renderControls() {
  dom.valueMode.textContent = modeName(state.lighting.mode);
  dom.deckState.textContent = modeName(state.lighting.mode);
  syncModes();
  syncBrightness();
  syncSpeed();
  syncDirection();
}

/* -- sending the change to the board ------------------------------------- */

function scheduleApply() {
  state.pending = true;
  state.sent = false;
  if (state.applyTimer) {
    clearTimeout(state.applyTimer);
  }
  state.applyTimer = setTimeout(applyLighting, APPLY_DELAY_MS);
}

async function applyLighting() {
  state.applyTimer = null;
  if (!state.connected) {
    /* The change is dropped, so say so - a silent drop looks like a dead
       button. */
    state.pending = false;
    showApplied(state.failure || 'The keyboard is not connected.', true);
    return;
  }
  const payload = {
    mode: state.lighting.mode,
    brightness: state.lighting.brightness,
    speed: state.lighting.speed,
    direction: state.lighting.direction,
    color: state.lighting.color,
  };
  try {
    await post('/api/lighting', payload);
    state.lastSent = payload;
    state.pending = false;
    state.sent = true;
    showApplied('Sent to the keyboard.');
  } catch (err) {
    state.pending = false;
    state.sent = false;
    showApplied(err.message, true);
  }
}

function showApplied(message, isError) {
  if (!state.showConfirmations && !isError) return;
  dom.applied.textContent = message;
  dom.applied.classList.toggle('is-error', Boolean(isError));
  dom.applied.classList.add('is-shown');
  if (state.appliedTimer) {
    clearTimeout(state.appliedTimer);
  }
  state.appliedTimer = setTimeout(() => {
    dom.applied.classList.remove('is-shown');
  }, isError ? 3200 : 1600);
}

/* Deleting something asks first, unless the user said not to. */
function confirmDelete(message) {
  if (!state.confirmDelete) return true;
  return window.confirm(message);
}

/* -- the per-key editor -------------------------------------------------- */

function buildPalette(container, onPick, colours) {
  const list = colours || PALETTE;
  const fragment = document.createDocumentFragment();
  for (const color of list) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'palette-swatch';
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', AkPicker.toHex(color));
    button.title = AkPicker.toHex(color);
    button.dataset.rgb = color.join(',');
    button.style.background = `rgb(${color[0]} ${color[1]} ${color[2]})`;
    button.addEventListener('click', () => onPick(color));
    fragment.appendChild(button);
  }
  container.replaceChildren(fragment);
}

function syncPalette(container, current) {
  const wanted = current.join(',');
  for (const button of container.querySelectorAll('.palette-swatch')) {
    button.setAttribute('aria-pressed', String(button.dataset.rgb === wanted));
  }
}

async function loadKeyColors() {
  try {
    const payload = await api('/api/keys/colors');
    state.keyColors = payload.colors || [];
  } catch (err) {
    state.keyColors = [];
  }
  paintBoard();
}

/* The board keeps black for a key that is not lit, so black means "off" and
   a key with black in it must not be painted. */
function isDark(color) {
  return !color || (color[0] === 0 && color[1] === 0 && color[2] === 0);
}

function paintBoard() {
  if (!state.geometry || !perKeyBoard) return;
  for (const key of state.geometry.keys) {
    const color = state.keyColors[key.led];
    if (isDark(color)) {
      perKeyBoard.paintKey(key.led, null);
      continue;
    }
    perKeyBoard.paintKey(key.led, `rgb(${color[0]} ${color[1]} ${color[2]})`);
  }
}

function selectKey(key) {
  state.selectedKey = key;
  perKeyBoard.select(key.led);
  dom.perkeyValue.textContent = key.label;
  paintKey(key, state.paintColour);
}

function renderPerKeyColour() {
  const hex = AkPicker.toHex(state.paintColour);
  dom.perkeyColour.textContent = hex;
  dom.perkeyRgb.textContent = state.paintColour.join(', ');
  dom.perkeySwatch.style.setProperty('--swatch',
    `rgb(${state.paintColour[0]} ${state.paintColour[1]} ${state.paintColour[2]})`);
  syncPalette(dom.perkeyPalette, state.paintColour);
  syncPalette(dom.perkeyFavourites, state.paintColour);
}

let keyTimer = null;

function paintKey(key, color) {
  state.keyColors[key.led] = color;
  if (isDark(color)) {
    perKeyBoard.paintKey(key.led, null);
  } else {
    perKeyBoard.paintKey(key.led, `rgb(${color[0]} ${color[1]} ${color[2]})`);
  }
  if (keyTimer) clearTimeout(keyTimer);
  keyTimer = setTimeout(sendKeyColors, 200);
}

async function sendKeyColors() {
  keyTimer = null;
  if (!state.connected) return;
  if (!state.keyColors.length) {
    /* The board's colours were never read, so anything sent now would wipe
       what is on it. Say so instead of guessing. */
    dom.perkeyState.textContent = 'The keyboard\'s colours were not read, so nothing was changed.';
    return;
  }
  /* The board wants one colour for every slot in its chain, so a slot it
     did not give us is sent as black rather than as a hole. */
  const buffer = [];
  for (let led = 0; led < COLOR_SLOTS; led += 1) {
    buffer.push(state.keyColors[led] || [0, 0, 0]);
  }
  try {
    await post('/api/keys/colors', { colors: buffer });
    dom.perkeyState.textContent = 'Painted on the keyboard';
  } catch (err) {
    dom.perkeyState.textContent = err.message;
    showApplied(err.message, true);
  }
}

function paintEveryKey() {
  if (!state.geometry) return;
  for (const key of state.geometry.keys) {
    state.keyColors[key.led] = state.paintColour.slice();
    perKeyBoard.paintKey(key.led, `rgb(${state.paintColour[0]} ${state.paintColour[1]} ${state.paintColour[2]})`);
  }
  sendKeyColors();
}

function clearEveryKey() {
  if (!state.geometry) return;
  for (const key of state.geometry.keys) {
    state.keyColors[key.led] = [0, 0, 0];
    perKeyBoard.paintKey(key.led, null);
  }
  sendKeyColors();
}

function invertEveryKey() {
  if (!state.geometry) return;
  for (const key of state.geometry.keys) {
    const color = state.keyColors[key.led] || [0, 0, 0];
    /* Inverted, not turned round: the other way up of a colour is not the
       opposite of it. */
    const flipped = [255 - color[0], 255 - color[1], 255 - color[2]];
    state.keyColors[key.led] = flipped;
    perKeyBoard.paintKey(key.led, `rgb(${flipped[0]} ${flipped[1]} ${flipped[2]})`);
  }
  sendKeyColors();
}

/* -- profiles ----------------------------------------------------------- */

async function loadProfiles() {
  try {
    const payload = await api('/api/profiles');
    state.profiles = payload.profiles || [];
  } catch (err) {
    state.profiles = [];
  }
  renderProfiles();
  try {
    const payload = await api('/api/board-profiles');
    state.boardProfiles = payload.profiles || [];
  } catch (err) {
    state.boardProfiles = [];
    /* The list is empty because the keyboard could not be read, not because
       the board has no profiles of its own. Say so, or the empty card is a
       lie. */
    showApplied(err.message, true);
  }
  renderBoardProfiles();
  try {
    const payload = await api('/api/settings');
    dom.profilesFolder.textContent = (payload.folders || {}).profiles || '';
  } catch (err) {
    /* The folder is only shown as a convenience. */
  }
}

function renderProfiles() {
  const list = dom.profilesList;
  list.replaceChildren();
  dom.profilesCount.textContent = String(state.profiles.length);
  dom.profilesEmpty.hidden = state.profiles.length > 0;
  for (const profile of state.profiles) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'list-row';
    row.setAttribute('role', 'listitem');
    row.dataset.name = profile.name;
    const effect = modeName(profile.mode);
    row.innerHTML = '<span class="list-dot" aria-hidden="true"></span>'
      + '<span class="list-text"><span class="list-name"></span>'
      + '<span class="list-note"></span></span>';
    row.querySelector('.list-name').textContent = profile.name;
    row.querySelector('.list-note').textContent =
      `${effect} · ${profile.modified ? profile.modified.replace('T', ' ').slice(0, 16) : ''}`;
    row.addEventListener('click', () => {
      state.selectedProfile = profile.name;
      renderProfiles();
      applyProfile(profile.name);
    });
    list.appendChild(row);
  }
  const has = Boolean(state.selectedProfile);
  dom.profileRename.disabled = !has;
  dom.profileDelete.disabled = !has;
  dom.profileDuplicate.disabled = !has;
  dom.profileExport.disabled = !has;
}

async function applyProfile(name) {
  try {
    await api(`/api/profiles/${encodeURIComponent(name)}`, { method: 'GET' });
    showApplied(`“${name}” is on the keyboard.`);
    await refresh();
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function saveProfile() {
  const name = window.prompt('What is this profile called?', state.selectedProfile || '');
  if (name === null) return;
  try {
    await post('/api/profiles', { name: name, with_key_colors: true });
    state.selectedProfile = name.trim();
    await loadProfiles();
    showApplied(`Saved “${name.trim()}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function renameProfile() {
  const current = state.selectedProfile;
  if (!current) return;
  const name = window.prompt('What is this profile called now?', current);
  if (name === null || !name.trim() || name.trim() === current) return;
  try {
    await post('/api/profiles/rename', { name: current, new_name: name.trim() });
    state.selectedProfile = name.trim();
    await loadProfiles();
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function deleteProfile() {
  const current = state.selectedProfile;
  if (!current) return;
  if (!confirmDelete(`Delete the profile “${current}”?\n\nThis cannot be undone.`)) return;
  try {
    await api(`/api/profiles/${encodeURIComponent(current)}`, { method: 'DELETE' });
    state.selectedProfile = null;
    await loadProfiles();
    showApplied(`Deleted “${current}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function duplicateProfile() {
  const current = state.selectedProfile;
  if (!current) return;
  const name = window.prompt('What is the copy called?', `${current} copy`);
  if (name === null || !name.trim()) return;
  try {
    const payload = await post('/api/profiles/duplicate',
      { name: current, new_name: name.trim() });
    state.selectedProfile = payload.name;
    await loadProfiles();
    showApplied(`Copied “${current}” to “${payload.name}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function exportProfile() {
  const current = state.selectedProfile;
  if (!current) return;
  try {
    const payload = await post('/api/profiles/export', { name: current });
    showApplied(`Exported to ${payload.path}`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function importProfile() {
  const path = window.prompt(
    'Which file do you want to import?\n\nPut it anywhere you like and paste the full path here.',
    '');
  if (path === null || !path.trim()) return;
  try {
    const payload = await post('/api/profiles/import', { path: path.trim() });
    state.selectedProfile = payload.name;
    await loadProfiles();
    showApplied(`Imported “${payload.name}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

function renderBoardProfiles() {
  const list = dom.boardProfiles;
  list.replaceChildren();
  for (const profile of state.boardProfiles) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'list-row';
    row.setAttribute('role', 'listitem');
    row.dataset.index = String(profile.index);
    row.innerHTML = '<span class="list-dot" aria-hidden="true"></span>'
      + '<span class="list-text"><span class="list-name"></span>'
      + '<span class="list-note"></span></span>';
    row.querySelector('.list-name').textContent = `Profile ${profile.index + 1}`;
    row.querySelector('.list-note').textContent = profile.active ? 'On screen now' : modeName(profile.mode);
    row.classList.toggle('is-active', Boolean(profile.active));
    row.addEventListener('click', () => {
      state.selectedBoardProfile = profile.index;
      renderBoardProfiles();
      useBoardProfile(profile.index);
    });
    list.appendChild(row);
  }
  dom.boardProfileSave.disabled = state.selectedBoardProfile === null;
}

async function useBoardProfile(index) {
  try {
    await post('/api/board-profiles/use', { index: index });
    showApplied(`Profile ${index + 1} is on the keyboard.`);
    await refresh();
    await loadProfiles();
  } catch (err) {
    showApplied(err.message, true);
  }
}

/* -- settings ----------------------------------------------------------- */

async function loadSettings() {
  try {
    const payload = await api('/api/settings');
    state.appSettings = payload.settings || [];
    state.deviceSettings = state.appSettings.filter((setting) => setting.kind === 'device');
    state.appSettings = state.appSettings.filter((setting) => setting.kind === 'app');
    const folders = payload.folders || {};
    dom.settingsFolders.textContent = [folders.profiles, folders.macros, folders.exports]
      .filter(Boolean).join('\n');
    for (const setting of state.appSettings) {
      if (setting.key === 'check_interval') state.checkInterval = Number(setting.value) || 0;
      if (setting.key === 'remember_section') state.rememberSection = setting.value !== '0';
      if (setting.key === 'confirm_delete') state.confirmDelete = setting.value !== '0';
      if (setting.key === 'show_confirmations') state.showConfirmations = setting.value !== '0';
      if (setting.key === 'theme') applyTheme(setting.value);
    }
    schedulePoll();
  } catch (err) {
    state.appSettings = [];
  }
  renderSettings();
  loadBoardFacts();
  loadSystemStages();
}

/* -- the settings the keyboard itself keeps ------------------------------- */

async function loadSystemStages() {
  try {
    state.systemStages = await api('/api/system-stages');
  } catch (err) {
    state.systemStages = null;
  }
  renderSystemStages();
}

function renderSystemStages() {
  if (!dom.deviceSettings) return;
  dom.deviceSettings.replaceChildren();
  const stages = state.systemStages;
  dom.deviceSettingsEmpty.hidden = Boolean(stages);
  if (!stages) {
    for (const setting of state.deviceSettings) {
      const note = document.createElement('p');
      note.className = 'note';
      note.textContent = `${setting.name}: ${setting.value}`;
      dom.deviceSettings.appendChild(note);
    }
    return;
  }
  const defs = [
    { key: 'polling_rate', name: 'Report rate', note: 'How often the keyboard sends input',
      options: [['0', '1000 Hz'], ['1', '500 Hz'], ['2', '250 Hz'], ['3', '125 Hz']] },
    { key: 'win_lock', name: 'Windows Lock', note: 'Stop the Win key reaching Windows',
      options: [['0', 'Off'], ['1', 'On']] },
    { key: 'exchange', name: 'Exchange key', note: 'Swap the Win and Alt keys',
      options: [['0', 'Off'], ['1', 'On']] },
  ];
  for (const def of defs) {
    const card = document.createElement('div');
    card.className = 'setting';
    card.innerHTML = '<span class="setting-icon" aria-hidden="true">'
      + '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="14" rx="2"></rect>'
      + '<path d="M7 9h.01M11 9h.01M15 9h.01M7 13h.01M11 13h.01M15 13h.01M8 16.5h8"></path></svg>'
      + '</span><div class="setting-text"><p class="setting-title"></p>'
      + '<p class="setting-note"></p></div><div class="setting-control"></div>';
    card.querySelector('.setting-title').textContent = def.name;
    card.querySelector('.setting-note').textContent = def.note;
    const control = card.querySelector('.setting-control');
    const track = document.createElement('div');
    track.className = 'track';
    track.setAttribute('role', 'radiogroup');
    track.setAttribute('aria-label', def.name);
    const current = String(stages[def.key]);
    for (const [value, label] of def.options) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'track-option';
      button.setAttribute('role', 'radio');
      button.dataset.value = value;
      button.textContent = label;
      button.setAttribute('aria-checked', String(value === current));
      button.addEventListener('click', () => changeStage(def.key, Number(value)));
      track.appendChild(button);
    }
    control.appendChild(track);
    dom.deviceSettings.appendChild(card);
  }
}

async function changeStage(key, value) {
  try {
    state.systemStages = await post('/api/system-stages', { [key]: value });
    renderSystemStages();
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function loadBoardFacts() {
  if (!dom.boardFacts) return;
  dom.boardFacts.replaceChildren();
  try {
    const info = await api('/api/board-info');
    const facts = [
      ['Name', info.name],
      ['Connection', `USB ${info.vid}:${info.pid}`],
      ['Keys', String(info.keys)],
      ['Lights', String(info.map_size)],
      ['Macro space', info.macro_space ? `${(info.macro_space / 1024).toFixed(0)} KB` : '—'],
    ];
    for (const [name, value] of facts) {
      const term = document.createElement('dt');
      term.textContent = name;
      const detail = document.createElement('dd');
      detail.textContent = value;
      dom.boardFacts.appendChild(term);
      dom.boardFacts.appendChild(detail);
    }
  } catch (err) {
    /* Without the keyboard there is nothing to show. */
  }
}

function renderSettings() {
  dom.appSettings.replaceChildren();
  for (const setting of state.appSettings) {
    const card = document.createElement('div');
    card.className = 'setting';
    card.innerHTML = '<span class="setting-icon" aria-hidden="true">'
      + '<svg viewBox="0 0 24 24"><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"></path></svg>'
      + '</span><div class="setting-text"><p class="setting-title"></p>'
      + '<p class="setting-note"></p></div><div class="setting-control"></div>';
    card.querySelector('.setting-title').textContent = setting.name;
    card.querySelector('.setting-note').textContent = setting.note;
    const control = card.querySelector('.setting-control');
    const track = document.createElement('div');
    track.className = 'track';
    track.setAttribute('role', 'radiogroup');
    track.setAttribute('aria-label', setting.name);
    for (const option of setting.options) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'track-option';
      button.setAttribute('role', 'radio');
      button.dataset.value = option.value;
      button.textContent = option.name;
      button.setAttribute('aria-checked', String(String(option.value) === String(setting.value)));
      button.addEventListener('click', () => changeSetting(setting.key, option.value, track));
      track.appendChild(button);
    }
    control.appendChild(track);
    dom.appSettings.appendChild(card);
  }
}

async function changeSetting(key, value, track) {
  try {
    await post('/api/settings', { key: key, value: value });
    for (const button of track.querySelectorAll('.track-option')) {
      button.setAttribute('aria-checked', String(button.dataset.value === String(value)));
    }
    if (key === 'theme') {
      applyTheme(value);
    }
    if (key === 'check_interval') {
      state.checkInterval = Number(value) || 0;
      schedulePoll();
    }
    if (key === 'remember_section') {
      state.rememberSection = value === '1';
    }
    if (key === 'confirm_delete') {
      state.confirmDelete = value !== '0';
    }
    if (key === 'show_confirmations') {
      state.showConfirmations = value !== '0';
    }
  } catch (err) {
    showApplied(err.message, true);
  }
}

/* -- macros ------------------------------------------------------------- */

async function loadMacros() {
  try {
    const payload = await api('/api/macros');
    state.macros = payload.macros || [];
  } catch (err) {
    state.macros = [];
  }
  renderMacros();
  try {
    const payload = await api('/api/remap');
    dom.remapActive.checked = Boolean(payload.active);
    state.remapMapping = payload.mapping || {};
    renderRemap(state.remapMapping);
    fillRemapKeys(payload.keys || []);
  } catch (err) {
    /* The hook state is only shown when it can be read. */
  }
}

function fillRemapKeys(keys) {
  const select = dom.remapKey;
  if (!select) return;
  state.remapKeyNames = {};
  for (const key of keys) {
    state.remapKeyNames[String(key.code)] = key.name;
  }
  select.replaceChildren();
  for (const key of keys) {
    const option = document.createElement('option');
    option.value = String(key.code);
    option.textContent = key.name;
    select.appendChild(option);
  }
}

function fillRemapMacros() {
  const select = dom.remapMacro;
  if (!select) return;
  const chosen = select.value;
  select.replaceChildren();
  for (const macro of state.macros) {
    const option = document.createElement('option');
    option.value = macro.name;
    option.textContent = macro.name;
    select.appendChild(option);
  }
  if (chosen) select.value = chosen;
}

function renderMacros() {
  const list = dom.macrosList;
  list.replaceChildren();
  dom.macrosCount.textContent = String(state.macros.length);
  dom.macrosEmpty.hidden = state.macros.length > 0;
  state.macros.forEach((macro, index) => {
    const row = document.createElement('div');
    row.className = 'list-row list-row-static';
    row.dataset.name = macro.name;
    row.innerHTML = '<span class="list-dot" aria-hidden="true"></span>'
      + '<span class="list-text"><span class="list-name"></span>'
      + '<span class="list-note"></span></span>';
    row.querySelector('.list-name').textContent = macro.name;
    const times = Number(macro.repeat) || 1;
    row.querySelector('.list-note').textContent = (macro.summary || 'Empty')
      + (times > 1 ? ` · ×${times}` : '');
    row.addEventListener('click', () => {
      state.selectedMacro = macro.name;
      renderMacros();
    });
    /* The two buttons that move the macro up or down the list. */
    for (const [where, title, path] of [
      [index - 1, 'Move it up', 'M18 15l-6-6-6 6'],
      [index + 1, 'Move it down', 'M6 9l6 6 6-6'],
    ]) {
      const move = document.createElement('button');
      move.type = 'button';
      move.className = 'icon-button';
      move.title = title;
      move.setAttribute('aria-label', `${title}: ${macro.name}`);
      move.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">'
        + `<path d="${path}"></path></svg>`;
      move.disabled = where < 0 || where >= state.macros.length;
      move.addEventListener('click', (event) => {
        event.stopPropagation();
        moveMacro(macro.name, where);
      });
      row.appendChild(move);
    }
    list.appendChild(row);
  });
  const has = Boolean(state.selectedMacro);
  dom.macroPlay.disabled = !has;
  dom.macroRename.disabled = !has;
  dom.macroDelete.disabled = !has;
  fillRemapMacros();
}

async function moveMacro(name, to) {
  try {
    await post('/api/macros/reorder', { name: name, to: to });
    await loadMacros();
  } catch (err) {
    showApplied(err.message, true);
  }
}

function renderRemap(mapping) {
  const list = dom.remapList;
  list.replaceChildren();
  const names = Object.keys(mapping || {});
  dom.remapEmpty.hidden = names.length > 0;
  for (const key of names) {
    const row = document.createElement('div');
    row.className = 'list-row list-row-static';
    row.innerHTML = '<span class="list-dot" aria-hidden="true"></span>'
      + '<span class="list-text"><span class="list-name"></span>'
      + '<span class="list-note"></span></span>';
    row.querySelector('.list-name').textContent = key;
    row.querySelector('.list-note').textContent = mapping[key];
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'icon-button';
    remove.title = `Take the macro off ${key}`;
    remove.setAttribute('aria-label', `Take the macro off ${key}`);
    remove.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">'
      + '<path d="M6 6l12 12M18 6 6 18"></path></svg>';
    remove.addEventListener('click', () => {
      const next = Object.assign({}, state.remapMapping);
      delete next[key];
      setRemap(true, next);
    });
    row.appendChild(remove);
    list.appendChild(row);
  }
}

async function startRecording() {
  try {
    await post('/api/macros/record', {});
    state.recording = true;
    state.recordedEvents = [];
    dom.recorder.hidden = false;
    dom.recorderKeys.textContent = 'Nothing yet';
    dom.macroRecord.disabled = true;
    showApplied('Recording. Press the keys you want.');
    pollRecording();
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function pollRecording() {
  if (!state.recording) return;
  try {
    const payload = await api('/api/macros/record');
    state.recordedEvents = payload.events || [];
    const names = state.recordedEvents
      .filter((event) => event.down)
      .map((event) => event.text || event.vk);
    dom.recorderKeys.textContent = names.length ? names.join(' then ') : 'Nothing yet';
  } catch (err) {
    /* Keep the last list. */
  }
  if (state.recording) {
    window.setTimeout(pollRecording, 500);
  }
}

async function stopRecording() {
  state.recording = false;
  dom.recorder.hidden = true;
  dom.macroRecord.disabled = false;
  let events = state.recordedEvents;
  try {
    const payload = await post('/api/macros/record/stop', {});
    events = payload.events || events;
  } catch (err) {
    showApplied(err.message, true);
  }
  if (!events.length) {
    showApplied('Nothing was recorded.', true);
    return;
  }
  const name = window.prompt('What is this macro called?', '');
  if (name === null || !name.trim()) return;
  try {
    await post('/api/macros', {
      name: name.trim(),
      events: events,
      repeat: Number(dom.macroRepeat.value) || 1,
      delay: Number(dom.macroDelay.value) || 0,
    });
    state.selectedMacro = name.trim();
    await loadMacros();
    showApplied(`Saved “${name.trim()}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function cancelRecording() {
  state.recording = false;
  dom.recorder.hidden = true;
  dom.macroRecord.disabled = false;
  try {
    await post('/api/macros/record/stop', {});
  } catch (err) {
    /* Nothing to stop. */
  }
}

async function playMacro() {
  const name = state.selectedMacro;
  if (!name) return;
  try {
    await post('/api/macros/play', { name: name });
    showApplied(`Played “${name}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function renameMacro() {
  const current = state.selectedMacro;
  if (!current) return;
  const name = window.prompt('What is this macro called now?', current);
  if (name === null || !name.trim() || name.trim() === current) return;
  try {
    await post('/api/macros/rename', { name: current, new_name: name.trim() });
    state.selectedMacro = name.trim();
    await loadMacros();
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function deleteMacro() {
  const current = state.selectedMacro;
  if (!current) return;
  if (!confirmDelete(`Delete the macro “${current}”?\n\nThis cannot be undone.`)) return;
  try {
    await api(`/api/macros/${encodeURIComponent(current)}`, { method: 'DELETE' });
    state.selectedMacro = null;
    await loadMacros();
    showApplied(`Deleted “${current}”.`);
  } catch (err) {
    showApplied(err.message, true);
  }
}

async function addRemap() {
  const key = dom.remapKey.value;
  const macro = dom.remapMacro.value;
  if (!key || !macro) {
    showApplied('Choose a key and a macro first.', true);
    return;
  }
  const name = state.remapKeyNames[key] || key;
  /* The whole list of bindings goes back, so a second binding does not
     throw the first one away. */
  const next = Object.assign({}, state.remapMapping);
  next[name] = macro;
  await setRemap(true, next);
}

async function setRemap(active, mapping) {
  try {
    const payload = await post('/api/remap', {
      active: active,
      mapping: mapping || state.remapMapping,
    });
    dom.remapActive.checked = Boolean(payload.active);
    await loadMacros();
    showApplied(active ? 'The app is now changing the keys.' : 'The keys are back as they were.');
  } catch (err) {
    dom.remapActive.checked = !active;
    showApplied(err.message, true);
  }
}

/* -- drawing ------------------------------------------------------------ */

function render() {
  const section = SECTIONS.find((item) => item.id === state.section) || SECTIONS[0];
  document.title = `${section.title} — Keylight`;

  for (const link of document.querySelectorAll('.nav-link')) {
    if (link.dataset.section === section.id) {
      link.setAttribute('aria-current', 'page');
    } else {
      link.removeAttribute('aria-current');
    }
  }

  const isLighting = section.id === 'lighting';
  const isPerKey = section.id === 'per-key';
  const isProfiles = section.id === 'profiles';
  const isSettings = section.id === 'settings';
  const isMacros = section.id === 'macros';
  dom.lighting.hidden = !isLighting;
  dom.perKey.hidden = !isPerKey;
  dom.profilesSection.hidden = !isProfiles;
  dom.settingsSection.hidden = !isSettings;
  dom.macrosSection.hidden = !isMacros;

  renderConnection();
  if (isLighting) {
    renderControls();
  }
  renderPreview();
  if (settingsBoard) {
    settingsBoard.light(state.lighting.mode === 0x00
      ? null
      : `rgb(${state.lighting.color[0]} ${state.lighting.color[1]} ${state.lighting.color[2]})`);
  }
}

function renderConnection() {
  const color = state.lighting.color;
  const css = `rgb(${color[0]} ${color[1]} ${color[2]})`;

  dom.tabDot.classList.toggle('is-on', state.connected);
  dom.chip.style.background = state.connected ? css : '';

  dom.readout.hidden = !state.connected;
  if (state.connected) {
    dom.mode.textContent = modeName(state.lighting.mode);
    dom.rgb.textContent = color.join(', ');
    dom.deviceState.textContent = 'AK820 · wired';
    dom.deviceConnection.textContent = 'Connected';
  } else {
    dom.deviceState.textContent = 'AK820 · wired';
    dom.deviceConnection.textContent = state.deviceState === 'busy'
      ? 'Held by another program'
      : 'Not connected';
  }

  dom.banner.hidden = state.connected && !state.failure;
  dom.bannerText.textContent = state.failure || 'No keyboard found';
  dom.checkAgain.textContent = state.checking ? 'Checking…' : state.failure ? 'Try again' : 'Check again';
  dom.checkAgain.disabled = state.checking;
}

/* -- navigation and polling ---------------------------------------------- */

function goToSection(animate) {
  const wanted = window.location.hash.replace('#', '');
  const next = SECTIONS.some((item) => item.id === wanted) ? wanted : 'lighting';
  const changed = next !== state.section;
  state.section = next;
  if (state.rememberSection) {
    try {
      localStorage.setItem('ak820-section', next);
    } catch (err) {
      /* No storage; the section is simply not remembered. */
    }
  }
  render();
  if (next === 'lighting') {
    scrollToChosenMode();
  }
  if (next === 'per-key' && !state.keyColors.length) {
    loadKeyColors();
  }
  if (next === 'profiles') {
    loadProfiles();
  }
  if (next === 'settings') {
    loadSettings();
  }
  if (next === 'macros') {
    loadMacros();
  }
  if (animate && changed) {
    enterSection();
  }
}

/* A section that has just been opened settles into place. It is a one-off,
   so a keyframe is right, and it never plays on the first load. */
function enterSection() {
  /* The panel that is actually on screen is the one to animate. Picking a
     fixed one meant three of the five sections animated a panel that was
     hidden, and so nothing moved at all. */
  const panel = document.querySelector('.canvas-inner:not([hidden])');
  if (!panel) return;
  const cards = panel.querySelectorAll('.card');
  for (const card of cards) {
    card.classList.remove('section-enter');
  }
  // Reading the layout is what lets the same animation play twice.
  void panel.offsetWidth;
  cards.forEach((card, index) => {
    card.style.animationDelay = `${index * 60}ms`;
    card.classList.add('section-enter');
  });
}

async function checkNow() {
  if (state.checking) return;
  state.checking = true;
  render();
  await refresh();
  state.checking = false;
  render();
}

window.addEventListener('hashchange', () => goToSection(true));

dom.checkAgain.addEventListener('click', checkNow);
dom.topbarRefresh.addEventListener('click', checkNow);
dom.themeToggle.addEventListener('click', () => {
  const next = currentTheme() === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  /* The theme is the app's own setting, so the switch in the top bar has
     to save it there too - otherwise the next start would put it back. */
  post('/api/settings', { key: 'theme', value: next })
    .catch((err) => showApplied(err.message, true));
});

/* -- starting up --------------------------------------------------------- */

const lightingPicker = AkPicker.create(dom.picker, (color) => {
  state.lighting.color = color;
  renderColour(color);
  scheduleApply();
}, { onFavourite: toggleFavourite });
const perKeyPicker = AkPicker.create(dom.perkeyPicker, (color) => {
  state.paintColour = color;
  renderPerKeyColour();
  if (state.selectedKey) {
    paintKey(state.selectedKey, color);
  }
}, { onFavourite: toggleFavourite });

buildPalette(dom.palette, (color) => {
  lightingPicker.set(color);
  state.lighting.color = color;
  renderColour(color);
  scheduleApply();
});
buildPalette(dom.perkeyPalette, (color) => {
  perKeyPicker.set(color);
  state.paintColour = color;
  renderPerKeyColour();
  if (state.selectedKey) {
    paintKey(state.selectedKey, color);
  }
});
dom.perkeyAll.addEventListener('click', paintEveryKey);
dom.perkeyClear.addEventListener('click', clearEveryKey);
dom.perkeyInvert.addEventListener('click', invertEveryKey);

dom.profileSave.addEventListener('click', saveProfile);
dom.profileRename.addEventListener('click', renameProfile);
dom.profileDelete.addEventListener('click', deleteProfile);
dom.profileDuplicate.addEventListener('click', duplicateProfile);
dom.profileExport.addEventListener('click', exportProfile);
dom.profileImport.addEventListener('click', importProfile);
dom.boardProfileSave.addEventListener('click', async () => {
  if (state.selectedBoardProfile === null) return;
  try {
    await post('/api/board-profiles', { index: state.selectedBoardProfile });
    showApplied(`Saved into profile ${state.selectedBoardProfile + 1} on the keyboard.`);
    await loadProfiles();
  } catch (err) {
    showApplied(err.message, true);
  }
});

dom.macroRecord.addEventListener('click', startRecording);
dom.macroRecordStop.addEventListener('click', stopRecording);
dom.macroRecordCancel.addEventListener('click', cancelRecording);
dom.macroPlay.addEventListener('click', playMacro);
dom.macroRename.addEventListener('click', renameMacro);
dom.macroDelete.addEventListener('click', deleteMacro);
dom.remapActive.addEventListener('change', (event) => setRemap(event.target.checked));
dom.remapAdd.addEventListener('click', addRemap);
dom.settingsReset.addEventListener('click', async () => {
  if (!confirmDelete('Put the app\'s settings back to how they came?')) return;
  try {
    await post('/api/settings/reset', {});
    await loadSettings();
    showApplied('The settings are back to how they came.');
  } catch (err) {
    showApplied(err.message, true);
  }
});
dom.lightingReset.addEventListener('click', async () => {
  if (!confirmDelete('Put the keyboard\'s lighting back to how it came?')) return;
  try {
    await post('/api/lighting/reset', {});
    showApplied('The keyboard is back to how it came.');
    await refresh();
  } catch (err) {
    showApplied(err.message, true);
  }
});

buildBrightness();
buildSpeed();
buildDirection();
renderColour(state.lighting.color);
renderPerKeyColour();
setTheme(currentTheme(), false);
loadFavourites();

/* Open on the section the user left the app on, unless they asked not to. */
try {
  const saved = localStorage.getItem('ak820-section');
  if (saved && !window.location.hash && SECTIONS.some((item) => item.id === saved)) {
    history.replaceState(null, '', `#${saved}`);
  }
} catch (err) {
  /* No storage; the app always starts on Lighting. */
}
goToSection(false);
loadModes();
/* The theme is the app's own setting, so loading the settings is what
   puts it right. The browser's storage only holds a copy of it, for the
   page to pick before the first paint. */
loadSettings();
loadGeometry().then(() => {
  if (!state.geometry) return;
  board = AkBoard.create(dom.board, state.geometry, { tint: true });
  perKeyBoard = AkBoard.create(dom.perkeyBoard, state.geometry, {
    editable: true,
    onPick: (key, event) => {
      selectKey(key);
      if (event) event.preventDefault();
    },
    onBrush: (key) => {
      /* The brush is on, so every key the mouse goes over is painted. */
      if (!dom.perkeyBrush.checked) return;
      paintKey(key, state.paintColour);
    },
  });
  if (dom.settingsBoard) {
    settingsBoard = AkBoard.create(dom.settingsBoard, state.geometry, { tint: true });
  }
  renderPreview();
  paintBoard();
});
refresh();
schedulePoll();

/* The app checks the keyboard on its own clock. How often is a setting, so
   the wait is set again after every check rather than fixed for ever.
   "Never" means never: no timer is armed at all. */
function schedulePoll() {
  if (pollTimer) {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }
  const seconds = Number(state.checkInterval) || 0;
  if (!seconds) return;
  pollTimer = window.setTimeout(async () => {
    pollTimer = null;
    if (!document.hidden) await refresh();
    schedulePoll();
  }, Math.max(500, seconds * 1000));
}
