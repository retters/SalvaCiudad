# Determinismo: reglas de la simulación

El multijugador funciona por **lockstep** (D-001): cada máquina simula todo, y solo viajan los comandos. Para que las partidas no se separen, la simulación tiene que dar **exactamente los mismos bits** en todas las máquinas, compiladores y sistemas. Este documento es la lista de reglas para el código de `src/sim/`, y cómo se verifica.

## Reglas

1. **Nada de coma flotante.** Ni `float` ni `double`, ni funciones como `std::sin` o `std::sqrt`.
   - Se usa `Fixed`, punto fijo 16.16 en 32 bits: rango de ±32 767 con precisión de 1/65 536. Las cuentas grandes (distancias al cuadrado) se hacen en enteros de 64 bits.
   - `Fixed` **satura** en lugar de desbordar, redondea las divisiones hacia cero y las multiplicaciones hacia abajo. Todo está definido: nunca hay comportamiento indefinido.
   - Raíz cuadrada entera exacta (`isqrt`, `sqrt`).
   - Seno y coseno por tabla generada (`tools/sim/make_trig_tables.py` → `fixed_tables.inc`), con interpolación entera.
   - `atan2` con CORDIC entero.
   - Los ángulos son `Angle`: 65 536 unidades por vuelta, así que dan la vuelta solos.
2. **Números aleatorios propios.** `Rng` (PCG32), con una semilla derivada de la partida y un **flujo por sistema**, para que un sistema nuevo no altere la secuencia de los demás. Nunca `rand()` ni `<random>`: sus resultados cambian entre bibliotecas estándar.
3. **Orden de iteración definido.** Nada de `unordered_map`, `unordered_set` ni de ordenar por direcciones de memoria.
   - Las entidades son ranuras numeradas con generación (`EntityId`), y los componentes se guardan densos (`ComponentStore`).
   - El orden solo depende de la secuencia de operaciones.
   - Si hay que borrar mientras se recorre, se junta la lista y se borra después, en el orden encontrado.
4. **La simulación no mira afuera.** No lee el reloj, ni archivos, ni variables de entorno, ni configuraciones locales, ni usa hilos. Todo lo que cambia el mundo entra como **comando**, y el tiempo avanza en **ticks** de 100 ms de juego.
5. **Comandos en orden fijo.** Dentro de un tick, los comandos se aplican por número de secuencia (en multijugador lo asigna el anfitrión). Un comando inválido para el estado actual (una entidad muerta, un mundo lleno) se **ignora y se cuenta**, igual en todas las máquinas.
6. **Estado serializable y comparable.** Todo el estado se guarda en binario little-endian explícito (`BinaryWriter`) y su **hash** (FNV-1a de 64 bits) se calcula cada 10 ticks. Si dos máquinas tienen hashes distintos, se desincronizaron.
7. **Versión de reglas.** `kRulesVersion` (en `world.h`) sube cada vez que cambian las reglas de la simulación a propósito. Las repeticiones y las instantáneas de otra versión se rechazan con un mensaje claro.
8. **Scripts de mods (fase 7).** Solo reciben y devuelven enteros y `Fixed`, y su biblioteca `math` se reemplaza por estas funciones.

## Cómo se verifica

Pruebas automáticas (`tests/test_sim.cpp`), en todas las configuraciones:

| Prueba | Qué garantiza |
|---|---|
| `sim_rules` | Ningún archivo de `src/sim` usa `float`, `double`, contenedores desordenados, relojes, archivos, hilos ni aleatorios estándar |
| `sim_fixed` | Aritmética, saturación, raíces exactas, trigonometría contra la referencia |
| `sim_rng` | PCG32 da la secuencia de referencia; los flujos son independientes |
| "the same game gives the same hashes" | Dos corridas iguales dan los mismos 150 hashes |
| "twelve simulations in one process" | 12 mundos con los mismos comandos no se separan (el caso de 12 jugadores) |
| "saving, loading and continuing" | Guardar a mitad, cargar y seguir da el mismo hash que no guardar |
| "the scenario hash is the same on every build" | El escenario da un **hash de referencia fijo** en `debug`, `release` y `debug-asan`; en Linux y macOS deberá dar el mismo |
| `sim_replay` | Una partida grabada se reproduce exactamente desde un archivo; un comando alterado se detecta en el siguiente punto de control; los archivos dañados se rechazan |

Si una prueba del hash de referencia falla sin que hayas cambiado las reglas a propósito, **se rompió el determinismo**: hay que encontrar la causa, no actualizar el número.

## Repeticiones

`Simulation::recording()` devuelve la partida grabada: la semilla, cada comando con su tick y los hashes de control. `verify_replay` la vuelve a jugar y compara. Formato del archivo (`.screplay`):

- Firma `SCRP` y versión del formato.
- Versión de reglas, semilla y tick final.
- Los comandos, de 32 bytes cada uno con su tick y su secuencia.
- Los puntos de control (tick y hash).
- Suma de verificación FNV-1a de todo lo anterior.

Se lee con límites y se valida por completo. Servirá para reproducir errores del multijugador y para detectar desincronizaciones.
