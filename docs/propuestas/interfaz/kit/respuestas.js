// Salvador's answers about the mockups: always in this browser
// (localStorage) and, once he opens it, in docs/propuestas/interfaz/
// respuestas.json through the File System Access API (written to a temporary
// copy and swapped in on close). tools/propuestas/interfaz.py respuestas
// prints them.
(function () {
  'use strict';
  const LS_KEY = 'interfaz.respuestas';
  const VOTES = ['si', 'talvez', 'no'];
  let doc = {version: 1, temas: {}, iconos: {}, general: ''};
  let handle = null, timer = 0, saving = false, again = false, error = '';
  const listeners = [];

  function cleanEntry(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    const out = {};
    if (VOTES.includes(raw.voto)) out.voto = raw.voto;
    if (Array.isArray(raw.partes)) {
      const parts = raw.partes.filter(p => typeof p === 'string' && p.length < 60).slice(0, 30);
      if (parts.length) out.partes = parts;
    }
    if (typeof raw.nota === 'string' && raw.nota.trim()) out.nota = raw.nota.slice(0, 20000);
    if (typeof raw.fecha === 'string') out.fecha = raw.fecha.slice(0, 40);
    return Object.keys(out).some(k => k !== 'fecha') ? out : null;
  }

  // Only this page's own format: an object with nothing but these keys. Any
  // other JSON (the review log, the models' answers) is refused untouched.
  const KEYS = ['version', 'temas', 'iconos', 'general'];
  function clean(raw) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
    if (Object.keys(raw).some(k => !KEYS.includes(k)) || raw.version !== 1) return null;
    const out = {version: 1, temas: {}, iconos: {}, general: ''};
    for (const group of ['temas', 'iconos']) {
      const src = raw[group];
      if (!src || typeof src !== 'object' || Array.isArray(src)) continue;
      for (const [k, v] of Object.entries(src)) {
        if (!/^[a-z0-9-]{1,40}$/.test(k)) continue;
        const e = cleanEntry(v);
        if (e) out[group][k] = e;
      }
    }
    if (typeof raw.general === 'string') out.general = raw.general.slice(0, 20000);
    return out;
  }

  try { doc = clean(JSON.parse(localStorage.getItem(LS_KEY) || 'null')) || doc; } catch (e) { /* Starts empty. */ }

  function emit() { listeners.forEach(f => f()); }

  function persist() {
    try { localStorage.setItem(LS_KEY, JSON.stringify(doc)); } catch (e) { /* Kept in memory. */ }
    clearTimeout(timer);
    timer = setTimeout(write, 350);
    emit();
  }

  async function write() {
    if (!handle) return;
    if (saving) { again = true; return; }
    saving = true;
    emit();
    try {
      const w = await handle.createWritable();
      await w.write(JSON.stringify(doc, null, 1) + '\n');
      await w.close();
      error = '';
    } catch (e) {
      error = e && e.message ? e.message : String(e);
    }
    saving = false;
    if (again) { again = false; write(); }
    emit();
  }

  function idb() {
    return new Promise((resolve, reject) => {
      const r = indexedDB.open('interfaz-propuestas', 1);
      r.onupgradeneeded = () => r.result.createObjectStore('kv');
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
  }
  async function idbGet(key) {
    try {
      const db = await idb();
      return await new Promise(resolve => {
        const r = db.transaction('kv').objectStore('kv').get(key);
        r.onsuccess = () => resolve(r.result); r.onerror = () => resolve(undefined);
      });
    } catch (e) { return undefined; }
  }
  async function idbSet(key, value) {
    try { const db = await idb(); db.transaction('kv', 'readwrite').objectStore('kv').put(value, key); } catch (e) { /* Not kept. */ }
  }

  async function useHandle(h) {
    const body = (await (await h.getFile()).text()).trim();
    if (h.name !== 'respuestas.json') throw new Error('elige el archivo respuestas.json de docs/propuestas/interfaz; no se cambió nada');
    let fromFile = {version: 1, temas: {}, iconos: {}, general: ''};
    if (body) {
      try { fromFile = clean(JSON.parse(body)); } catch (e) { fromFile = null; }
      if (!fromFile) throw new Error('ese archivo no es un respuestas.json de la interfaz; no se cambió');
    }
    for (const group of ['temas', 'iconos']) {
      for (const [k, theirs] of Object.entries(fromFile[group])) {
        const mine = doc[group][k];
        if (!mine || String(theirs.fecha || '') > String(mine.fecha || '')) doc[group][k] = theirs;
      }
    }
    if (!doc.general && fromFile.general) doc.general = fromFile.general;
    handle = h;
    error = '';
    persist();
  }

  window.Respuestas = {
    VOTES,
    get: (group, key) => (doc[group] && doc[group][key]) || {},
    set(group, key, patch) {
      const next = cleanEntry(Object.assign({}, this.get(group, key), patch, {fecha: new Date().toISOString()}));
      if (next) doc[group][key] = next; else delete doc[group][key];
      persist();
    },
    get general() { return doc.general; },
    setGeneral(text) { doc.general = String(text).slice(0, 20000); persist(); },
    onChange(f) { listeners.push(f); },
    status() {
      if (error) return ['bad', 'No se pudo guardar en el archivo (' + error + '). Tus respuestas siguen en este navegador.'];
      if (handle && saving) return ['', 'Guardando…'];
      if (handle) return ['ok', 'Guardado en respuestas.json'];
      if (!('showOpenFilePicker' in window)) return ['warn', 'Este navegador no puede escribir el archivo: usa Descargar.'];
      const n = Object.keys(doc.temas).length + Object.keys(doc.iconos).length;
      return [n ? 'warn' : '', n ? 'Guardado solo en este navegador: abre respuestas.json para guardarlo en el archivo.' : 'Abre respuestas.json para guardar tus respuestas.'];
    },
    get connected() { return !!handle; },
    canConnect: 'showOpenFilePicker' in window,
    async connect() {
      try {
        let h = await idbGet('respuestas-interfaz');
        if (h && (await h.requestPermission({mode: 'readwrite'})) !== 'granted') h = null;
        if (!h) [h] = await window.showOpenFilePicker({types: [{description: 'respuestas.json', accept: {'application/json': ['.json']}}]});
        if ((await h.requestPermission({mode: 'readwrite'})) !== 'granted') throw new Error('sin permiso de escritura');
        await useHandle(h);
        idbSet('respuestas-interfaz', h);
      } catch (e) {
        if (e && e.name === 'AbortError') return;
        error = e && e.message ? e.message : String(e);
        emit();
      }
    },
    download() {
      const url = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 1) + '\n'], {type: 'application/json'}));
      const a = document.createElement('a');
      a.href = url; a.download = 'respuestas.json'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    },
  };

  (async () => {  // Reconnects without a click while the browser still grants the permission.
    if (!('showOpenFilePicker' in window)) return;
    const h = await idbGet('respuestas-interfaz');
    if (!h) return;
    try {
      if ((await h.queryPermission({mode: 'readwrite'})) === 'granted') await useHandle(h);
    } catch (e) { /* The button stays. */ }
    emit();
  })();
})();
