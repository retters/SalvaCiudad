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
        note from Salvador newer than Claude's last answer. First turns every
        manual check marked failing into an authorized correction.
    python tools/revision/revision.py responder <id> <estado|-> <texto>
        Claude's answer on an item (and its new state, or - to keep it).
    python tools/revision/revision.py compactar
        Turns history written by the first version of the page (one entry per
        pause while typing a note) into one entry per state change and one
        for the note as it was finally left.
    python tools/revision/revision.py ideas
        Everything in the ideas cycle that is not archived: each idea with its
        original text, state, analysis and note; each analysis question with
        the options Salvador chose.
    python tools/revision/revision.py archivar
        Closes a refinement round: archives the ideas already planned or
        discarded, the questions already answered and the corrections
        verified or discarded. Ideas kept for later stay visible.

Ideas ("idea") and corrections ("correccion") keep Salvador's text as he
wrote it: "agregar" numbers new ones (I-001..., C-001...) and never changes
the text of one already there. Authorized corrections show in "pendientes".
Analysis questions ("pregunta") carry "opciones" (a list of {"etiqueta",
"descripcion", "recomendada"}) and "multiple"; Salvador's choice is kept in
"eleccion". A confirmation ("confirmar") may carry options too, one of them
marked "actual": what Claude did; choosing it confirms, any other rejects.
Claude's own suggestions and open work are ideas with "autor": "Claude".

History entries have an "accion": "estado" (a state chosen), "nota" (a note
saved with its button), "eleccion" (options chosen in a question) or
"respuesta" (Claude's answer).

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
    'idea': ['nueva', 'analizada', 'para el plan', 'ajustar', 'para después', 'descartada', 'planeada'],
    'pregunta': ['sin responder', 'respondida', 'requiere definición'],
    'correccion': ['nueva', 'autorizada', 'en curso', 'corregida', 'no se reproduce', 'verificada', 'descartada'],
}
# Written by Salvador (in the chat or on the page), numbered with a prefix.
CAPTURED = {'idea': 'I', 'correccion': 'C'}
# States that ask Claude to act.
FOR_CLAUDE = {'con problemas', 'falla', 'requiere cambio', 'confirmado', 'rechazado', 'autorizada', 'autorizado',
              'requiere definición', 'para el plan', 'ajustar', 'respondida'}
FIELDS_USER = ('estado', 'nota', 'eleccion', 'historial', 'actualizado')
# Links between items, kept when "sincronizar" rebuilds an item from the docs.
LINKS = ('correccion', 'ideaCreada')
# What Claude may never rewrite in an idea or a correction: Salvador's own words.
IDEA_FIXED = ('detalle', 'area', 'capturada')
AREAS = ['Juego', 'Interfaz', 'Red', 'Arte', 'Rendimiento', 'Mods', 'Herramientas', 'Otro']
MAX_TEXT = 20000


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
                and isinstance(it.get('titulo'), str) and it.get('estado') in STATES[it['tipo']]
                and (not has_options(it) or valid_options(it.get('opciones')))):
            it.setdefault('nota', '')
            it.setdefault('respuesta', '')
            it.setdefault('historial', [])
            if has_options(it):
                clean_choice(it)
            good.append(it)
        else:
            print('ignored a damaged item:', str(it)[:80])
    doc['items'] = good
    doc['estados'] = STATES
    return doc


def has_options(it):
    """Questions always offer options; a confirmation may (D-9013)."""
    return it['tipo'] == 'pregunta' or 'opciones' in it


def valid_options(opts):
    """At least two options, each with its own label. "actual" marks, in a
    confirmation, what Claude already did."""
    if not isinstance(opts, list) or len(opts) < 2:
        return False
    labels = [o.get('etiqueta') if isinstance(o, dict) else None for o in opts]
    return (all(isinstance(x, str) and x.strip() for x in labels) and len(set(labels)) == len(labels)
            and all(isinstance(o.get('descripcion', ''), str) and isinstance(o.get('recomendada', False), bool)
                    and isinstance(o.get('actual', False), bool) for o in opts))


