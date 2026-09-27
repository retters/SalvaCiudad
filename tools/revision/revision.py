"""The review log (docs/revision): what was built, decisions, questions for
Salvador, suggestions and open work, each with a state he sets in
docs/revision/index.html.

    python tools/revision/revision.py sincronizar
        Rebuilds the decisions (docs/DECISIONES.md) and the manual checks
        (README.md) into revision.json, keeping every state, note and history.
    python tools/revision/revision.py agregar <archivo.json>
        Adds or updates hand-written items (changes, questions, suggestions,
        open work) from a JSON list; states and notes already set are kept.
    python tools/revision/revision.py pendientes
        Lists what waits for Claude: authorized, to change, failing, or with a
        note from Salvador newer than Claude's last answer.
    python tools/revision/revision.py responder <id> <estado|-> <texto>
        Claude's answer on an item (and its new state, or - to keep it).

Standard library only. The file is written atomically (temporary file, then
replace) and read with strict checks.
"""

import datetime
import hashlib
import json
import os
import re
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA = os.path.join(ROOT, 'docs', 'revision', 'revision.json')
SCHEMA = 1
MAX_BYTES = 32 * 1024 * 1024

# The states of each kind of item; the first is where an item starts.
STATES = {
    'cambio': ['sin revisar', 'revisado', 'aprobado', 'con problemas'],
    'prueba': ['sin probar', 'funciona', 'falla', 'no aplica'],
    'decision': ['sin revisar', 'aprobada', 'requiere cambio', 'requiere definición', 'descartada'],
    'confirmar': ['pendiente', 'confirmado', 'rechazado', 'requiere definición'],
    'sugerencia': ['sin revisar', 'autorizada', 'requiere definición', 'pospuesta', 'descartada', 'en curso',
                   'implementada'],
    'pendiente': ['abierto', 'autorizado', 'requiere definición', 'pospuesto', 'descartado', 'en curso', 'hecho'],
}
# States that ask Claude to act.
FOR_CLAUDE = {'con problemas', 'falla', 'requiere cambio', 'confirmado', 'rechazado', 'autorizada', 'autorizado',
              'requiere definición'}
FIELDS_USER = ('estado', 'nota', 'historial', 'actualizado')


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def empty():
    return {'schemaVersion': SCHEMA, 'estados': STATES, 'items': []}


def load():
    if not os.path.exists(DATA):
        return empty()
    if os.path.getsize(DATA) > MAX_BYTES:
        sys.exit('revision.json is too large')
    with open(DATA, encoding='utf-8') as f:
        doc = json.load(f)
    if not isinstance(doc, dict) or doc.get('schemaVersion') != SCHEMA or not isinstance(doc.get('items'), list):
        sys.exit('revision.json: unknown format (schemaVersion %r)' % doc.get('schemaVersion'))
    good = []
    for it in doc['items']:
        if (isinstance(it, dict) and isinstance(it.get('id'), str) and it.get('tipo') in STATES
                and isinstance(it.get('titulo'), str) and it.get('estado') in STATES[it['tipo']]):
            it.setdefault('nota', '')
            it.setdefault('respuesta', '')
            it.setdefault('historial', [])
            good.append(it)
        else:
            print('ignored a damaged item:', str(it)[:80])
    doc['items'] = good
    doc['estados'] = STATES
    return doc


def save(doc):
    doc['generado'] = now()
    text = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
    json.loads(text)  # Verified before it replaces anything.
    folder = os.path.dirname(DATA)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.revision-', suffix='.json', dir=folder)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA)


def group_of(heading):
    """'Fase 6b: biomas... (2026-09-27)' -> ('6b', 'Fase 6b: biomas...')."""
    label = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\)\s*$', '', heading).strip()
    m = re.match(r'Fase (\d+[a-z]?)\b', label)
    return (m.group(1) if m else label), label


def short_hash(text):
    return hashlib.sha1(re.sub(r'\s+', ' ', text).strip().encode('utf-8')).hexdigest()[:8]


def parse_decisions():
    items = []
    text = open(os.path.join(ROOT, 'docs', 'DECISIONES.md'), encoding='utf-8').read()
    fase, grupo = '0', ''
    current = None
    for line in text.splitlines():
        h = re.match(r'^## (.+)$', line)
        d = re.match(r'^\*\*(D-\d+[a-z]?)\.\s*(.+?)\*\*\s*(.*)$', line)
        if h:
            fase, grupo = group_of(h.group(1))
            current = None
        elif d:
            current = {'id': d.group(1), 'tipo': 'decision', 'fase': fase, 'grupo': grupo,
                       'titulo': d.group(2).rstrip('.'), 'detalle': d.group(3), 'fuente': 'docs/DECISIONES.md'}
            items.append(current)
        elif current is not None and not line.startswith('---'):
            current['detalle'] += '\n' + line
    for it in items:
        it['detalle'] = it['detalle'].strip()
    return items


