// The game's HUD rebuilt in HTML for the interface mockups. One structure for
// every theme: a theme is a stylesheet (temas/<id>.css) plus a few layout
// choices (see temas/catalogo.js), so variants compare like for like.
// Texts come from the game (kit/datos.js, generated); the few that the game
// does not have yet are in NUEVOS and marked as new in the page.
(function () {
  'use strict';
  const D = window.DATOS;
  const I = window.icono;

  // --- Texts ----------------------------------------------------------------------------------

  const NUEVOS = {
    es: {
      'mk.production': 'Producción', 'mk.perDay': '+{0} al día', 'mk.produces': 'Produce',
      'mk.needs': 'Para mejorar', 'mk.bonus': 'Entorno', 'mk.residents': 'Habitantes', 'mk.level': 'Nivel',
      'mk.annexes': 'Anexos', 'mk.firewood': 'Leña', 'mk.materials': 'Materiales', 'mk.progress': 'Avance',
      'mk.live': 'En vivo', 'mk.season': 'Temporada', 'mk.state': 'Estado', 'mk.layers': 'Capas',
      'mk.history': 'Últimos 12 meses', 'mk.next': 'Siguiente', 'mk.prev': 'Anterior', 'mk.all': 'Todo',
      'mk.workers': 'Trabajadores', 'mk.store': 'Guardado', 'mk.search': 'Buscar edificio…',
      'mk.start': 'Construir', 'mk.order': 'Orden', 'mk.days': '{0} días', 'mk.new': 'nuevo',
      'mk.menu': 'Menú', 'mk.villager': 'Aldeano', 'mk.thing': 'Recurso',
    },
    en: {
      'mk.production': 'Production', 'mk.perDay': '+{0} a day', 'mk.produces': 'Produces',
      'mk.needs': 'To upgrade', 'mk.bonus': 'Surroundings', 'mk.residents': 'Residents', 'mk.level': 'Level',
      'mk.annexes': 'Annexes', 'mk.firewood': 'Firewood', 'mk.materials': 'Materials', 'mk.progress': 'Progress',
      'mk.live': 'Live', 'mk.season': 'Season', 'mk.state': 'State', 'mk.layers': 'Layers',
      'mk.history': 'Last 12 months', 'mk.next': 'Next', 'mk.prev': 'Previous', 'mk.all': 'All',
      'mk.workers': 'Workers', 'mk.store': 'Stored', 'mk.search': 'Find a building…',
      'mk.start': 'Build', 'mk.order': 'Order', 'mk.days': '{0} days', 'mk.new': 'new',
      'mk.menu': 'Menu', 'mk.villager': 'Villager', 'mk.thing': 'Resource',
    },
  };

  let lang = 'es';

  function t(key, ...args) {
    let s = (NUEVOS[lang] && NUEVOS[lang][key]) || (D.textos[lang] && D.textos[lang][key]);
    if (s === undefined) s = D.textos.es[key];
    if (s === undefined) return key;
    if (typeof s === 'object') s = args[0] === 1 ? s.one : s.other;
    return s.replace(/\{(\d+)(?::[^}]*)?\}/g, (m, i) => (args[+i] === undefined ? m : String(args[+i])));
  }

  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const fmt = n => (lang === 'es' ? n.toLocaleString('es-MX') : n.toLocaleString('en-US'));

  // --- The town shown ---------------------------------------------------------------------------

  const building = id => D.edificios.find(b => b.id === id);
  const resource = id => D.recursos.find(r => r.id === id);
  const portrait = id => D.retratos.find(p => p.id === id);
  const race = id => D.razas.find(r => r.id === id);

  const GLYPH = {  // Resource -> our icon and its tint.
    'core:log': ['log', '#b07a48'], 'core:stone': ['stone', '#a8a8a0'], 'core:firewood': ['firewood', '#e08a3a'],
    'core:clothes': ['shirt', '#6a9ad0'], 'core:gold': ['coins', '#e8c45a'], 'core:wheat': ['wheat', '#e0c070'],
    'core:berries': ['berry', '#d0505a'], 'core:fish': ['fish', '#7ab0d0'], 'core:meat': ['meat', '#d07060'],
    'core:bread': ['bread', '#d8a060'], 'core:eggs': ['egg', '#f0e0c0'], 'core:honey': ['honey', '#f0b030'],
    'core:herbs': ['herb', '#70b060'], 'core:tools': ['tools', '#b0b8c0'], 'core:weapons': ['sword', '#c0c8d0'],
    'core:wool': ['wool', '#e8e0d0'], 'core:fruit': ['apple', '#e06040'], 'core:vegetables': ['herb', '#80c050'],
    'core:iron': ['tools', '#9aa4ae'], 'core:iron_ore': ['stone', '#8a7a70'], 'core:coal': ['stone', '#505058'],
    'core:clay': ['stone', '#c08060'], 'core:bricks': ['box', '#c06a4a'], 'core:shoes': ['bag', '#8a6a4a'],
    'core:bows': ['bow', '#b08a5a'], 'core:smoked_meat': ['meat', '#a05a40'], 'core:beer': ['drop', '#e0b040'],
    'core:wine': ['drop', '#9a3a5a'],
  };
  const FOOD = '#e06a4a';

  /** A resource picture: the 3D render when the theme asks for it and there is one, else our glyph. */
  function resIcon(id, cls) {
    const r = resource(id);
    const g = GLYPH[id] || ['box', '#c0b090'];
    const img = r && r.img ? `<img class="r3d" src="${r.img}" alt="">` : '';
    return `<span class="res-ic ${cls || ''}" style="--tint:${g[1]}">${I(g[0])}${img}</span>`;
  }

  const S = {
    stored: {'core:log': 57, 'core:stone': 73, 'core:firewood': 40, 'core:clothes': 12, 'core:tools': 6,
      'core:wheat': 18, 'core:berries': 8, 'core:fish': 14, 'core:bread': 9, 'core:eggs': 6, 'core:honey': 4,
      'core:wool': 10, 'core:iron': 3, 'core:herbs': 5},
    food: 57, population: 18, maxPop: 20, adults: 13, children: 5, happiness: 64, gold: 100, sick: 1, fires: 0,
    speed: 1, paused: false, season: 1, temp: 21, year: 2, month: 3, day: 14, night: false,
    category: 2, workers: 2,
  };

  // --- Small parts ------------------------------------------------------------------------------

  const tip = s => ` data-tip="${esc(s)}"`;

  function btn(icon, label, opts = {}) {
    const cls = ['btn', opts.cls || '', opts.on ? 'on' : '', opts.label === false ? 'icon-only' : ''].join(' ');
    const showLabel = label && opts.label !== false;
    return `<button class="${cls}"${opts.act ? ` data-act="${opts.act}"` : ''}${opts.tip ? tip(opts.tip) : ''}${label ? ` aria-label="${esc(label)}"` : ''}${opts.disabled ? ' disabled' : ''}>`
      + (icon ? I(icon) : '') + (showLabel ? `<span class="lbl">${esc(label)}</span>` : '') + '</button>';
  }

  function meter(fraction, opts = {}) {
    const p = Math.max(0, Math.min(1, fraction)) * 100;
    return `<span class="meter ${opts.cls || ''}"${opts.tip ? tip(opts.tip) : ''}><span class="fill" style="width:${p.toFixed(1)}%"></span></span>`;
  }

  function chip(icon, text, cls, tipText) {
    return `<span class="chip ${cls || ''}"${tipText ? tip(tipText) : ''}>${icon ? I(icon) : ''}<span>${esc(text)}</span></span>`;
  }

  function dot(state) { return `<span class="dot ${state}"></span>`; }

  function avatar(pid, cls) {
    const p = portrait(pid);
    return `<span class="avatar ${cls || ''}"><img src="${p.img}" alt=""></span>`;
  }

  function newMark() { return `<span class="newmark"${tip(t('mk.new') + ': ' + (lang === 'es' ? 'el juego aún no lo muestra' : 'the game does not show it yet'))}>✦</span>`; }

  function costChips(cost) {
    return Object.entries(cost).map(([id, n]) => `<span class="cost">${resIcon(id, 'sm')}<b>${n}</b></span>`).join('');
  }

  // --- Top bar ----------------------------------------------------------------------------------

  const SEASONS = ['hud.season.spring', 'hud.season.summer', 'hud.season.autumn', 'hud.season.winter'];
  const SEASON_ICON = ['sprout', 'sun', 'leaf', 'snow'];

  function topBar() {
    const res = [
      ['food', 'apple', FOOD, t('hud.food', S.food).replace(/\s*[\d.,]+$/, ''), S.food, t('hud.food.tooltip')],
      ['core:log'], ['core:stone'], ['core:firewood'], ['core:clothes'],
    ].map(r => {
      if (r[0] === 'food') {
        return `<span class="tb-item res"${tip(r[3] + ' ' + r[4] + '\n' + r[5])}><span class="res-ic" style="--tint:${r[2]}">${I(r[1])}<img class="r3d" src="img/cosas/basket_back.png" alt=""></span><b>${fmt(r[4])}</b><span class="tb-name">${esc(r[3])}</span></span>`;
      }
      const def = resource(r[0]);
      const name = t(def.nombre);
      return `<span class="tb-item res"${tip(name)}>${resIcon(r[0])}<b>${fmt(S.stored[r[0]])}</b><span class="tb-name">${esc(name)}</span></span>`;
    }).join('');
    const more = `<span class="tb-item more"${tip(['core:tools', 'core:wool', 'core:iron'].map(id => t('hud.amount', t(resource(id).nombre), S.stored[id])).join('\n'))}>${esc(t('hud.more', 3))}</span>`;
    const pop = `<span class="tb-item pop"${tip(t('hud.population.tooltip', S.adults, 4, 6, 1))}>${I('users')}<b>${S.population}</b><span class="of">/ ${S.maxPop}</span><span class="tb-name">${esc(t('hud.population', '').trim())}</span></span>`;
    const joy = `<span class="tb-item joy"${tip(t('hud.happiness.tooltip'))}>${I('smile')}<b>${S.happiness} %</b>${meter(S.happiness / 100, {cls: 'mini ok'})}</span>`;
    const gold = `<span class="tb-item gold"${tip(t('hud.gold.tooltip', 60, 40, 0))}>${resIcon('core:gold')}<b>${S.gold}</b></span>`;
    const troubles = `<span class="tb-item alert"${tip(t('hud.troubles.tooltip'))}>${I('pill')}<b>${S.sick}</b></span>`;
    const weather = `<span class="tb-item time"${tip(t('hud.day.tooltip', 4, '20') + '\n' + t('hud.weather.tooltip', 0))}>`
      + `${I(S.night ? 'moon' : SEASON_ICON[S.season])}<span class="two"><span>${esc(t('hud.weather', t(SEASONS[S.season]), S.temp))}</span>`
      + `<span class="dim">${esc(t('hud.date', S.year, S.month, S.day))}</span></span></span>`;
    const speed = `<span class="tb-speed">`
      + btn(S.paused ? 'play' : 'pause', t('hud.speed.pause'), {act: 'pause', tip: t('hud.speed.pause.tooltip'), on: S.paused, label: false})
      + btn('slower', t('hud.speed.slower'), {act: 'slower', tip: t('hud.speed.slower.tooltip'), label: false})
      + `<span class="speed-val${S.paused ? ' dim' : ''}">${esc(t('hud.speed.value', S.speed))}</span>`
      + btn('faster', t('hud.speed.faster'), {act: 'faster', tip: t('hud.speed.faster.tooltip'), label: false})
      + `</span>`;
    return `<div class="topbar"><div class="tb-group tb-res">${res}${more}</div>`
      + `<div class="tb-group tb-town">${pop}${troubles}${joy}${gold}</div>`
      + `<div class="tb-group tb-clock">${weather}${speed}</div></div>`;
  }

  // --- Dock, minimap ------------------------------------------------------------------------------

  const DOCK = [
    ['goods', 'box', 'hud.dock.goods', 'hud.dock.goods.tooltip'],
    ['stats', 'chart', 'hud.dock.stats', 'hud.dock.stats.tooltip'],
    ['log', 'list', 'hud.dock.log', 'hud.dock.log.tooltip'],
    ['layers', 'layers', 'hud.dock.layers', 'hud.dock.layers.tooltip'],
    ['trade', 'scales', 'hud.trade', 'hud.trade.tooltip'],
    ['army', 'shield', 'hud.dock.army', 'hud.army.tooltip'],
  ];

  function dock(open) {
    return '<nav class="dock">' + DOCK.map(([id, icon, label, tipKey]) =>
      `<button class="btn dock-btn${open.has(id) ? ' on' : ''}" data-act="dock" data-win="${id}"${tip(t(label) + '\n' + t(tipKey))}>${I(icon)}<span class="lbl">${esc(id === 'army' ? t('hud.army', 4) : t(label))}</span>${id === 'log' ? '<span class="badge">3</span>' : ''}</button>`).join('') + '</nav>';
  }

  function minimap() {
    return `<div class="minimap"${tip(t('hud.minimap.tooltip'))}><div class="mm-frame"><img src="fondos/minimapa.jpg" alt=""></div>`
      + `<span class="mm-n">${t('hud.minimap.north')}</span><span class="mm-s">${t('hud.minimap.south')}</span>`
      + `<span class="mm-e">${t('hud.minimap.east')}</span><span class="mm-w">${t('hud.minimap.west')}</span>`
      + `<div class="mm-tools">${btn('plus', '', {label: false, tip: t('action.camera.zoomIn')})}${btn('minus', '', {label: false, tip: t('action.camera.zoomOut')})}${btn('layers', '', {label: false, act: 'dock', tip: t('hud.dock.layers')})}</div>`
      + `</div><div class="compass"${tip(t('hud.compass.tooltip'))}><svg viewBox="0 0 40 40"><path class="n" d="M20 4l6 16H14z"/><path class="sth" d="M20 36l6-16H14z"/></svg></div>`;
  }

  // --- Build bar -----------------------------------------------------------------------------------

  const CAT_ICON = ['home', 'wheatfield', 'axe', 'factory', 'well', 'flower', 'shield', 'fountain', 'stall', 'tree', 'landmark', 'ruins'];
  const CAT_KEYS = ['housing', 'food', 'resources', 'industry', 'services', 'decoration', 'defense', 'plaza', 'garden', 'nature', 'monuments', 'ruins'];

  function buildTip(b) {
    const cost = Object.entries(b.costo).map(([id, n]) => `${t(resource(id).nombre)} ${n}`).join(', ') || t('hud.cost.free');
    let s = t(b.nombre) + '\n' + t('hud.build.cost', cost) + '\n' + t('hud.build.size', b.tamano[0], b.tamano[1]);
    if (b.trabajadores) s += '\n' + t('hud.build.workers', b.trabajadores);
    if (b.habitantes) s += '\n' + t('hud.build.residents', b.habitantes);
    if (b.guarda) s += '\n' + t('hud.build.storage', b.guarda);
    if (b.nivel > 1) s += '\n' + t('hud.build.locked', b.nivel);
    return s;
  }

  function buildItems(cat) {
    const list = D.edificios.filter(b => b.categoria === cat && b.id !== 'core:town_center' && b.img).slice(0, 16);
    return list.map(b => {
      const locked = b.nivel > 1;
      return `<button class="bb-item${locked ? ' locked' : ''}${b.id === 'core:stonecutter' ? ' on' : ''}" data-act="place"${tip(buildTip(b))}>`
        + `<span class="bb-thumb"><img src="${b.img}" alt="">${locked ? `<span class="bb-lock">${I('lock')}<b>${b.nivel}</b></span>` : ''}</span>`
        + `<span class="bb-name">${esc(t(b.nombre))}</span><span class="bb-cost">${costChips(b.costo)}</span></button>`;
    }).join('');
  }

  function buildBar(layout) {
    if (layout.build === 'none') return '';
    const cats = CAT_KEYS.map((k, i) => `<button class="btn bb-cat${i === S.category && (S.catOpen || layout.build !== 'dock') ? ' on' : ''}" data-act="cat" data-cat="${i}"${tip(t('hud.build.cat.' + k))}>${I(CAT_ICON[i])}<span class="lbl">${esc(t('hud.build.cat.' + k))}</span></button>`).join('');
    const items = `<div class="bb-items-wrap"><button class="btn bb-arrow" data-act="scroll" data-dir="-1">${I('left')}</button><div class="bb-items">${buildItems(S.category)}</div><button class="btn bb-arrow" data-act="scroll" data-dir="1">${I('right')}</button></div>`;
    if (layout.build === 'start') {
      return `<div class="taskbar"><button class="btn start-btn${S.startOpen ? ' on' : ''}" data-act="start">${I('castle')}<span class="lbl">${esc(t('mk.start'))}</span></button>`
        + `<span class="tb-sep"></span><span class="task-wins"></span><span class="tray">${I('bell')}<span>${esc(t('hud.date', S.year, S.month, S.day))}</span></span></div>`
        + (!S.startOpen ? '' : `<div class="startmenu"><div class="sm-side"><span>SALVA'S PROSPERIA</span></div><div class="sm-cats">${cats}</div><div class="sm-items">${buildItems(S.category)}</div></div>`);
    }
    const shut = layout.build === 'dock' && !S.catOpen;
    return `<div class="buildbar${shut ? ' shut' : ''}"><div class="bb-cats">${cats}</div>${shut ? '' : items}</div>`;
  }

  // --- Windows ------------------------------------------------------------------------------------

  function winFrame(w, title, body, opts = {}) {
    const acts = (opts.eye ? btn('eye', t('hud.window.eye'), {cls: 'wbtn', act: 'eye', tip: t('hud.window.eye.tooltip')}) : '')
      + (opts.camera ? btn('camera', t('hud.window.camera'), {cls: 'wbtn', act: 'camera', tip: t('hud.window.camera.tooltip')}) : '');
    const ctl = btn(w.min ? 'restore' : 'minus', t(w.min ? 'hud.window.restore' : 'hud.window.minimize'), {cls: 'wbtn ctl-min', act: 'min', tip: t(w.min ? 'hud.window.restore.tooltip' : 'hud.window.minimize.tooltip')})
      + btn('pin', t(w.pinned ? 'hud.window.pinned' : 'hud.window.pin'), {cls: 'wbtn ctl-pin', act: 'pin', on: w.pinned, tip: t('hud.window.pin.tooltip')})
      + btn('x', t('hud.close'), {cls: 'wbtn ctl-close', act: 'close', tip: t('hud.window.close.tooltip')});
    const tabs = w.tabs ? `<div class="win-tabs">${w.tabs.map((tb, i) => `<button class="win-tab${i === 0 ? ' on' : ''}" data-act="tab">${tb}</button>`).join('')}</div>` : '';
    const style = `left:${w.x}px;top:${w.y}px;width:${w.w}px;${w.h ? `height:${w.h}px;` : ''}z-index:${w.z || 1}`;
    return `<section class="win win-${w.kind}${w.min ? ' minimized' : ''}${w.pinned ? ' pinned' : ''}" data-id="${w.id}" style="${style}">${tabs}`
      + `<header class="win-bar">${opts.icon || ''}<span class="win-titles"><h2 class="win-title">${esc(title)}</h2>${opts.sub ? `<span class="win-sub">${esc(opts.sub)}</span>` : ''}</span>`
      + `<span class="win-act">${acts}</span><span class="win-ctl">${ctl}</span></header>`
      + `<div class="win-body">${body}</div><span class="win-grip">${I('grip')}</span></section>`;
  }

  const thumbIcon = img => `<span class="win-icon"><img src="${img}" alt=""></span>`;

  function workerRow(pid, years, task, taskIcon) {
    const p = portrait(pid);
    return `<button class="row person" data-act="open"${tip(t('hud.villager.open.tooltip'))}>${avatar(pid)}<span class="row-main"><b>${esc(t('hud.villager.listed', p.nombre, years))}</b>`
      + `<span class="row-sub">${I(taskIcon)}${esc(task)}</span></span>${I('right', 'chev')}</button>`;
  }

  function stonecutterWin(w) {
    const b = building('core:stonecutter');
    const body = `<div class="hero"><img src="${b.img}" alt=""><span class="hero-chip">${chip('', t('hud.building.working'), 'ok', t('hud.building.production.tooltip'))}</span></div>`
      + `<div class="kv"><span class="k">${I('users')}${esc(t('mk.workers'))}</span><span class="v stepper">`
      + btn('minus', '', {label: false, cls: 'step', act: 'fewer', tip: t('hud.building.fewer.tooltip')})
      + `<b class="step-val"${tip(t('hud.building.workers', S.workers, 2, 2))}>${S.workers} / 2</b>`
      + btn('plus', '', {label: false, cls: 'step', act: 'more', tip: t('hud.building.more.tooltip')}) + '</span></div>'
      + `<div class="kv"><span class="k">${I('factory')}${esc(t('mk.production'))}</span><span class="v"><button class="switch on" data-act="switch"${tip(t('hud.building.production.tooltip'))}><span class="knob"></span></button></span></div>`
      + `<div class="kv"><span class="k">${resIcon('core:stone')}${esc(t('mk.produces'))}${newMark()}</span><span class="v"><b>${esc(t('mk.perDay', 4))}</b></span></div>`
      + `<div class="kv"><span class="k">${I('box')}${esc(t('hud.building.limitAuto').split(':')[0])}</span><span class="v">${chip('', lang === 'es' ? 'automático' : 'automatic', '', t('hud.building.limit.tooltip'))}</span></div>`
      + `<h3 class="sec">${esc(t('hud.building.workerList', 2))}</h3>`
      + workerRow('nyxar', 22, t('task.produce'), 'pickaxe') + workerRow('thazza', 32, t('task.goDeliver'), 'bag')
      + `<div class="win-foot">${btn('trash', t('hud.building.demolish'), {cls: 'danger', act: 'demolish', tip: t('hud.building.demolish.tooltip')})}${btn('more', '', {label: false, cls: 'ghost'})}</div>`;
    return winFrame(w, t(b.nombre), body, {eye: true, camera: true, icon: thumbIcon(b.img), sub: t('hud.build.cat.resources')});
  }

  function houseWin(w) {
    const b = building('core:house');
    const residents = ['alonso', 'francisca', 'nicolas', 'elena', 'teresa'];
    const needs = [['apple', 'need.food', false], ['drop', 'need.water', true], ['shirt', 'need.clothes', false], ['chapel', 'need.religion', true]];
    const body = `<div class="hero short"><img src="img/edificios/house.png" alt=""><span class="hero-chip">${chip('crown', t('hud.house.level', 1, 3), 'accent')}</span></div>`
      + `<div class="kv"><span class="k">${I('users')}${esc(t('mk.residents'))}</span><span class="v avatars">${residents.map(r => avatar(r, 'sm')).join('')}<b>5/5</b></span></div>`
      + `<div class="kv"><span class="k">${I('smile')}${esc(t('hud.happiness', '').replace(/\s*%/, '').trim())}</span><span class="v">${meter(0.41, {cls: 'warn'})}<b>41 %</b></span></div>`
      + `<div class="kv"><span class="k">${I('flower')}${esc(t('mk.bonus'))}</span><span class="v chips"><b class="big">10</b>${chip('paw', '+8', 'ok', t('hud.house.unicorn', 8))}${chip('flower', '+1', 'ok', t('hud.house.flowers', 1))}</span></div>`
      + `<div class="kv"><span class="k">${I('firewood')}${esc(t('mk.firewood'))}</span><span class="v">${meter(1, {cls: 'ok'})}<b>20/20</b></span></div>`
      + `<h3 class="sec">${esc(t('mk.needs'))}</h3><div class="needs">${needs.map(([ic, k, ok]) => `<span class="need ${ok ? 'ok' : 'miss'}"${tip(t(k))}>${I(ic)}${ok ? I('check', 'tick') : ''}</span>`).join('')}</div>`
      + `<h3 class="sec">${esc(t('mk.annexes'))}</h3><div class="annexes">${['annex_clothesline', 'annex_home_shrine', 'annex_rain_barrel'].map(a => `<span class="annex"${tip(t('building.' + a))}><img src="img/edificios/${a}.png" alt=""></span>`).join('')}<span class="annex add">${I('plus')}</span></div>`
      + `<div class="win-foot">${btn('trash', t('hud.building.demolish'), {cls: 'danger', act: 'demolish'})}</div>`;
    return winFrame(w, t(b.nombre), body, {eye: true, camera: true, icon: thumbIcon('img/edificios/house.png')});
  }

  function villagerWin(w) {
    const p = portrait(w.who || 'nyxar');
    const r = race(p.raza);
    const meters = [['apple', 'hud.villager.food', 0.72, 'ok'], ['heart', 'hud.villager.health', 0.9, 'ok'], ['bolt', 'hud.villager.energy', 0.35, 'warn'], ['thermo', 'hud.villager.warmth', 0.8, 'ok']];
    const body = `<div class="person-head"><span class="avatar xl"><img src="${p.img}" alt=""></span><span class="ph-main">`
      + `<span class="ph-line">${esc(t('hud.villager.who', t(p.sexo === 'male' ? 'hud.villager.man' : 'hud.villager.woman'), 22))}</span>`
      + chip('race', t(r.nombre), 'race', t('hud.villager.race', t(r.nombre)))
      + `<span class="ph-task">${dot('ok')}${esc(t('task.produce'))}</span></span></div>`
      + `<div class="links"><button class="link" data-act="open"${tip(t('hud.building.open.tooltip'))}><img src="img/edificios/stonecutter.png" alt="">${I('briefcase')}<span>${esc(t('building.stonecutter'))}</span></button>`
      + `<button class="link" data-act="open"${tip(t('hud.building.open.tooltip'))}><img src="img/edificios/house.png" alt="">${I('home')}<span>${esc(t('building.house'))}</span></button></div>`
      + `<div class="meters">${meters.map(([ic, k, v, c]) => `<span class="m"${tip(t(k) + ': ' + Math.round(v * 100) + ' %')}>${I(ic)}${meter(v, {cls: c})}</span>`).join('')}</div>`
      + `<div class="kv"><span class="k">${I('bag')}${esc(t('hud.villager.carrying', '').replace(/[:\s]+$/, ''))}</span><span class="v">${resIcon('core:stone', 'sm')}<b>4</b></span></div>`
      + `<div class="kv"><span class="k">${I('shirt')}${esc(t('hud.villager.clothes'))}</span><span class="v">${I('check', 'okc')}</span></div>`
      + `<div class="win-foot">${btn('target', t('hud.villager.follow'), {cls: 'primary', act: 'follow', tip: t('hud.villager.follow.tooltip')})}${btn('pencil', t('hud.villager.rename'), {label: false, cls: 'ghost', tip: t('hud.villager.rename.tooltip')})}</div>`;
    return winFrame(w, p.nombre, body, {eye: true, camera: true, icon: `<span class="win-icon round"><img src="${p.img}" alt=""></span>`, sub: t(p.sexo === 'male' ? 'hud.villager.man' : 'hud.villager.woman')});
  }

  function siteWin(w) {
    const b = building('core:chapel');
    const mats = [['core:log', 18, 30], ['core:stone', 12, 30]];
    const body = `<div class="hero short site"><img src="${b.img}" alt=""><span class="ring" style="--p:45"><b>45 %</b></span></div>`
      + `<div class="kv"><span class="k">${I('hammer')}${esc(t('mk.progress'))}</span><span class="v">${meter(0.45, {cls: 'accent'})}<b>45 %</b></span></div>`
      + `<h3 class="sec">${esc(t('mk.materials'))}</h3>`
      + mats.map(([id, have, need]) => `<div class="kv"${tip(t('hud.building.material', t(resource(id).nombre), have, need))}><span class="k">${resIcon(id)}${esc(t(resource(id).nombre))}</span><span class="v">${meter(have / need)}<b>${have}/${need}</b></span></div>`).join('')
      + `<div class="win-foot">${btn('x', t('hud.building.cancel'), {cls: 'danger', act: 'cancel', tip: t('hud.building.cancel.tooltip')})}</div>`;
    return winFrame(w, t(b.nombre), body, {eye: true, icon: thumbIcon(b.img), sub: t('hud.building.construction', 45)});
  }

  function nodeWin(w) {
    const body = `<div class="hero short"><img src="img/cosas/bush_berries.png" alt="">${'<span class="hero-chip">' + chip('berry', t('hud.node.fruit', 6), 'ok') + '</span>'}</div>`
      + `<div class="kv"><span class="k">${I('box')}${esc(t('hud.thing.gives', '').replace(/[:\s]+$/, ''))}</span><span class="v">${resIcon('core:berries', 'sm')}<b>${esc(t('resource.berries'))}</b></span></div>`
      + `<div class="kv"><span class="k">${I('calendar')}${esc(t('mk.season'))}</span><span class="v">${chip('sun', t('hud.season.summer'))}${chip('leaf', t('hud.season.autumn'))}</span></div>`
      + `<p class="note">${esc(t('feature.yield.season', t('resource.berries'), t('hud.season.summer')))}</p>`;
    return winFrame(w, t('feature.berryBush'), body, {eye: true, camera: true, icon: thumbIcon('img/cosas/bush_berries.png'), sub: t('mk.thing')});
  }

  function creatureWin(w) {
    const body = `<div class="hero short danger"><img src="img/cosas/wolf.png" alt=""><span class="hero-chip">${chip('warning', t('hud.creature.state.chase'), 'bad')}</span></div>`
      + `<p class="alert-line">${I('warning')}${esc(t('hud.creature.danger'))}</p>`
      + `<div class="kv"><span class="k">${I('heart')}${esc(t('hud.villager.health'))}</span><span class="v">${meter(0.6, {cls: 'bad'})}<b>30</b></span></div>`
      + `<div class="win-foot">${btn('bell', t('hud.bell.ring'), {cls: 'danger', tip: t('hud.bell.tooltip')})}</div>`;
    return winFrame(w, t('hud.creature.wolf'), body, {eye: true, camera: true, icon: thumbIcon('img/cosas/wolf.png')});
  }

  function goodsWin(w) {
    const groups = [['food', 'hud.goods.food'], ['material', 'hud.goods.material'], ['fuel', 'hud.goods.fuel'], ['good', 'hud.goods.good']];
    const body = `<div class="seg"><button class="seg-b on">${esc(t('mk.all'))}</button>${groups.map(([, k]) => `<button class="seg-b">${esc(t(k))}</button>`).join('')}</div>`
      + groups.map(([cat, k]) => {
        const list = D.recursos.filter(r => r.cat === cat && S.stored[r.id]);
        if (!list.length) return '';
        return `<h3 class="sec">${esc(t(k))}</h3><div class="tiles">` + list.map(r => `<span class="tile"${tip(t(r.nombre) + '\n' + t('hud.goods.value', r.valor))}>${resIcon(r.id, 'lg')}<b>${S.stored[r.id]}</b><span class="tile-name">${esc(t(r.nombre))}</span></span>`).join('') + '</div>';
      }).join('');
    return winFrame(w, t('hud.goods.title'), body, {icon: `<span class="win-icon glyph">${I('box')}</span>`});
  }

  function sparkline(values, cls) {
    const max = Math.max(...values), min = Math.min(...values);
    const pts = values.map((v, i) => `${(i / (values.length - 1) * 100).toFixed(1)},${(28 - (v - min) / Math.max(1, max - min) * 24).toFixed(1)}`).join(' ');
    return `<svg class="spark ${cls || ''}" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline points="${pts}"/></svg>`;
  }

  function statsWin(w) {
    const kpi = (icon, value, label, extra, cls) => `<span class="kpi ${cls || ''}">${I(icon)}<b>${value}</b><span class="kpi-l">${esc(label)}</span>${extra || ''}</span>`;
    const body = `<div class="kpis">`
      + kpi('users', S.population, t('hud.stats.population', S.population, S.adults, S.children).split(':')[0].replace(/\s*\d+$/, ''), sparkline([8, 9, 9, 11, 12, 12, 14, 15, 15, 16, 17, 18]))
      + kpi('smile', S.happiness + ' %', t('hud.happiness', '').replace('%', '').trim(), sparkline([40, 45, 50, 48, 52, 60, 58, 62, 61, 63, 64, 64], 'ok'))
      + kpi('coins', S.gold, t('hud.gold', '').trim(), sparkline([0, 0, 10, 20, 40, 40, 60, 70, 80, 90, 100, 100], 'gold'))
      + kpi('star', 1240, t('hud.stats.score', '').trim())
      + `</div><p class="hint-line">${esc(t('mk.history'))}${newMark()}</p>`
      + `<div class="kv"><span class="k">${I('child')}${esc(t('hud.stats.births', 4, 6).split('·')[0])}</span><span class="v"><b>4</b></span></div>`
      + `<div class="kv"><span class="k">${I('pill')}${esc(t('hud.stats.sick', 1).split(':')[0])}</span><span class="v"><b>1</b></span></div>`
      + `<div class="kv"><span class="k">${I('flame')}${esc(t('hud.stats.burned', 0).split(':')[0])}</span><span class="v"><b>0</b></span></div>`
      + `<div class="kv"><span class="k">${I('crown')}${esc(t('hud.stats.level', 1).replace(/\s*\d+$/, ''))}</span><span class="v"><b>1</b></span></div>`
      + `<div class="kv"><span class="k">${I('race')}${esc(t('hud.stats.races', '').replace(/[:\s]+$/, ''))}</span><span class="v avatars">${['alonso', 'nyxar', 'borin', 'misu'].map(x => avatar(x, 'sm')).join('')}</span></div>`;
    return winFrame(w, t('hud.stats.title'), body, {icon: `<span class="win-icon glyph">${I('chart')}</span>`});
  }

  const LOG = [
    ['heart', 'ok', 'event.born', []], ['scales', 'info', 'event.merchantArrived', []],
    ['paw', 'warn', 'event.fox', [3]], ['sprout', 'info', 'event.unicornSeen', []],
    ['flame', 'bad', 'event.fire', ['@building.house']], ['users', 'ok', 'event.townJoined', ['Ana', 'Nyxar']],
  ];

  const args = a => a.map(x => (typeof x === 'string' && x[0] === '@' ? t(x.slice(1)) : x));

  function logWin(w) {
    const body = '<div class="log">' + LOG.map(([ic, cls, k, a], i) => `<button class="log-row ${cls}"${tip(t('hud.log.goTo'))}><span class="log-ic">${I(ic)}</span><span class="log-main"><span>${esc(t(k, ...args(a)))}</span><span class="log-date">${esc(t('hud.log.row', 2, 3, 14 - i, '').replace(/\s*·\s*$/, ''))}</span></span>${I('map', 'go')}</button>`).join('') + '</div>';
    return winFrame(w, t('hud.log.title'), body, {icon: `<span class="win-icon glyph">${I('list')}</span>`});
  }

  function layersWin(w) {
    const L = [['none', 'map', '#888'], ['fertility', 'sprout', '#6ab04c'], ['beauty', 'flower', '#e07ab0'], ['water', 'drop', '#4aa0e0'],
      ['market', 'stall', '#e0b040'], ['religion', 'chapel', '#b08ae0'], ['health', 'heart', '#e06060'], ['fire', 'flame', '#e0703a'], ['routes', 'route', '#d8c8a0']];
    const body = '<div class="radio-list">' + L.map(([k, ic, c], i) => `<button class="radio${i === 1 ? ' on' : ''}" style="--sw:${c}"${tip(t('hud.layers.' + k + '.tooltip'))}><span class="sw">${I(ic)}</span><span>${esc(t('hud.layers.' + k))}</span></button>`).join('') + '</div>'
      + `<div class="legend"><span>${esc(lang === 'es' ? 'pobre' : 'poor')}</span><span class="grad"></span><span>${esc(lang === 'es' ? 'buena' : 'good')}</span></div>`;
    return winFrame(w, t('hud.layers.title'), body, {icon: `<span class="win-icon glyph">${I('layers')}</span>`});
  }

  function cameraWin(w) {
    const body = `<div class="cam-view" style="background-image:url(fondos/${w.bg || 'pueblo'}.jpg);background-position:${w.pos || '50% 55%'}"><span class="live">${dot('bad')}${esc(t('mk.live'))}</span><span class="cam-tools">${btn('left', '', {label: false, cls: 'ghost'})}${btn('right', '', {label: false, cls: 'ghost'})}</span></div>`;
    return winFrame(w, w.title || 'Nyxar', body, {icon: `<span class="win-icon glyph">${I('camera')}</span>`});
  }

  function armyWin(w) {
    const body = `<div class="kpis two">${'<span class="kpi">' + I('shield') + '<b>4</b><span class="kpi-l">' + esc(lang === 'es' ? 'soldados' : 'soldiers') + '</span></span>'}<span class="kpi">${I('swords')}<b>36</b><span class="kpi-l">${esc(lang === 'es' ? 'poder militar' : 'military power')}</span></span></div>`
      + `<h3 class="sec">${esc(t('mk.order'))}</h3><div class="seg big">${btn('home', t('hud.army.defend'), {cls: 'seg-b on', tip: t('hud.army.defend.tooltip')})}${btn('target', t('hud.army.defendHere'), {cls: 'seg-b', tip: t('hud.army.defendHere.tooltip')})}${btn('exit', t('hud.army.retreat'), {cls: 'seg-b', tip: t('hud.army.retreat.tooltip')})}</div>`
      + `<h3 class="sec">${esc(t('hud.army.scores'))}</h3>`
      + [['Pueblo de Nyxar', 1240, 36, 'playing'], ['Pueblo de Ana', 980, 52, 'playing'], ['Pueblo 3', 410, 0, 'lost']].map(([n, s, p, o]) => `<div class="score-row ${o}"><span>${esc(n)}</span><span>${I('star')}${s}</span><span>${I('swords')}${p}</span><span class="chip ${o === 'lost' ? 'bad' : 'ok'}"><span>${esc(t('hud.outcome.' + o))}</span></span></div>`).join('')
      + `<div class="win-foot">${btn('swords', t('hud.army.attack'), {cls: 'danger', tip: t('hud.army.attack.tooltip')})}</div>`;
    return winFrame(w, t('hud.army.title'), body, {icon: `<span class="win-icon glyph">${I('shield')}</span>`});
  }

  function tradeWin(w) {
    const body = `<div class="seg">${btn('scales', t('hud.trade.new'), {cls: 'seg-b on'})}${btn('list', t('hud.trade.offers'), {cls: 'seg-b'})}${btn('cart', t('hud.trade.caravans'), {cls: 'seg-b'})}</div>`
      + `<div class="trade"><span class="tr-col"><span class="k">${esc(t('hud.trade.give'))}</span><span class="tr-pick">${resIcon('core:stone', 'lg')}<b>20</b></span></span>${I('right', 'tr-arrow')}<span class="tr-col"><span class="k">${esc(t('hud.trade.want'))}</span><span class="tr-pick">${resIcon('core:wheat', 'lg')}<b>15</b></span></span></div>`
      + `<div class="kv"><span class="k">${I('home')}${esc(t('hud.trade.to'))}</span><span class="v">${chip('', 'Pueblo de Ana')}</span></div>`
      + `<h3 class="sec">${esc(t('hud.trade.caravans'))}</h3><div class="kv"><span class="k">${I('cart')}${resIcon('core:fish', 'sm')}12 · Ana</span><span class="v">${meter(0.6)}<b>${esc(t('mk.days', 2))}</b></span></div>`
      + `<div class="win-foot">${btn('check', t('hud.trade.send'), {cls: 'primary', tip: t('hud.trade.send.tooltip')})}</div>`;
    return winFrame(w, t('hud.trade.title'), body, {icon: `<span class="win-icon glyph">${I('scales')}</span>`});
  }

  const WINDOWS = {stonecutter: stonecutterWin, house: houseWin, villager: villagerWin, site: siteWin, node: nodeWin,
    creature: creatureWin, goods: goodsWin, stats: statsWin, log: logWin, layers: layersWin, camera: cameraWin,
    army: armyWin, trade: tradeWin};

  // --- Notices, question, hint, menu ---------------------------------------------------------------

  const TOASTS = [
    ['scales', 'info', 'event.merchantArrived', []], ['heart', 'ok', 'event.born', []],
    ['paw', 'warn', 'event.fox', [3]], ['swords', 'bad', 'event.raid', [3]], ['sprout', 'info', 'event.unicornSeen', []],
    ['bell', 'warn', 'event.bark.wolf', []], ['cart', 'info', 'event.caravanArrived', ['Ana']],
  ];

  function toast(i, count) {
    const [ic, cls, k, a] = TOASTS[i % TOASTS.length];
    return `<button class="toast ${cls}"${tip(t('hud.log.goTo'))}><span class="toast-ic">${I(ic)}</span><span class="toast-txt">${esc(t(k, ...a))}${count > 1 ? ` <b>×${count}</b>` : ''}</span></button>`;
  }

  function question() {
    return `<div class="question"><img class="q-img" src="img/cosas/sheep.png" alt="" hidden><span class="q-ic">${I('warning')}</span><div class="q-main"><b>${esc(t('hud.ask.turtles', 5))}</b><span class="dim">${esc(t('hud.ask.days', 3))}</span>`
      + `<div class="q-btns">${btn('shield', t('hud.ask.turtles.keep'), {cls: 'primary', tip: t('hud.ask.turtles.keep.tooltip', 30)})}${btn('egg', t('hud.ask.turtles.take'), {tip: t('hud.ask.turtles.take.tooltip', 40)})}${btn('eye', t('hud.ask.see'), {cls: 'ghost'})}</div></div></div>`;
  }

  function hint() {
    const txt = t('hud.place.hint', 'R');
    return `<div class="place-hint">${I('info')}<span>${esc(txt).replace(/\bR\b/, '<kbd>R</kbd>').replace(/(Mayús|Shift)/, '<kbd>$1</kbd>').replace(/(Esc)\b/, '<kbd>$1</kbd>')}</span></div>`;
  }

  function gameMenu() {
    const items = [['play', 'gameMenu.resume'], ['save', 'gameMenu.save'], ['users', 'gameMenu.open'], ['lock', 'gameMenu.access'], ['eye', 'gameMenu.watch'], ['exit', 'gameMenu.leave'], ['x', 'gameMenu.quit']];
    return `<div class="modal-veil"></div><div class="modal"><h2>${esc(t('gameMenu.title'))}</h2>`
      + items.map(([ic, k], i) => btn(ic, t(k), {cls: 'menu-item' + (i === 0 ? ' primary' : '') + (i === items.length - 1 ? ' danger' : ''), tip: D.textos[lang][k + '.tooltip'] ? t(k + '.tooltip') : ''})).join('')
      + `</div>`;
  }

  function dialog() {
    return `<div class="modal dialog"><span class="dlg-ic">${I('info')}</span><h2>${esc(t('dialog.keepDisplay.title'))}</h2><p>${esc(t('dialog.keepDisplay.body', 12))}</p>`
      + `<div class="dlg-btns">${btn('', t('dialog.keepDisplay.revert'), {cls: 'ghost'})}${btn('check', t('dialog.keepDisplay.keep'), {cls: 'primary'})}</div></div>`;
  }

  // --- Scenes -----------------------------------------------------------------------------------------

  const ESCENAS = {
    ventanas: {
      nombre: 'Ventanas de selección',
      windows: [
        {id: 'w1', kind: 'stonecutter', x: 196, y: 330, w: 360, z: 3, pinned: true},
        {id: 'w2', kind: 'villager', x: 576, y: 84, w: 370, z: 4},
        {id: 'w3', kind: 'camera', x: 196, y: 84, w: 360, h: 226, z: 2, title: 'Nyxar', bg: 'pueblo', pos: '47% 42%'},
        {id: 'w4', kind: 'house', x: 1286, y: 330, w: 370, z: 5},
      ],
      toasts: [0, 1], open: [],
    },
    pueblo: {
      nombre: 'Panel del pueblo',
      windows: [
        {id: 'w1', kind: 'goods', x: 196, y: 72, w: 380, z: 2},
        {id: 'w2', kind: 'stats', x: 594, y: 72, w: 380, z: 3},
        {id: 'w3', kind: 'log', x: 992, y: 84, w: 380, z: 4, tabs: [t('hud.log.title'), t('hud.layers.title')]},
        {id: 'w4', kind: 'node', x: 1330, y: 330, w: 340, z: 5},
      ],
      toasts: [2], open: ['goods', 'stats', 'log'],
    },
    construir: {
      nombre: 'Construir y avisos',
      windows: [
        {id: 'w1', kind: 'site', x: 196, y: 260, w: 360, z: 2},
        {id: 'w2', kind: 'creature', x: 1310, y: 330, w: 350, z: 3, min: false},
      ],
      toasts: [3, 4, 5], open: [], question: true, hint: true,
    },
    defensa: {
      nombre: 'Comercio y ejército',
      windows: [
        {id: 'w1', kind: 'army', x: 196, y: 72, w: 460, z: 2},
        {id: 'w2', kind: 'trade', x: 680, y: 72, w: 440, z: 3},
        {id: 'w3', kind: 'layers', x: 1380, y: 330, w: 280, z: 4},
      ],
      toasts: [6], open: ['army', 'trade', 'layers'],
    },
    menu: {nombre: 'Menú y diálogo', windows: [{id: 'w1', kind: 'villager', x: 196, y: 72, w: 350, z: 2, who: 'borin', min: true}], toasts: [], open: [], menu: true},
  };

  // --- Mounting and interaction ---------------------------------------------------------------------

  let stage = null, layout = {}, scene = 'ventanas', windows = [], toastList = [], zTop = 10, toastTimer = 0;

  function render() {
    const sc = ESCENAS[scene];
    const open = new Set(sc.open);
    stage.className = 'stage ' + Object.entries(layout).map(([k, v]) => `${k}-${v}`).join(' ');
    stage.innerHTML = '<div class="hud">' + topBar() + dock(open) + minimap()
      + '<div class="wins">' + windows.map(w => WINDOWS[w.kind](w)).join('') + '</div>'
      + (sc.question ? question() : '') + (sc.hint ? hint() : '')
      + `<div class="toasts">${toastList.map(([i, n]) => toast(i, n)).join('')}</div>`
      + buildBar(layout)
      + (sc.menu ? gameMenu() + dialog() : '')
      + '<div class="tooltip" hidden></div></div>';
  }

  function setScene(id) {
    scene = ESCENAS[id] ? id : 'ventanas';
    windows = ESCENAS[scene].windows.map(w => Object.assign({}, w));
    toastList = ESCENAS[scene].toasts.map(i => [i, 1]);
    S.startOpen = scene === 'construir';
    S.catOpen = scene === 'construir';
    render();
  }

  let tipTimer = 0, tipFor = null;
  function showTip(target, x, y) {
    const tipEl = stage.querySelector('.tooltip');
    if (!tipEl) return;
    tipEl.textContent = target.getAttribute('data-tip');
    tipEl.hidden = false;
    const r = stage.getBoundingClientRect();
    const k = r.width / stage.offsetWidth;
    let lx = (x - r.left) / k + 14, ly = (y - r.top) / k + 18;
    const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    if (lx + w > stage.offsetWidth - 8) lx = stage.offsetWidth - 8 - w;
    if (ly + h > stage.offsetHeight - 8) ly = (y - r.top) / k - h - 10;
    tipEl.style.left = lx + 'px';
    tipEl.style.top = ly + 'px';
  }

  function hideTip() {
    clearTimeout(tipTimer);
    tipFor = null;
    const tipEl = stage && stage.querySelector('.tooltip');
    if (tipEl) tipEl.hidden = true;
  }

  function winOf(el) {
    const sec = el.closest('.win');
    return sec ? windows.find(w => w.id === sec.dataset.id) : null;
  }

  function onClick(e) {
    const b = e.target.closest('[data-act]');
    if (!b) return;
    const act = b.dataset.act;
    const w = winOf(b);
    hideTip();
    if (act === 'pin' && w) { w.pinned = !w.pinned; render(); }
    else if (act === 'min' && w) { w.min = !w.min; render(); }
    else if (act === 'close' && w) { windows = windows.filter(x => x !== w); render(); }
    else if (act === 'pause') { S.paused = !S.paused; render(); }
    else if (act === 'slower') { S.speed = Math.max(1, S.speed - 1); render(); }
    else if (act === 'faster') { S.speed = Math.min(3, S.speed + 1); render(); }
    else if (act === 'start') { S.startOpen = !S.startOpen; render(); }
    else if (act === 'cat') {
      const c = +b.dataset.cat;
      S.catOpen = !(S.catOpen && S.category === c);
      S.category = c;
      render();
    }
    else if (act === 'fewer') { S.workers = Math.max(0, S.workers - 1); render(); }
    else if (act === 'more') { S.workers = Math.min(2, S.workers + 1); render(); }
    else if (act === 'switch') { b.classList.toggle('on'); }
    else if (act === 'tab') { b.parentElement.querySelectorAll('.win-tab').forEach(x => x.classList.toggle('on', x === b)); }
    else if (act === 'scroll') { const row = b.parentElement.querySelector('.bb-items'); row.scrollBy({left: +b.dataset.dir * 400, behavior: 'smooth'}); }
    else if (act === 'dock') {
      const kind = b.dataset.win;
      const existing = windows.find(x => x.kind === kind);
      if (existing) windows = windows.filter(x => x !== existing);
      else if (WINDOWS[kind]) windows.push({id: 'd' + kind, kind, x: 196 + windows.length * 30, y: 72 + windows.length * 30, w: 360, z: ++zTop});
      const sc = ESCENAS[scene];
      sc.open = windows.map(x => x.kind);
      render();
    }
  }

  let drag = null;
  function onDown(e) {
    const sec = e.target.closest('.win');
    if (!sec) return;
    const w = windows.find(x => x.id === sec.dataset.id);
    if (!w) return;
    if (w.z !== zTop) { w.z = ++zTop; sec.style.zIndex = w.z; }
    const k = stage.getBoundingClientRect().width / stage.offsetWidth;
    if (e.target.closest('.win-grip')) {
      drag = {w, sec, resize: true, sx: e.clientX, sy: e.clientY, ow: sec.offsetWidth, oh: sec.offsetHeight, k};
    } else if (e.target.closest('.win-bar') && !e.target.closest('button')) {
      drag = {w, sec, sx: e.clientX, sy: e.clientY, ox: w.x, oy: w.y, k};
    } else return;
    e.preventDefault();
  }
  function onMove(e) {
    if (drag) {
      const dx = (e.clientX - drag.sx) / drag.k, dy = (e.clientY - drag.sy) / drag.k;
      if (drag.resize) {
        drag.w.w = Math.max(240, drag.ow + dx);
        drag.w.h = Math.max(120, drag.oh + dy);
        drag.sec.style.width = drag.w.w + 'px';
        drag.sec.style.height = drag.w.h + 'px';
      } else {
        drag.w.x = Math.round(drag.ox + dx);
        drag.w.y = Math.round(Math.max(48, drag.oy + dy));
        drag.sec.style.left = drag.w.x + 'px';
        drag.sec.style.top = drag.w.y + 'px';
      }
      return;
    }
    const target = e.target.closest && e.target.closest('[data-tip]');
    if (target !== tipFor) {
      hideTip();
      tipFor = target;
      if (target && target.getAttribute('data-tip')) tipTimer = setTimeout(() => showTip(target, e.clientX, e.clientY), 380);
    }
  }
  function onUp() { drag = null; }

  function cycleToasts() {
    clearInterval(toastTimer);
    toastTimer = setInterval(() => {
      if (!stage || document.hidden) return;
      const next = (toastList.length ? toastList[toastList.length - 1][0] + 1 : 0) % TOASTS.length;
      toastList.push([next, 1]);
      if (toastList.length > 4) toastList.shift();
      const box = stage.querySelector('.toasts');
      if (box) {
        box.innerHTML = toastList.map(([i, n]) => toast(i, n)).join('');
        const last = box.lastElementChild;
        if (last) last.classList.add('enter');
      }
    }, 7000);
  }

  window.Kit = {
    t, ESCENAS,
    setLang(l) { lang = l === 'en' ? 'en' : 'es'; },
    get lang() { return lang; },
    mount(el, opts) {
      if (!stage) {
        el.addEventListener('click', onClick);
        el.addEventListener('mousedown', onDown);
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        el.addEventListener('mouseleave', hideTip);
      }
      stage = el;
      layout = Object.assign({top: 'bar', dock: 'list', build: 'tabs', minimap: 'square', chrome: 'right', toasts: 'stack', labels: 'icons', res: 'glyph', windows: 'float'}, opts.layout || {}, opts.override || {});
      if (opts.lang) this.setLang(opts.lang);
      setScene(opts.escena || scene);
      cycleToasts();
    },
    setScene,
  };
})();