def clean_choice(it):
    """Only labels the question offers, and one of them unless it is multiple."""
    it['multiple'] = it.get('multiple') is True
    labels = [o['etiqueta'] for o in it['opciones']]
    chosen = it.get('eleccion')
    if not isinstance(chosen, list):
        chosen = []
    kept = [x for x in labels if x in chosen]
    if not it['multiple']:
        kept = kept[:1]
    if len(kept) != len(chosen):
        print('ignored a damaged choice in', it['id'])
    it['eleccion'] = kept


def next_idea_id(items, tipo='idea'):
    prefix = CAPTURED[tipo]
    top = 0
    for it in items:
        m = re.match(r'^%s-(\d+)$' % prefix, it['id'])
        if m:
            top = max(top, int(m.group(1)))
    return '%s-%03d' % (prefix, top + 1)


def idea_title(text):
    line = text.strip().splitlines()[0].strip() if text.strip() else ''
    return line if len(line) <= 90 else line[:87].rstrip() + '…'


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
            for k in FIELDS_USER + ('respuesta',) + LINKS:
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


def check_new(n, prev):
    """Strict checks on an item Claude adds; exits on the first problem."""
    if not isinstance(n, dict) or n.get('tipo') not in STATES:
        sys.exit('bad item: %r' % n)
    for k, v in n.items():
        if isinstance(v, str) and len(v) > MAX_TEXT:
            sys.exit('%s: field %s is too long' % (n.get('id', 'new idea'), k))
    if 'estado' in n and n['estado'] not in STATES[n['tipo']]:
        sys.exit('%s: state %r is not one of %s' % (n.get('id'), n['estado'], STATES[n['tipo']]))
    if prev and prev['tipo'] != n['tipo']:
        sys.exit('%s is a %s, not a %s' % (n['id'], prev['tipo'], n['tipo']))
    if n['tipo'] in CAPTURED and not prev:
        if not isinstance(n.get('detalle'), str) or not n['detalle'].strip():
            sys.exit('a new %s needs its text in "detalle": %r' % (n['tipo'], n))
        if n.get('area') not in AREAS:
            sys.exit('%s area %r is not one of %s' % (n['tipo'], n.get('area'), AREAS))
    elif not isinstance(n.get('id'), str) or not n['id'] or not isinstance(n.get('titulo', prev and prev['titulo']), str):
        sys.exit('bad item: %r' % n)
    if n['tipo'] not in ('pregunta', 'confirmar') and 'opciones' in n:
        sys.exit('%s: only questions and confirmations have options' % n['id'])
    if (n['tipo'] == 'pregunta' and not prev) or 'opciones' in n:
        if not valid_options(n.get('opciones')):
            sys.exit('%s: options need two or more distinct labels' % n['id'])
        if n['tipo'] == 'confirmar' and n.get('multiple'):
            sys.exit('%s: a confirmation takes a single choice' % n['id'])
        if 'multiple' in n and not isinstance(n['multiple'], bool):
            sys.exit('%s: "multiple" must be true or false' % n['id'])


def cmd_add(path):
    """New items are added; for items already there only the fields given
    change, and never Salvador's notes and choices, nor the text of an idea.
    A state changes only when given, and goes on the history as Claude's."""
    with open(path, encoding='utf-8') as f:
        new = json.load(f)
    if not isinstance(new, list):
        sys.exit('%s must hold a JSON list of items' % path)
    doc = load()
    by_id = {it['id']: it for it in doc['items']}
    for n in new:
        prev = by_id.get(n.get('id')) if isinstance(n, dict) else None
        check_new(n, prev)
        keep = FIELDS_USER + ('respuesta',) + (IDEA_FIXED if n['tipo'] in CAPTURED else ())
        if prev:
            for k, v in n.items():
                if k not in keep and k != 'id':
                    prev[k] = v
            if 'estado' in n and n['estado'] != prev['estado']:
                # Only when asked for (an idea analyzed or planned), and on record as Claude's.
                prev['estado'] = n['estado']
                prev['actualizado'] = now()
                prev['historial'].append({'fecha': prev['actualizado'], 'quien': 'Claude', 'accion': 'estado',
                                          'estado': n['estado'], 'texto': ''})
            if has_options(prev):
                clean_choice(prev)
            continue
        if n['tipo'] in CAPTURED:
            n['id'] = n.get('id') or next_idea_id(doc['items'], n['tipo'])
            n.setdefault('titulo', idea_title(n['detalle']))
            n.setdefault('capturada', now()[:10])
            n.setdefault('grupo', n['area'])
        n.setdefault('detalle', '')
        n.setdefault('fase', '')
        n.setdefault('grupo', '')
        n['origen'] = 'curado'
        n.setdefault('estado', STATES[n['tipo']][0])
        n.setdefault('nota', '')
        n.setdefault('respuesta', '')
        n.setdefault('historial', [])
        if has_options(n):
            clean_choice(n)
        doc['items'].append(n)
        by_id[n['id']] = n
        if n['tipo'] in CAPTURED:
            print('new', n['tipo'], n['id'], '—', n['titulo'])
    save(doc)
    print('added or updated', len(new), 'items')