def parse_checks():
    items = []
    text = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read()
    inside = False
    fase, grupo = '', ''
    for line in text.splitlines():
        if line.startswith('## '):
            inside = line.startswith('## Lista de verificación')
            continue
        if not inside:
            continue
        h = re.match(r'^### (.+)$', line)
        c = re.match(r'^- \[[ xX]\] (.+)$', line)
        if h:
            fase, grupo = group_of(h.group(1))
            if not re.match(r'\d', fase):
                fase = grupo
        elif c:
            body = c.group(1).strip()
            items.append({'id': 'prueba-%s-%s' % (re.sub(r'\W+', '', fase.lower())[:12], short_hash(body)),
                          'tipo': 'prueba', 'fase': fase, 'grupo': grupo, 'titulo': body, 'detalle': '',
                          'fuente': 'README.md'})
    return items


def merge(doc, fresh, origin):
    """New content from the docs, the old states and notes kept. Items of this
    origin gone from the docs are dropped unless Salvador touched them."""
    old = {it['id']: it for it in doc['items']}
    seen = set()
    out = [it for it in doc['items'] if it.get('origen') != origin]
    order = {it['id']: i for i, it in enumerate(doc['items'])}
    for f in fresh:
        seen.add(f['id'])
        f['origen'] = origin
        prev = old.get(f['id'])
        if prev:
            for k in FIELDS_USER + ('respuesta',):
                if k in prev:
                    f[k] = prev[k]
            f.pop('retirado', None)
        else:
            f['estado'] = STATES[f['tipo']][0]
            f['nota'] = ''
            f['respuesta'] = ''
            f['historial'] = []
        out.append(f)
    for it in doc['items']:
        if it.get('origen') == origin and it['id'] not in seen:
            touched = it['estado'] != STATES[it['tipo']][0] or it.get('nota') or it.get('historial')
            if touched:
                it['retirado'] = True
                out.append(it)
    # Keep the file's order stable: known items where they were, new ones after.
    out.sort(key=lambda it: order.get(it['id'], len(order)))
    doc['items'] = out


def cmd_sync():
    doc = load()
    merge(doc, parse_decisions(), 'DECISIONES')
    merge(doc, parse_checks(), 'README')
    save(doc)
    count = {}
    for it in doc['items']:
        count[it['tipo']] = count.get(it['tipo'], 0) + 1
    print('revision.json:', ', '.join('%s %d' % kv for kv in sorted(count.items())))


def cmd_add(path):
    with open(path, encoding='utf-8') as f:
        new = json.load(f)
    doc = load()
    by_id = {it['id']: it for it in doc['items']}
    for n in new:
        if n.get('tipo') not in STATES or not n.get('id') or not n.get('titulo'):
            sys.exit('bad item: %r' % n)
        prev = by_id.get(n['id'])
        n.setdefault('detalle', '')
        n.setdefault('fase', '')
        n.setdefault('grupo', '')
        n['origen'] = 'curado'
        if prev:
            for k in FIELDS_USER + ('respuesta',):
                if k in prev:
                    n[k] = prev[k]
            prev.clear()
            prev.update(n)
        else:
            n.setdefault('estado', STATES[n['tipo']][0])
            n.setdefault('nota', '')
            n.setdefault('respuesta', '')
            n.setdefault('historial', [])
            doc['items'].append(n)
            by_id[n['id']] = n
    save(doc)
    print('added or updated', len(new), 'items')


def waiting(it):
    """Salvador wrote after Claude's last word, or set a state that asks for work."""
    last_user = last_claude = ''
    for h in it.get('historial', []):
        if h.get('quien') == 'Claude':
            last_claude = h.get('fecha', '')
        else:
            last_user = h.get('fecha', '')
    return last_user > last_claude and (it['estado'] in FOR_CLAUDE or it.get('nota'))


def cmd_pending():
    doc = load()
    todo = [it for it in doc['items'] if waiting(it)]
    if not todo:
        print('Nothing waits for Claude.')
    for it in todo:
        print('- %s [%s] %s — %s' % (it['id'], it['estado'], it['titulo'][:90], (it.get('nota') or '').replace('\n', ' ')[:300]))


def cmd_answer(item_id, state, text):
    doc = load()
    for it in doc['items']:
        if it['id'] == item_id:
            if state != '-':
                if state not in STATES[it['tipo']]:
                    sys.exit('state %r is not one of %s' % (state, STATES[it['tipo']]))
                it['estado'] = state
            it['respuesta'] = text
            it['actualizado'] = now()
            it.setdefault('historial', []).append({'fecha': it['actualizado'], 'quien': 'Claude',
                                                   'estado': it['estado'], 'texto': text})
            save(doc)
            print('answered', item_id)
            return
    sys.exit('no item ' + item_id)


def main():
    args = sys.argv[1:]
    if args[:1] == ['sincronizar']:
        cmd_sync()
    elif args[:1] == ['agregar'] and len(args) == 2:
        cmd_add(args[1])
    elif args[:1] == ['pendientes']:
        cmd_pending()
    elif args[:1] == ['responder'] and len(args) == 4:
        cmd_answer(args[1], args[2], args[3])
    else:
        print(__doc__)
        sys.exit(2)


main()
