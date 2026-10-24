/* The board: a drawing of the AK820, with a click target on every key.
 *
 * The board is drawn here, from the key geometry in
 * ``ui/assets/ak820-caps.json``: eighty-two keycaps in the places they
 * sit on the board, plus the knob.  Drawing it rather than using a
 * picture of the board means the colour on a key is the colour of that
 * key, the labels can be read, and it stays sharp at any size.
 *
 * The key geometry was worked out once from a picture of the board; the
 * places the keys sit are facts about the keyboard, and everything drawn
 * from them is this app's own work.
 */

window.AkBoard = (function () {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';

  /* Every board on the page needs its own names for the gradient and the
     shape of the keycaps, so the three of them do not fight. */
  let serial = 0;

  function node(tag, attributes) {
    const made = document.createElementNS(NS, tag);
    for (const name in attributes) made.setAttribute(name, attributes[name]);
    return made;
  }

  /* How dark a colour is, so the label on a key can be read against it.
     A key with no colour of its own keeps the ordinary dark label. */
  function isDark(colour) {
    if (!colour) return false;
    const match = /rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(colour);
    if (!match) return false;
    const red = Number(match[1]);
    const green = Number(match[2]);
    const blue = Number(match[3]);
    return (red * 299 + green * 587 + blue * 114) / 1000 < 140;
  }

  function create(root, geometry, options) {
    const settings = options || {};
    root.classList.add('board');
    if (settings.tint) root.classList.add('board-tint');
    const name = 'akboard-' + (++serial);
    root.innerHTML = [
      '<svg class="board-art" aria-hidden="true"></svg>',
      '<div class="board-keys"></div>',
    ].join('');

    const art = root.querySelector('.board-art');
    art.setAttribute('viewBox', `0 0 ${geometry.width} ${geometry.height}`);
    art.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    const caps = new Map();
    const legends = new Map();

    const defs = node('defs', {});
    const wave = node('linearGradient', {
      id: `${name}-wave`, x1: '0', y1: '0', x2: '1', y2: '0',
    });
    wave.appendChild(node('stop', { offset: '0', 'stop-color': '#ffffff', 'stop-opacity': '0' }));
    wave.appendChild(node('stop', { offset: '0.42', 'stop-color': '#ffffff', 'stop-opacity': '0.5' }));
    wave.appendChild(node('stop', { offset: '0.58', 'stop-color': '#000000', 'stop-opacity': '0.3' }));
    wave.appendChild(node('stop', { offset: '1', 'stop-color': '#000000', 'stop-opacity': '0' }));
    defs.appendChild(wave);

    const sheen = node('linearGradient', {
      id: `${name}-sheen`, x1: '0', y1: '0', x2: '0', y2: '1',
    });
    sheen.appendChild(node('stop', { offset: '0', 'stop-color': '#ffffff', 'stop-opacity': '0.34' }));
    sheen.appendChild(node('stop', { offset: '1', 'stop-color': '#000000', 'stop-opacity': '0.16' }));
    defs.appendChild(sheen);

    /* The keycaps, as a shape, so the light can be kept to them. */
    const capShape = node('clipPath', { id: `${name}-caps` });
    defs.appendChild(capShape);
    art.appendChild(defs);

    art.appendChild(node('rect', {
      class: 'board-case', x: '0', y: '0',
      width: String(geometry.width), height: String(geometry.height), rx: '10',
    }));

    const capGroup = node('g', { class: 'board-caps' });
    art.appendChild(capGroup);
    const legendGroup = node('g', { class: 'board-legends' });

    for (const key of geometry.keys) {
      /* The key's place on the board is a cell; the cap is drawn a little
         inside it, so the keys are told apart. */
      const gap = 1.6;
      const cap = node('rect', {
        class: 'board-cap',
        x: String(key.x + gap), y: String(key.y + gap),
        width: String(Math.max(2, key.w - gap * 2)),
        height: String(Math.max(2, key.h - gap * 2)),
        rx: '3.5',
      });
      capGroup.appendChild(cap);
      caps.set(key.led, cap);
      capShape.appendChild(node('rect', {
        x: String(key.x + gap), y: String(key.y + gap),
        width: String(Math.max(2, key.w - gap * 2)),
        height: String(Math.max(2, key.h - gap * 2)),
        rx: '3.5',
      }));

      if (key.label) {
        const legend = node('text', {
          class: 'board-legend',
          x: String(key.x + key.w / 2),
          y: String(key.y + key.h / 2 + 0.5),
        });
        legend.textContent = key.label;
        legendGroup.appendChild(legend);
        legends.set(key.led, legend);
      }
    }

    if (geometry.knob) {
      /* The knob sits over the Home/PgUp/PgDn/End column; its x and y in
         the geometry are the top-left of its circle, same as a key. */
      const knob = geometry.knob;
      const size = 46;
      const left = knob.x !== undefined ? knob.x : geometry.width - size - 14;
      const top = knob.y !== undefined ? knob.y : 12;
      art.appendChild(node('circle', {
        class: 'board-knob',
        cx: String(left + size / 2),
        cy: String(top + size / 2),
        r: String(size / 2),
      }));
    }

    /* The light that sweeps across the keys, and the shading on the top
       of them.  Both are kept to the keycaps, so the case stays still. */
    const lit = node('g', { 'clip-path': `url(#${name}-caps)` });
    lit.appendChild(node('rect', {
      class: 'board-wave', x: String(-geometry.width), y: '0',
      width: String(geometry.width), height: String(geometry.height),
      fill: `url(#${name}-wave)`,
    }));
    art.appendChild(lit);
    const top = node('g', { 'clip-path': `url(#${name}-caps)` });
    top.appendChild(node('rect', {
      class: 'board-sheen', x: '0', y: '0',
      width: String(geometry.width), height: String(geometry.height),
      fill: `url(#${name}-sheen)`,
    }));
    art.appendChild(top);

    /* The legends go on last, so the light crossing the board does not
       wash them out. */
    art.appendChild(legendGroup);

    const layer = root.querySelector('.board-keys');
    const nodes = new Map();

    if (settings.editable) {
      /* The mouse is down on the board, so every key it goes over is a key
         the user is painting. */
      let down = false;
      layer.addEventListener('pointerdown', () => { down = true; }, true);
      window.addEventListener('pointerup', () => { down = false; });
      window.addEventListener('pointercancel', () => { down = false; });

      for (const key of geometry.keys) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'board-key';
        button.dataset.led = String(key.led);
        button.title = key.label;
        button.setAttribute('aria-label', key.label);
        button.addEventListener('click', (event) => {
          if (settings.onPick) settings.onPick(key, event);
        });
        const brush = (event) => {
          if (down && settings.onBrush) settings.onBrush(key, event);
        };
        button.addEventListener('pointerdown', brush);
        button.addEventListener('pointerenter', brush);
        layer.appendChild(button);
        nodes.set(key.led, button);
      }
    }

    /* The picture is fitted inside the board, so where a key sits on the
       screen depends on how big the board is. This works that out. */
    function layout() {
      const box = root.getBoundingClientRect();
      if (!box.width || !box.height) return;
      const scale = Math.min(box.width / geometry.width, box.height / geometry.height);
      const shownWidth = geometry.width * scale;
      const shownHeight = geometry.height * scale;
      const left = (box.width - shownWidth) / 2;
      const top = (box.height - shownHeight) / 2;
      for (const key of geometry.keys) {
        const button = nodes.get(key.led);
        if (!button) continue;
        button.style.left = `${left + key.x * scale}px`;
        button.style.top = `${top + key.y * scale}px`;
        button.style.width = `${key.w * scale}px`;
        button.style.height = `${key.h * scale}px`;
      }
    }

    if (typeof ResizeObserver !== 'undefined') {
      new ResizeObserver(layout).observe(root);
    }
    window.addEventListener('resize', layout);
    layout();

    function paint(led, colour) {
      const cap = caps.get(led);
      if (!cap) return;
      cap.classList.toggle('is-lit', Boolean(colour));
      cap.style.fill = colour || '';
      const legend = legends.get(led);
      if (legend) legend.classList.toggle('is-dark', isDark(colour));
    }

    return {
      root: root,
      layout: layout,
      /* Light every key on the board the same colour. */
      light: function (colour) {
        for (const key of geometry.keys) paint(key.led, colour);
      },
      select: function (led) {
        for (const [id, button] of nodes) {
          button.classList.toggle('is-selected', id === led);
        }
      },
      paintKey: paint,
    };
  }

  return { create: create };
})();