def waiting(it):
    """Salvador wrote after Claude's last word, or set a state that asks for
    work. An authorized correction waits until Claude moves it on, whoever
    authorized it (a failing check becomes one already authorized)."""
    if it['tipo'] == 'correccion' and it['estado'] == 'autorizada' and not it.get('archivado'):
        return True
    last_user = last_claude = ''
    for h in it.get('historial', []):
        if h.get('quien') == 'Claude':
            last_claude = h.get('fecha', '')
        else:
            last_user = h.get('fecha', '')
    return last_user > last_claude and (it['estado'] in FOR_CLAUDE or it.get('nota'))


def failing_to_corrections(doc):
    """Each manual check Salvador marked failing becomes an authorized
    correction (D-9012), linked both ways; the check gets Claude's answer."""
    made = []
    for it in list(doc['items']):
        if it['tipo'] != 'prueba' or it['estado'] != 'falla' or it.get('correccion'):
            continue
        fecha = now()
        text = 'Falla en la prueba manual (%s): %s' % (it.get('grupo') or it.get('fase'), it['titulo'])
        if it.get('nota'):
            text += '\n\n' + it['nota']
        c = {'id': next_idea_id(doc['items'], 'correccion'), 'tipo': 'correccion', 'area': 'Juego', 'grupo': 'Juego',
             'capturada': fecha[:10], 'fase': it.get('fase', ''), 'origen': 'curado', 'prueba': it['id'],
             'titulo': idea_title(it['titulo']), 'detalle': text, 'estado': 'autorizada', 'nota': '', 'respuesta': '',
             'historial': [{'fecha': fecha, 'quien': 'Claude', 'accion': 'estado', 'estado': 'autorizada',
                            'texto': 'Creada desde la prueba ' + it['id']}], 'actualizado': fecha}
        doc['items'].append(c)
        it['correccion'] = c['id']
        it['respuesta'] = 'La paso a la corrección %s; cuando la marques "verificada", esta prueba queda como "funciona".' % c['id']
        it['historial'].append({'fecha': fecha, 'quien': 'Claude', 'accion': 'respuesta', 'estado': it['estado'],
                                'texto': it['respuesta']})
        made.append('%s -> %s' % (it['id'], c['id']))
    return made


def cmd_pending():
    doc = load()
    made = failing_to_corrections(doc)
    if made:
        save(doc)
        print('Failing checks turned into corrections:', ', '.join(made))
    todo = [it for it in doc['items'] if waiting(it)]
    fresh = [it['id'] for it in doc['items'] if it['tipo'] == 'idea' and it['estado'] == 'nueva' and not it.get('archivado')]
    if fresh:
        print('Ideas not yet analyzed (see "ideas"):', ', '.join(fresh))
    fixes = [it['id'] for it in doc['items'] if it['tipo'] == 'correccion' and it['estado'] == 'nueva' and not it.get('archivado')]
    if fixes:
        print('Corrections not yet authorized (Salvador decides):', ', '.join(fixes))
    if not todo:
        print('Nothing waits for Claude.')
    for it in todo:
        chosen = ' | eligió: ' + ', '.join(it['eleccion']) if it.get('eleccion') else ''
        print('- %s [%s] %s — %s%s' % (it['id'], it['estado'], it['titulo'][:90],
                                       (it.get('nota') or '').replace('\n', ' ')[:300], chosen))


