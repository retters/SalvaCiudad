"""Tests for revision.py on a temporary revision.json (the real one is never
touched). Run: python tools/revision/test_revision.py"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revision  # noqa: E402


class RevisionTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        revision.DATA = os.path.join(self.dir.name, 'revision.json')

    def tearDown(self):
        self.dir.cleanup()

    def add(self, items):
        path = os.path.join(self.dir.name, 'add.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)
        with contextlib.redirect_stdout(io.StringIO()):
            revision.cmd_add(path)

    def text(self):
        with open(revision.DATA, encoding='utf-8') as f:
            return f.read()

    def items(self):
        with open(revision.DATA, encoding='utf-8') as f:
            return {it['id']: it for it in json.load(f)['items']}

    def run_cmd(self, fn, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            fn(*args)
        return out.getvalue()

    def question(self, **extra):
        q = {'id': 'q-orden', 'tipo': 'pregunta', 'titulo': '¿En qué orden?', 'ideas': ['I-001'],
             'opciones': [{'etiqueta': 'Primero A', 'descripcion': 'Porque sí', 'recomendada': True},
                          {'etiqueta': 'Primero B', 'descripcion': ''}]}
        q.update(extra)
        return q

    def test_ideas_are_numbered_and_keep_the_text(self):
        self.add([{'tipo': 'idea', 'area': 'Juego', 'detalle': 'Que llueva ranas.\nA veces.'},
                  {'tipo': 'idea', 'area': 'Red', 'detalle': 'Chat de voz'}])
        items = self.items()
        self.assertEqual(items['I-001']['titulo'], 'Que llueva ranas.')
        self.assertEqual(items['I-001']['detalle'], 'Que llueva ranas.\nA veces.')
        self.assertEqual(items['I-001']['estado'], 'nueva')
        self.assertEqual(items['I-002']['grupo'], 'Red')
        self.add([{'tipo': 'idea', 'area': 'Otro', 'detalle': 'Tercera'}])
        self.assertIn('I-003', self.items())

    def test_analysis_never_rewrites_the_idea(self):
        self.add([{'tipo': 'idea', 'area': 'Juego', 'detalle': 'Texto original'}])
        self.add([{'id': 'I-001', 'tipo': 'idea', 'detalle': 'Reescrita', 'area': 'Arte', 'estado': 'analizada',
                   'analisis': 'Buena idea; choca con I-004.'}])
        it = self.items()['I-001']
        self.assertEqual(it['detalle'], 'Texto original')
        self.assertEqual(it['area'], 'Juego')
        self.assertEqual(it['estado'], 'analizada')
        self.assertEqual(it['analisis'], 'Buena idea; choca con I-004.')
        self.assertEqual([(h['quien'], h['accion'], h['estado']) for h in it['historial']],
                         [('Claude', 'estado', 'analizada')])

    def test_user_fields_survive_an_update(self):
        self.add([self.question()])
        doc = revision.load()
        q = next(it for it in doc['items'] if it['id'] == 'q-orden')
        q.update(estado='respondida', eleccion=['Primero B'], nota='B, claro')
        revision.save(doc)
        self.add([self.question(titulo='¿En qué orden las hacemos?')])
        q = self.items()['q-orden']
        self.assertEqual(q['titulo'], '¿En qué orden las hacemos?')
        self.assertEqual((q['estado'], q['eleccion'], q['nota']), ('respondida', ['Primero B'], 'B, claro'))

    def test_bad_input_changes_nothing(self):
        self.add([{'tipo': 'idea', 'area': 'Juego', 'detalle': 'Una'}])
        before = self.text()
        bad = [
            [{'tipo': 'idea', 'area': 'Juego', 'detalle': 'ok'}, {'tipo': 'idea', 'area': 'Cocina', 'detalle': 'x'}],
            [{'tipo': 'idea', 'area': 'Juego', 'detalle': '   '}],
            [self.question(opciones=[{'etiqueta': 'Sola'}])],
            [self.question(opciones=[{'etiqueta': 'A'}, {'etiqueta': 'A'}])],
            [self.question(multiple='sí')],
            [{'id': 'I-001', 'tipo': 'pregunta', 'titulo': 'x', 'opciones': [{'etiqueta': 'A'}, {'etiqueta': 'B'}]}],
            [{'id': 'I-001', 'tipo': 'idea', 'estado': 'inventado'}],
            [{'tipo': 'idea', 'area': 'Juego', 'detalle': 'x' * (revision.MAX_TEXT + 1)}],
        ]
        for items in bad:
            with self.assertRaises(SystemExit, msg=items):
                self.add(items)
            self.assertEqual(self.text(), before)

    def test_damaged_choices_are_dropped_on_load(self):
        self.add([self.question()])
        doc = json.loads(self.text())
        doc['items'][0]['eleccion'] = ['Primero B', 'Inventada', 'Primero A']
        doc['items'].append({'id': 'q-rota', 'tipo': 'pregunta', 'titulo': 'x', 'estado': 'sin responder', 'opciones': 3})
        with open(revision.DATA, 'w', encoding='utf-8') as f:
            json.dump(doc, f)
        with contextlib.redirect_stdout(io.StringIO()):
            loaded = revision.load()
        ids = [it['id'] for it in loaded['items']]
        self.assertEqual(ids, ['q-orden'])
        self.assertEqual(loaded['items'][0]['eleccion'], ['Primero A'])  # Single choice: the first offered.

    def test_answers_and_notes_wait_for_claude(self):
        self.add([self.question(), {'tipo': 'idea', 'area': 'Juego', 'detalle': 'Una'}])
        doc = revision.load()
        for it in doc['items']:
            if it['id'] == 'q-orden':
                it.update(estado='respondida', eleccion=['Primero A'],
                          historial=[{'fecha': '2026-09-28T10:00:00-06:00', 'quien': 'Salvador', 'accion': 'eleccion',
                                      'estado': 'respondida', 'texto': 'Primero A'}])
        revision.save(doc)
        out = self.run_cmd(revision.cmd_pending)
        self.assertIn('q-orden [respondida]', out)
        self.assertIn('eligió: Primero A', out)
        self.assertIn('not yet analyzed (see "ideas"): I-001\n', out)
        self.assertNotIn('- I-001', out)  # A new idea is listed apart, not as waiting work.

    def test_archive_keeps_ideas_for_later(self):
        self.add([{'tipo': 'idea', 'area': 'Juego', 'detalle': t} for t in ('Planeada', 'Descartada', 'Después')])
        self.add([self.question()])
        self.add([{'id': 'I-001', 'tipo': 'idea', 'estado': 'planeada', 'fasePlan': '35'},
                  {'id': 'I-002', 'tipo': 'idea', 'estado': 'descartada'},
                  {'id': 'I-003', 'tipo': 'idea', 'estado': 'para después'},
                  {'id': 'q-orden', 'tipo': 'pregunta', 'estado': 'respondida'}])
        out = self.run_cmd(revision.cmd_archive)
        self.assertIn('still open: I-003', out)
        items = self.items()
        self.assertTrue(items['I-001']['archivado'] and items['I-002']['archivado'] and items['q-orden']['archivado'])
        self.assertNotIn('archivado', items['I-003'])
        self.assertEqual(items['I-001']['detalle'], 'Planeada')  # Archived, never deleted.
        listing = self.run_cmd(revision.cmd_ideas)
        self.assertIn('I-003', listing)
        self.assertNotIn('I-001', listing)
        # New ideas keep counting after archived ones.
        self.add([{'tipo': 'idea', 'area': 'Juego', 'detalle': 'Nueva'}])
        self.assertIn('I-004', self.items())

    def test_corrections_have_their_own_numbers_and_cycle(self):
        self.add([{'tipo': 'idea', 'area': 'Juego', 'detalle': 'Una idea'},
                  {'tipo': 'correccion', 'area': 'Interfaz', 'detalle': 'El botón Salir no responde'},
                  {'tipo': 'correccion', 'area': 'Juego', 'detalle': 'Los aldeanos atraviesan muros'}])
        items = self.items()
        self.assertEqual((items['C-001']['estado'], items['C-002']['titulo']), ('nueva', 'Los aldeanos atraviesan muros'))
        self.assertIn('I-001', items)
        self.assertIn('not yet authorized (Salvador decides): C-001, C-002', self.run_cmd(revision.cmd_pending))
        # Salvador authorizes one; it waits for Claude.
        doc = revision.load()
        c1 = next(it for it in doc['items'] if it['id'] == 'C-001')
        c1.update(estado='autorizada', historial=[{'fecha': '2026-09-28T10:00:00-06:00', 'quien': 'Salvador',
                                                   'accion': 'estado', 'estado': 'autorizada', 'texto': ''}])
        revision.save(doc)
        self.assertIn('- C-001 [autorizada]', self.run_cmd(revision.cmd_pending))
        # Claude fixes it; the text stays; once verified it is archived.
        self.add([{'id': 'C-001', 'tipo': 'correccion', 'estado': 'corregida', 'detalle': 'otro texto'}])
        self.assertEqual(self.items()['C-001']['detalle'], 'El botón Salir no responde')
        self.assertNotIn('- C-001', self.run_cmd(revision.cmd_pending))
        self.add([{'id': 'C-001', 'tipo': 'correccion', 'estado': 'verificada'}])
        self.run_cmd(revision.cmd_archive)
        items = self.items()
        self.assertTrue(items['C-001'].get('archivado'))
        self.assertNotIn('archivado', items['C-002'])
        with self.assertRaises(SystemExit):
            self.add([{'tipo': 'correccion', 'area': 'Cocina', 'detalle': 'x'}])

    def test_failing_check_becomes_an_authorized_correction(self):
        doc = revision.empty()
        doc['items'].append({'id': 'prueba-5-x', 'tipo': 'prueba', 'fase': '5', 'grupo': 'Fase 5: mercado', 'titulo': 'Se vende pan',
                             'detalle': '', 'estado': 'falla', 'nota': 'No aparece el botón', 'respuesta': '', 'origen': 'README',
                             'historial': [{'fecha': '2026-09-28T10:00:00-06:00', 'quien': 'Salvador', 'accion': 'estado',
                                            'estado': 'falla', 'texto': ''}]})
        revision.save(doc)
        out = self.run_cmd(revision.cmd_pending)
        self.assertIn('prueba-5-x -> C-001', out)
        self.assertIn('- C-001 [autorizada]', out)
        self.assertNotIn('- prueba-5-x', out)  # Answered: the correction carries it now.
        items = self.items()
        self.assertEqual(items['prueba-5-x']['correccion'], 'C-001')
        self.assertEqual(items['C-001']['prueba'], 'prueba-5-x')
        self.assertIn('No aparece el botón', items['C-001']['detalle'])
        self.assertNotIn('->', self.run_cmd(revision.cmd_pending))  # Only once.
        # Rebuilding the checks from the manual checklist keeps the link.
        doc = revision.load()
        revision.merge(doc, [{'id': 'prueba-5-x', 'tipo': 'prueba', 'fase': '5', 'grupo': 'Fase 5: mercado',
                              'titulo': 'Se vende pan', 'detalle': '', 'fuente': 'docs/VERIFICACION_MANUAL.md'}], 'README')
        self.assertEqual(next(i for i in doc['items'] if i['id'] == 'prueba-5-x')['correccion'], 'C-001')

    def test_confirmations_may_offer_options(self):
        conf = {'id': 'conf-x', 'tipo': 'confirmar', 'titulo': '¿Cuántas monedas?',
                'opciones': [{'etiqueta': '100', 'actual': True}, {'etiqueta': '200'}]}
        self.add([conf])
        self.assertEqual(self.items()['conf-x']['eleccion'], [])
        self.add([{'id': 'conf-y', 'tipo': 'confirmar', 'titulo': 'Sin opciones'}])  # Still allowed.
        for bad in ([dict(conf, id='conf-z', multiple=True)],
                    [dict(conf, id='conf-z', opciones=[{'etiqueta': '1', 'actual': 'sí'}, {'etiqueta': '2'}])],
                    [{'id': 'D-1', 'tipo': 'decision', 'titulo': 'x', 'opciones': conf['opciones']}]):
            with self.assertRaises(SystemExit, msg=bad):
                self.add(bad)

    def test_ideas_listing_shows_choices(self):
        self.add([{'tipo': 'idea', 'area': 'Arte', 'detalle': 'Texto completo\ncon dos líneas'}, self.question()])
        out = self.run_cmd(revision.cmd_ideas)
        self.assertIn('Texto completo\ncon dos líneas', out)
        self.assertIn('[ ] Primero A (recomendada)', out)


if __name__ == '__main__':
    unittest.main()
