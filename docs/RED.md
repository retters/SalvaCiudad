# Red: multijugador por lockstep

Cómo juegan varias computadoras la misma partida (sección 7.4 de la especificación). El código está en `src/net/`.

## Idea

Cada computadora simula **todo** el mundo. Por la red solo viajan las órdenes de los jugadores ("colocar una casa aquí", "dos trabajadores en el leñador"). Como la simulación es determinista (`docs/DETERMINISMO.md`), las mismas órdenes en el mismo tick dan el mismo resultado en todas las máquinas. El tráfico no depende de cuántos aldeanos haya.

La topología es una **estrella**: el anfitrión recibe las órdenes de todos y reparte los **turnos**. Cada cliente solo habla con el anfitrión.

## Turnos

- Un turno es un tick (100 ms de juego). El turno *T* lleva las órdenes que se ejecutan al pasar del tick *T* al *T+1*, en el orden en que llegaron al anfitrión.
- El anfitrión **cierra** el turno *T + retraso* antes de ejecutar el *T*, y lo envía a todos. Así los clientes reciben cada turno antes de necesitarlo.
- El **retraso** va de 2 a 10 turnos: la mitad del tiempo de ida y vuelta más lento, más 50 ms, medido en ticks a la velocidad actual. Se recalcula cada segundo; solo crece de golpe, y al bajar se deja de cerrar turnos hasta alcanzarlo.
- Una orden que un jugador da en el tick *T* se ejecuta en el primer turno que el anfitrión cierre después de recibirla. El anfitrión reemplaza el jugador de cada orden por el asiento de quien la mandó: nadie da órdenes en nombre de otro.
- Los clientes van a lo sumo un retraso por delante del anfitrión. Si un cliente se atrasa, alcanza a los demás corriendo hasta 8 ticks por cuadro.

## Comprobación y desincronización

- Cada 5 ticks los clientes confirman hasta dónde llegaron. Cada 50 ticks (5 s a x1; por encima de x1, cada 5 s reales: 250 ticks a x5) mandan además los hashes de siete partes del estado: cabecera, jugadores, entidades, recursos del mapa, edificios, aldeanos y generador aleatorio.
- El anfitrión compara con sus propios hashes del mismo tick. Si alguno no coincide:
  - se avisa a todos;
  - se guarda un informe en la carpeta de registros (`logs/desync-<tick>-seat<n>.txt`) con las partes que difieren;
  - el anfitrión le manda a ese jugador su estado completo (la instantánea), y el jugador sigue desde ahí.

## Jugadores lentos

Si un jugador queda más de 30 ticks detrás del anfitrión (3 s; por encima de x1 son los ticks de 3 s reales), el anfitrión espera y todos ven "Esperando a …". Si la espera dura más de 3 s y la velocidad es mayor que x1, la velocidad baja un paso para todos y se avisa quién la bajó.

## Velocidad y pausa (sección 7.5)

- **Pausa:** inmediata. Cualquier jugador la pide y el anfitrión la aplica sin votación.
- **Reanudar y cambiar de velocidad:** se vota. El que la pide acepta solo; los demás ven "Aceptar" y "Rechazar". Pasa cuando todos aceptan; basta un rechazo para descartarla, y se descarta sola a los 15 s.
- Cada turno lleva la velocidad del anfitrión, así que un jugador que vuelve a entrar la ve bien.
- **Velocidades (fase 58):** x0,25, x0,5 y x1 a x5; las de x6 a x9 solo existen en un jugador. La velocidad viaja en cuartos de x1 (4 es x1, 20 es x5); un mensaje con otro valor se rechaza. El retraso de las órdenes llega hasta 1 s real a cualquier velocidad.

## Sala, arranque y mundo

1. El anfitrión elige el mapa (la misma pantalla de partida nueva) y abre la sala. Escucha en el puerto 47800 (más el número de `--instance`).
2. Cada jugador que se conecta manda un saludo con:
   - la versión del protocolo y la del juego;
   - el hash del contenido y la lista de mods que afectan a la simulación;
   - su nombre.
   Si la versión o los mods no coinciden, se le rechaza diciéndole qué falta y qué sobra.
3. En la sala cada jugador elige nombre y color y avisa que está listo. El anfitrión elige el mundo:
   - **mapa compartido con un pueblo común:** todos dan órdenes al mismo pueblo, con los mismos permisos;
   - **mapa compartido con un pueblo por jugador:** aliados, cada uno con su centro del pueblo, y nadie puede tocar lo de otro.
4. Al empezar:
   - los asientos se ordenan 0..n−1;
   - cada máquina **genera el mapa por su cuenta** con la misma configuración (no se envía el mapa) y avisa con el hash del mapa;
   - un mapa distinto se detecta y se desconecta a ese jugador;
   - el juego empieza cuando todos terminaron.