def cmd_ideas():
    doc = load()
    ideas = [it for it in doc['items'] if it['tipo'] == 'idea' and not it.get('archivado')]
    questions = [it for it in doc['items'] if it['tipo'] == 'pregunta' and not it.get('archivado')]
    if not ideas and not questions:
        print('No open ideas.')
    for it in ideas:
        print('== %s [%s] %s (%s, %s)%s' % (it['id'], it['estado'], it['titulo'], it.get('area', ''),
                                           it.get('capturada', ''), ' -> fase ' + it['fasePlan'] if it.get('fasePlan') else ''))
        print(it['detalle'].strip())
        if it.get('analisis'):
            print('-- análisis:', it['analisis'].strip())
        if it.get('nota'):
            print('-- nota de Salvador:', it['nota'].strip())
        print()
    for it in questions:
        print('?? %s [%s] %s%s' % (it['id'], it['estado'], it['titulo'],
                                  ' (ideas ' + ', '.join(it['ideas']) + ')' if it.get('ideas') else ''))
        for o in it['opciones']:
            mark = 'x' if o['etiqueta'] in it['eleccion'] else ' '
            print('   [%s] %s%s' % (mark, o['etiqueta'], ' (recomendada)' if o.get('recomendada') else ''))
        if it.get('nota'):
            print('   nota de Salvador:', it['nota'].strip())
        print()


def cmd_archive():
    doc = load()
    done = []
    for it in doc['items']:
        closed = ((it['tipo'] == 'idea' and it['estado'] in ('planeada', 'descartada'))
                  or (it['tipo'] == 'correccion' and it['estado'] in ('verificada', 'descartada'))
                  or (it['tipo'] == 'pregunta' and it['estado'] == 'respondida'))
        if closed and not it.get('archivado'):
            it['archivado'] = True
            done.append(it['id'])
    save(doc)
    kept = [it['id'] for it in doc['items'] if it['tipo'] in ('idea', 'pregunta', 'correccion') and not it.get('archivado')]
    print('archived:', ', '.join(done) if done else 'nothing')
    print('still open:', ', '.join(kept) if kept else 'nothing')


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
            it.setdefault('historial', []).append({'fecha': it['actualizado'], 'quien': 'Claude', 'accion': 'respuesta',
                                                   'estado': it['estado'], 'texto': text})
            save(doc)
            print('answered', item_id)
            return
    sys.exit('no item ' + item_id)


def compact_history(it):
    """Runs of Salvador's old entries (no 'accion') become state changes and a
    single final note; everything else stays as it was."""
    out = []
    state = STATES[it['tipo']][0]
    note = ''
    run = []

    def flush():
        nonlocal state, note
        for e in run:
            if e.get('estado') != state:
                state = e.get('estado', state)
                out.append({'fecha': e['fecha'], 'quien': e['quien'], 'accion': 'estado', 'estado': state, 'texto': ''})
        if run:
            last = run[-1]
            text = (last.get('texto') or '').strip()
            if text != note:
                note = text
                out.append({'fecha': last['fecha'], 'quien': last['quien'], 'accion': 'nota', 'estado': state, 'texto': text})
        run.clear()

    for e in it.get('historial', []):
        if e.get('quien') != 'Claude' and 'accion' not in e:
            run.append(e)
            continue
        flush()
        out.append(e)
        if e.get('accion') == 'estado' or e.get('quien') == 'Claude':
            state = e.get('estado', state)
        if e.get('accion') == 'nota':
            note = (e.get('texto') or '').strip()
    flush()
    changed = len(out) != len(it.get('historial', []))
    it['historial'] = sorted(out, key=lambda e: e['fecha'])
    return changed


def cmd_compact():
    doc = load()
    changed = [it['id'] for it in doc['items'] if compact_history(it)]
    save(doc)
    print('compacted:', ', '.join(changed) if changed else 'nothing')


def main():
    args = sys.argv[1:]
    if args[:1] == ['sincronizar']:
        cmd_sync()
    elif args[:1] == ['agregar'] and len(args) == 2:
        cmd_add(args[1])
    elif args[:1] == ['compactar']:
        cmd_compact()
    elif args[:1] == ['pendientes']:
        cmd_pending()
    elif args[:1] == ['responder'] and len(args) == 4:
        cmd_answer(args[1], args[2], args[3])
    elif args == ['ideas']:
        cmd_ideas()
    elif args == ['archivar']:
        cmd_archive()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == '__main__':
    main()
