/* The colour picker: a saturation and brightness square, a hue strip and a
 * hex field.
 *
 * The lighting section and the per-key editor both need one, so this is a
 * component: it takes the colours it is given and hands back the colour the
 * user picked. It works with the mouse and from the keyboard.
 *
 * Each gradient sits inside a little padding. The handle's centre can then
 * reach the very ends of the gradient - white at the top left of the square,
 * black at the bottom, red at the top of the strip - while the handle
 * itself still has room to hang over the edge instead of being cut off.
 */

window.AkPicker = (function () {
  'use strict';

  function toHex(rgb) {
    return '#' + rgb.map((c) => c.toString(16).padStart(2, '0')).join('');
  }

  function fromHex(text) {
    const match = /^#?([0-9a-f]{6})$/i.exec(String(text).trim());
    if (!match) return null;
    const value = parseInt(match[1], 16);
    return [(value >> 16) & 0xff, (value >> 8) & 0xff, value & 0xff];
  }

  function toHsv(r, g, b) {
    const red = r / 255;
    const green = g / 255;
    const blue = b / 255;
    const max = Math.max(red, green, blue);
    const min = Math.min(red, green, blue);
    const d = max - min;
    let h = 0;
    if (d !== 0) {
      if (max === red) {
        h = ((green - blue) / d + (green < blue ? 6 : 0)) / 6;
      } else if (max === green) {
        h = ((blue - red) / d + 2) / 6;
      } else {
        h = ((red - green) / d + 4) / 6;
      }
    }
    return { h: h, s: max === 0 ? 0 : d / max, v: max };
  }

  function toRgb(h, s, v) {
    const hue = ((h % 1) + 1) % 1;
    const sector = hue * 6;
    const c = v * s;
    const x = c * (1 - Math.abs((sector % 2) - 1));
    const m = v - c;
    let r = 0;
    let g = 0;
    let b = 0;
    if (sector < 1) { r = c; g = x; }
    else if (sector < 2) { r = x; g = c; }
    else if (sector < 3) { g = c; b = x; }
    else if (sector < 4) { g = x; b = c; }
    else if (sector < 5) { r = x; b = c; }
    else { r = c; b = x; }
    return [
      Math.round((r + m) * 255),
      Math.round((g + m) * 255),
      Math.round((b + m) * 255),
    ];
  }

  function create(root, onChange, options) {
    const settings = options || {};
    root.classList.add('picker');
    root.innerHTML = [
      '<div class="picker-square" tabindex="0" role="application"',
      '     aria-label="Saturation and brightness. Use the arrow keys to move the marker.">',
      '  <div class="picker-gradient">',
      '    <span class="picker-marker"></span>',
      '  </div>',
      '</div>',
      '<div class="picker-hue" tabindex="0" role="application"',
      '     aria-label="Hue. Use the arrow keys to change the hue.">',
      '  <div class="picker-hue-gradient">',
      '    <span class="picker-hue-marker"></span>',
      '  </div>',
      '</div>',
      '<label class="picker-hex">',
      '  <span class="visually-hidden">Hex colour</span>',
      '  <input type="text" spellcheck="false" autocomplete="off" maxlength="7" value="#000000">',
      '</label>',
      '<div class="picker-actions">',
      '  <button class="picker-action" type="button" data-action="random">Random</button>',
      '  <button class="picker-action" type="button" data-action="favourite" hidden>Pin</button>',
      '</div>',
    ].join('');

    const square = root.querySelector('.picker-square');
    const gradient = root.querySelector('.picker-gradient');
    const marker = root.querySelector('.picker-marker');
    const hue = root.querySelector('.picker-hue');
    const hueGradient = root.querySelector('.picker-hue-gradient');
    const hueMarker = root.querySelector('.picker-hue-marker');
    const hex = root.querySelector('.picker-hex input');
    const state = { h: 0, s: 1, v: 1 };
    let quiet = false;

    function current() {
      return toRgb(state.h, state.s, state.v);
    }

    function paint(force) {
      const rgb = current();
      gradient.style.setProperty('--hue', String(state.h * 360));
      marker.style.setProperty('--sat', String(state.s));
      marker.style.setProperty('--val', String(state.v));
      // The marker is filled with the colour that is chosen, so it can be
      // seen on a light colour as well as on a dark one.
      marker.style.setProperty('--picker-colour',
        `rgb(${rgb[0]} ${rgb[1]} ${rgb[2]})`);
      hueMarker.style.setProperty('--hue', String(state.h));
      // The hex field is left alone while it is being typed into, but when the
      // colour is changed some other way it has to follow, or it would go on
      // showing a colour that is not the current one.
      if (force || document.activeElement !== hex) {
        hex.value = toHex(rgb);
      }
    }

    function changed() {
      paint(true);
      if (!quiet && onChange) onChange(current());
    }

    function set(rgb, notify) {
      const hsv = toHsv(rgb[0], rgb[1], rgb[2]);
      state.h = hsv.h;
      state.s = hsv.s;
      state.v = hsv.v;
      quiet = !notify;
      paint(false);
      quiet = false;
    }

    /* Where the pointer is, as a share of the gradient itself. Clicking on
       the very edge gives the exact colour at that edge. */
    function point(event, element) {
      const box = element.getBoundingClientRect();
      if (!box.width || !box.height) {
        return { x: 0, y: 0 };
      }
      return {
        x: Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)),
        y: Math.min(1, Math.max(0, (event.clientY - box.top) / box.height)),
      };
    }

    function pickSquare(event) {
      const where = point(event, gradient);
      state.s = where.x;
      state.v = 1 - where.y;
      changed();
    }

    function pickHue(event) {
      const where = point(event, hueGradient);
      state.h = where.y;
      changed();
    }

    square.addEventListener('pointerdown', (event) => {
      square.setPointerCapture(event.pointerId);
      pickSquare(event);
    });
    square.addEventListener('pointermove', (event) => {
      if (square.hasPointerCapture(event.pointerId)) pickSquare(event);
    });
    hue.addEventListener('pointerdown', (event) => {
      hue.setPointerCapture(event.pointerId);
      pickHue(event);
    });
    hue.addEventListener('pointermove', (event) => {
      if (hue.hasPointerCapture(event.pointerId)) pickHue(event);
    });

    const MOVES = {
      ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1],
    };

    square.addEventListener('keydown', (event) => {
      const move = MOVES[event.key];
      if (!move) return;
      event.preventDefault();
      const step = event.shiftKey ? 0.1 : 0.02;
      state.s = Math.min(1, Math.max(0, state.s + move[0] * step));
      state.v = Math.min(1, Math.max(0, state.v - move[1] * step));
      changed();
    });

    hue.addEventListener('keydown', (event) => {
      const move = MOVES[event.key];
      if (!move) return;
      event.preventDefault();
      const step = event.shiftKey ? 0.1 : 0.02;
      state.h = (state.h + move[1] * step + 1) % 1;
      changed();
    });

    hex.addEventListener('change', () => {
      const rgb = fromHex(hex.value);
      if (!rgb) {
        hex.value = toHex(current());
        return;
      }
      set(rgb, false);
      if (onChange) onChange(rgb);
    });

    /* A random colour, in the same shape as a colour the user would pick:
       a random hue, a good deal of colour in it and a bright value. */
    const random = root.querySelector('[data-action="random"]');
    const favourite = root.querySelector('[data-action="favourite"]');
    if (settings.onFavourite) favourite.hidden = false;

    random.addEventListener('click', () => {
      state.h = Math.random();
      state.s = 0.65 + Math.random() * 0.35;
      state.v = 0.75 + Math.random() * 0.25;
      changed();
    });

    favourite.addEventListener('click', () => {
      if (settings.onFavourite) settings.onFavourite(current());
    });

    paint();
    return { set: set, get: current };
  }

  return { create: create, toHex: toHex, fromHex: fromHex };
})();