## Fundar los pueblos (fase 74)

- La partida empieza sin pueblos. Cada jugador con pueblo propio elige dónde fundarlo; en un pueblo común funda el anfitrión.
- Mientras falte alguien, el tiempo no corre (el tick se queda en 0), pero los turnos siguen: llevan las órdenes de fundar. Los turnos se numeran con `Game::turn()` (tick más pasos de espera), no con el tick.
- En esa espera el anfitrión ignora las pausas y los votos de velocidad.
- Al empezar, el mapa se genera con los sitios sugeridos que pidió el anfitrión, y al menos uno por pueblo a fundar.

## Entrar a una partida empezada y reconectar

- Un jugador que vuelve con **el mismo nombre** recupera su asiento. En un pueblo común creado en la sala, un jugador nuevo recibe un asiento nuevo (orden `AddSeat` del anfitrión) y queda unido al pueblo (orden `JoinTown`); en pueblos separados puede ocupar el de un jugador que se fue.
- El anfitrión le manda la instantánea del juego (la misma serialización que las partidas guardadas, comprimida con zstd) y los turnos ya cerrados desde ese tick. Mientras tanto los demás siguen jugando.
- Un jugador desconectado deja su pueblo trabajando solo hasta que vuelva.

## Mensajes

Cada mensaje es un byte de tipo y sus campos en little-endian (`src/net/protocol.h`). Todo se valida al leer, como un archivo externo: tamaños, cantidades, rangos, textos UTF-8 sin caracteres de control y el orden del tipo. Un mensaje inválido desconecta a quien lo mandó.

| Tipo | Dirección | Contenido |
|---|---|---|
| Hello | cliente → anfitrión | protocolo, versión, hash del contenido, mods, nombre |
| Welcome | anfitrión → cliente | asiento |
| Reject | anfitrión → cliente | motivo, versión y mods del anfitrión |
| Lobby | anfitrión → todos | configuración, fase, asientos |
| SetInfo | cliente → anfitrión | nombre, color, listo |
| Start | anfitrión → todos | configuración y asientos en juego |
| Loaded | cliente → anfitrión | hash del mapa generado |
| Commands | cliente → anfitrión | órdenes (hasta 256) |
| Turn | anfitrión → todos | tick, velocidad, órdenes con su asiento |
| Ack | cliente → anfitrión | tick alcanzado y, cada 50 ticks, hashes por parte |
| Snapshot | anfitrión → cliente | tick y estado comprimido (hasta 512 MB) |
| SpeedPropose / SpeedAnswer | cliente → anfitrión | pedir una velocidad / votar |
| SpeedVote / SpeedSet / VoteEnded | anfitrión → todos | votación abierta, velocidad aplicada, votación fallida |
| Notice | anfitrión → todos | entró, salió, volvió, desincronización, mapa distinto |

Los mensajes, salvo la instantánea, miden a lo sumo 256 KB. ENet los entrega en orden y con confirmación en un solo canal.

## Descubrimiento en la red local

- El anfitrión escucha en el puerto UDP 47799.
- Quien busca partidas manda cada segundo un sondeo por difusión (`SCPROBE1` y la versión del protocolo).
- El anfitrión responde con su puerto, su nombre, cuántos jugadores hay y si la partida empezó.
- La respuesta se valida como cualquier mensaje. Una partida que no responde en 5 s desaparece de la lista.

## Varias ventanas en una computadora

- `SalvaCiudad.exe --instance 2` usa la carpeta de datos `instance-2` (configuración, partidas y registros propios), una ventana pequeña y el puerto 47802.
- `--loopback` hace que el anfitrión solo acepte conexiones de la misma computadora (127.0.0.1) y que no busque ni anuncie partidas en la red, así Windows no pregunta por el firewall.

Por ejemplo, en dos consolas:

```
SalvaCiudad.exe --instance 1 --loopback
SalvaCiudad.exe --instance 2 --loopback
```

La 1 crea la partida. La 2 se une a `127.0.0.1`, puerto `47801`.

## Pruebas automáticas

La suite `net` (`tests/test_net.cpp`) corre varias máquinas en un proceso con una red en memoria:

- doce jugadores en un pueblo común;
- cuatro pueblos separados;
- un jugador que se cae y vuelve;
- una desincronización provocada que se detecta y se repara;
- pueblos por fundar: el tiempo espera a todos, solo el anfitrión funda el pueblo común, y quien entra durante la espera recibe la misma partida;
- votos de velocidad;
- rechazos por versión y por mods.

La suite `net_enet` hace lo mismo con ENet real en 127.0.0.1.
