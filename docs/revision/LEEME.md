# Registro de revisión

Una página local para revisar todo lo que se implementó y decirme qué hacer con cada cosa, sin conversación de por medio.

## Abrirlo

1. Abre `docs/revision/index.html` con **Edge o Chrome** (doble clic).
2. Pulsa **Abrir revision.json** y elige `docs/revision/revision.json`.
3. Da permiso de edición cuando el navegador lo pida.

Desde ahí, cada cambio se guarda solo en ese archivo, en menos de un segundo. La próxima vez basta con **Reconectar**. La página no usa internet ni instala nada.

En Firefox la página no puede escribir en el archivo: usa **Descargar** y reemplaza `revision.json` con lo descargado.

## Pestañas

| Pestaña | Qué hay | Estados |
|---|---|---|
| Requiere tu atención | Mis respuestas que no leíste y lo que espera tu confirmación | — |
| Cambios | Qué se implementó en cada fase | sin revisar, revisado, aprobado, con problemas |
| Pruebas manuales | La lista de verificación del README | sin probar, funciona, falla, no aplica |
| Decisiones | Todo `docs/DECISIONES.md` | sin revisar, aprobada, requiere cambio, requiere definición, descartada |
| Por confirmar | Decisiones que tomé solo y conviene que confirmes | pendiente, confirmado, rechazado, requiere definición |
| Sugerencias | Ideas mías | sin revisar, autorizada, requiere definición, pospuesta, descartada, en curso, implementada |
| Pendientes | Trabajo abierto de la especificación | abierto, autorizado, requiere definición, pospuesto, descartado, en curso, hecho |
| Ideas | Tus ideas tal como las escribiste, por área; aquí también se escriben | nueva, analizada, para el plan, ajustar, para después, descartada, planeada |
| Análisis | Mis preguntas con opciones y mi análisis de cada idea | preguntas: sin responder, respondida, requiere definición |
| Resumen | Cuántos hay en cada estado, y un cuadro por fase | — |

Cada pestaña muestra **atendidos/total**. Atendido es lo que ya no está en su primer estado y no tiene una respuesta mía sin leer. Lo pendiente aparece primero, lo atendido al final, y la casilla **ocultar atendidos** lo esconde.

Cada elemento tiene tu **nota** (lo que ves, lo que autorizas, lo que falta definir), mi **respuesta** y el **historial** de quién cambió qué y cuándo.

- **La nota se guarda con ✓ Guardar nota** (o Ctrl+Enter). Mientras escribes es un borrador: se marca "nota sin guardar", no llega al archivo y sobrevive si cierras la pestaña. "Descartar cambios" vuelve a la nota guardada.
- **El estado se guarda al elegirlo.**
- **El historial** tiene una entrada por acción: cada estado elegido, cada nota guardada y cada respuesta mía. Hay filtros por fase, estado y texto, y se pueden cambiar varios a la vez.

## Ideas y plan de trabajo

1. **Escribes ideas** en la pestaña Ideas ("+ Agregar idea", o Ctrl+Enter) o en el chat. Cada una recibe un número (I-001, I-002…) y su texto no se cambia nunca.
2. **Cuando me pides refinarlas**, publico en Análisis una evaluación por idea (cómo se haría, conflictos, riesgos, sugerencias) y las preguntas que necesito, con opciones como en el chat. La recomendada va marcada.
3. **Respondes cuando puedas.**
   - A cada idea analizada le das un estado: "para el plan", "ajustar" (explica en tu nota qué cambiarías), "para después" o "descartada".
   - En las preguntas eliges una opción (o varias, si lo dice). Si ninguna te sirve, escribe tu respuesta en "Otra respuesta o comentario" y guárdala.
4. **Me dices "revisa el registro".** Si falta algo, hago otra ronda de preguntas. Si no, escribo el plan por fases en la especificación y marco cada idea como "planeada", con su fase.
5. **Al cerrar la ronda** archivo las ideas planeadas o descartadas y las preguntas respondidas. No se borran: se ven con la casilla "archivadas". Las ideas "para después" siguen visibles para la próxima ronda.

## Cómo lo uso yo

Cuando me pidas "revisa el registro", leo lo que marcaste:

- **Autorizada / autorizado**: lo implemento y lo paso a "en curso" y luego a "implementada" o "hecho".
- **Requiere cambio, con problemas, falla, rechazado**: lo corrijo o te propongo cómo, y respondo en el elemento.
- **Requiere definición**: te respondo en el elemento con preguntas o una propuesta concreta; aparece en "Requiere tu atención" hasta que contestes.
- **Confirmado, aprobada, funciona**: queda registrado; no hago nada más.
- **Para el plan, ajustar, respondida**: lo tomo en cuenta al escribir el plan de trabajo.

Al cerrar cada fase agrego sus cambios, pruebas, decisiones, dudas y sugerencias.

Herramienta (Python, sin dependencias):

```
python tools/revision/revision.py sincronizar            # vuelve a leer DECISIONES.md y README.md, sin perder tus estados
python tools/revision/revision.py pendientes             # lo que espera que yo actúe
python tools/revision/revision.py responder <id> <estado|-> "<texto>"
python tools/revision/revision.py agregar <archivo.json> # cambios, dudas y sugerencias nuevas
python tools/revision/revision.py compactar              # limpia historiales de la primera versión (nota guardada por partes)
python tools/revision/revision.py ideas                  # ideas y preguntas abiertas, con tus respuestas
python tools/revision/revision.py archivar               # cierra una ronda de ideas
python tools/revision/test_revision.py                   # pruebas de la herramienta (usan un archivo temporal)
```

Si la página está abierta mientras actualizo el archivo, se vuelve a leer sola; lo que estés editando en ese momento no se pierde.
