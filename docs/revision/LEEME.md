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
| Resumen | Cuántos hay en cada estado, y un cuadro por fase | — |

Cada elemento tiene tu **nota** (lo que ves, lo que autorizas, lo que falta definir), mi **respuesta** y el **historial** de quién cambió qué y cuándo. Hay filtros por fase, estado y texto, y se pueden cambiar varios a la vez.

## Cómo lo uso yo

Cuando me pidas "revisa el registro", leo lo que marcaste:

- **Autorizada / autorizado**: lo implemento y lo paso a "en curso" y luego a "implementada" o "hecho".
- **Requiere cambio, con problemas, falla, rechazado**: lo corrijo o te propongo cómo, y respondo en el elemento.
- **Requiere definición**: te respondo en el elemento con preguntas o una propuesta concreta; aparece en "Requiere tu atención" hasta que contestes.
- **Confirmado, aprobada, funciona**: queda registrado; no hago nada más.

Al cerrar cada fase agrego sus cambios, pruebas, decisiones, dudas y sugerencias.

Herramienta (Python, sin dependencias):

```
python tools/revision/revision.py sincronizar            # vuelve a leer DECISIONES.md y README.md, sin perder tus estados
python tools/revision/revision.py pendientes             # lo que espera que yo actúe
python tools/revision/revision.py responder <id> <estado|-> "<texto>"
python tools/revision/revision.py agregar <archivo.json> # cambios, dudas y sugerencias nuevas
```

Si la página está abierta mientras actualizo el archivo, se vuelve a leer sola; lo que estés editando en ese momento no se pierde.
