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
| Pruebas manuales | La lista de verificación manual (`docs/VERIFICACION_MANUAL.md`). Una que falla se vuelve corrección | sin probar, funciona, falla, no aplica |
| Decisiones | Todo `docs/DECISIONES.md` | sin revisar, aprobada, requiere cambio, requiere definición, descartada |
| Por confirmar | Decisiones que tomé solo y conviene que confirmes; las nuevas, con opciones | pendiente, confirmado, rechazado, requiere definición |
| Ideas | Tus ideas tal como las escribiste, y las mías ("de Claude": sugerencias y trabajo que quedó abierto); aquí también se escriben | nueva, analizada, para el plan, ajustar, para después, descartada, planeada |
| Correcciones | Fallas y mejoras pequeñas que encuentras al probar; aquí también se escriben | nueva, autorizada, en curso, corregida, no se reproduce, verificada, descartada |
| Análisis | Mis preguntas con opciones y mi análisis de cada idea | preguntas: sin responder, respondida, requiere definición |
| Resumen | Cuántos hay en cada estado, y un cuadro por fase | — |

Los estados que solo pongo yo (por ejemplo "analizada" o "corregida") se ven en el selector, pero no se pueden elegir.

Bajo la introducción de cada pestaña, **"¿Qué significa cada estado?"** despliega la explicación de cada estado. Al pasar el ratón sobre el estado de un elemento se ve la misma explicación.

**Enlaces entre secciones:**
- Una prueba que marcas "falla" se vuelve una corrección ya autorizada, y cada una muestra el número de la otra. Al marcar esa corrección "verificada", la prueba pasa sola a "funciona".
- Si en una decisión o una confirmación tu nota pide algo nuevo, lo paso a Ideas con tus palabras. La idea muestra "de D-…" y el elemento de origen muestra "→ I-…".

**Por confirmar con opciones:** las confirmaciones nuevas traen opciones, y la marcada "lo que hice" es lo que ya está implementado. Elegirla confirma. Elegir otra la rechaza, y cambio lo hecho por esa opción.

Cada pestaña muestra **atendidos/total**. Atendido es lo que ya no está en su primer estado y no tiene una respuesta mía sin leer. Lo pendiente aparece primero, lo atendido al final, y la casilla **ocultar atendidos** lo esconde.

Cada elemento tiene tu **nota** (lo que ves, lo que autorizas, lo que falta definir), mi **respuesta** y el **historial** de quién cambió qué y cuándo.

- **La nota se guarda con ✓ Guardar nota** (o Ctrl+Enter). Mientras escribes es un borrador: se marca "nota sin guardar", no llega al archivo y sobrevive si cierras la pestaña. "Descartar cambios" vuelve a la nota guardada.
- **El estado se guarda al elegirlo.**
- **El historial** tiene una entrada por acción: cada estado elegido, cada nota guardada y cada respuesta mía. Hay filtros por fase, estado y texto, y se pueden cambiar varios a la vez.

## Ideas y plan de trabajo

1. **Escribes ideas** en la pestaña Ideas ("+ Agregar idea", o Ctrl+Enter) o en el chat. Cada una recibe un número (I-001, I-002…) y su texto no se cambia nunca.
   Mientras una idea tuya siga en "nueva", puedes corregir su texto con **✎ Editar texto**. El texto anterior queda en el historial. Una vez que la analizo, el texto queda fijo; para matizarla usa tu nota o el estado "ajustar". Lo mismo vale para las correcciones en "nueva".
2. **Cuando me pides refinarlas**, publico en Análisis una evaluación por idea (cómo se haría, conflictos, riesgos, sugerencias) y las preguntas que necesito, con opciones como en el chat. La recomendada va marcada.
3. **Respondes cuando puedas.**
   - A cada idea analizada le das un estado: "para el plan", "ajustar" (explica en tu nota qué cambiarías), "para después" o "descartada".
   - En las preguntas eliges una opción (o varias, si lo dice). Si ninguna te sirve, escribe tu respuesta en "Otra respuesta o comentario" y guárdala.
4. **Me dices "revisa el registro".** Si falta algo, hago otra ronda de preguntas. Si no, escribo el plan por fases en la especificación y marco cada idea como "planeada", con su fase.
5. **Al cerrar la ronda** archivo las ideas planeadas o descartadas y las preguntas respondidas. No se borran: se ven con la casilla "archivadas". Las ideas "para después" siguen visibles para la próxima ronda.

## Correcciones

Son para lo que encuentras al probar el juego. No pasan por rondas de análisis ni por el plan.

1. **La anotas** en la pestaña Correcciones, o en el chat: qué pasó, qué esperabas y cómo llegaste ahí. Recibe un número (C-001…) y su texto no se cambia.
2. **La marcas "autorizada"** cuando quieres que la corrija. Si es algo que conviene pensar, déjala en "nueva".
3. **En una sesión dices "corrige lo autorizado".** Paso cada una a "en curso" y luego a "corregida", con una respuesta que dice qué cambié y cómo comprobarlo. Si no logro provocar el problema, queda en "no se reproduce" con mis preguntas.
4. **La pruebas.** Si quedó bien, márcala "verificada". Si no, regrésala a "autorizada" con una nota de lo que viste.

Si una corrección resulta ser un cambio de diseño, te lo digo y la paso al ciclo de ideas.

## Cómo lo uso yo

Cuando me pidas "revisa el registro", leo lo que marcaste:

- **Corrección autorizada**: la corrijo y la paso a "en curso" y luego a "corregida".
- **Requiere cambio, con problemas, falla, rechazado**: lo corrijo o te propongo cómo, y respondo en el elemento.
- **Requiere definición**: te respondo en el elemento con preguntas o una propuesta concreta; aparece en "Requiere tu atención" hasta que contestes.
- **Confirmado, aprobada, funciona**: queda registrado; no hago nada más.
- **Para el plan, ajustar, respondida**: lo tomo en cuenta al escribir el plan de trabajo.

Al cerrar cada fase agrego sus cambios, pruebas, decisiones y dudas (con opciones). Mis sugerencias y el trabajo que queda abierto van a Ideas, marcados "de Claude".

Herramienta (Python, sin dependencias):

```
python tools/revision/revision.py sincronizar            # vuelve a leer DECISIONES.md y VERIFICACION_MANUAL.md, sin perder tus estados
python tools/revision/revision.py pendientes             # lo que espera que yo actúe (antes pasa las pruebas que fallan a correcciones)
python tools/revision/revision.py responder <id> <estado|-> "<texto>"
python tools/revision/revision.py agregar <archivo.json> # cambios, dudas, ideas y correcciones nuevas
python tools/revision/revision.py compactar              # limpia historiales de la primera versión (nota guardada por partes)
python tools/revision/revision.py ideas                  # ideas y preguntas abiertas, con tus respuestas
python tools/revision/revision.py archivar               # cierra una ronda de ideas
python tools/revision/test_revision.py                   # pruebas de la herramienta (usan un archivo temporal)
```

Si la página está abierta mientras actualizo el archivo, se vuelve a leer sola; lo que estés editando en ese momento no se pierde.
