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
7. **Versión de reglas.** `kGameRulesVersion` (en `game.h`) sube cada vez que cambian las reglas de la simulación a propósito. Las partidas guardadas y las instantáneas de otra versión se rechazan con un mensaje claro.
8. **Scripts de mods (fase 7).** Solo reciben y devuelven enteros y `Fixed`, y su biblioteca `math` se reemplaza por estas funciones.

## Cómo se verifica

Pruebas automáticas (`tests/test_sim.cpp`), en todas las configuraciones:

| Prueba | Qué garantiza |
|---|---|
| `sim_rules` | Ningún archivo de `src/sim` usa `float`, `double`, contenedores desordenados, relojes, archivos, hilos ni aleatorios estándar |
| `sim_fixed` | Aritmética, saturación, raíces exactas, trigonometría contra la referencia |
| `sim_rng` | PCG32 da la secuencia de referencia; los flujos son independientes |
| "the same commands give the same game" (`test_village.cpp`) | Dos partidas con los mismos comandos dan el mismo hash |
| "a game session saves and loads to the same hash" (`test_save.cpp`) | Guardar, cargar y seguir da el mismo hash que no guardar |
| "twelve players in a common town stay in step" (`test_net.cpp`) | 12 máquinas con los mismos comandos no se separan |
| "a desynchronization is found and repaired" (`test_net.cpp`) | Un estado distinto se detecta por su hash y se repara |
| "a game without towns keeps its wildlife alive" (`test_wildlife.cpp`) | El mapa de fondo del menú (fase 50) también es repetible |

Hasta la fase 50 había además un mundo de prueba de caminantes (fase 5) con su hash de referencia y sus repeticiones; se borró cuando la simulación del juego ya cubría lo mismo (D-5002).

Si una prueba del hash de referencia falla sin que hayas cambiado las reglas a propósito, **se rompió el determinismo**: hay que encontrar la causa, no actualizar el número.
