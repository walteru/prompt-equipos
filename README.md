# prompt-equipos

Generador de harness de trabajo para los equipos **DEV**, **TESTING**, para un agente
**SINGLE_DEVELOPER** que asume ambas responsabilidades y para el modo
**TEST_EN_BROWSER**, que valida la aplicación desde un navegador real, el modo
**ANÁLISIS**, destinado a estudiar una situación sin modificar código, y dos
equipos de **ANÁLISIS CONSENSUADO** para alinear interpretaciones.

Acompaña al post [Desarrollo asistido por IA: Generando prompts especializados para DEV y TESTING](https://sincrodev.com/blog/introduccion-prompt-equipos-flujo-dev-testing/)
del blog de SincroDev, que presenta el flujo que dio origen a la herramienta.

A partir de la plantilla maestra (`inicial.txt`), produce siete archivos listos para
pasar a los agentes:

- `_temps/DEV.txt`
- `_temps/TESTING.txt`
- `_temps/TEST_EN_BROWSER.txt`
- `_temps/SINGLE_DEVELOPER.txt`
- `_temps/REQUIERE_ANALISIS.txt`
- `_temps/ANALISIS_A.txt`
- `_temps/ANALISIS_B.txt`

Reemplaza dos placeholders en la plantilla:

| Placeholder en plantilla   | Se reemplaza por                                      |
|----------------------------|-------------------------------------------------------|
| `context_inicial_AAAA`     | `context_inicial_<proyecto>` en referencias `.txt` y `.md` |
| `<REQUERIMIENTO>`          | Texto del sprint/iteración (ingresado en vim)         |

La salida generada separa explícitamente:

- `context_inicial_<proyecto>.txt` y `context_inicial_<proyecto>.md`: formatos
  independientes del contexto inicial. Se usa cada uno que exista y, si están
  ambos, se leen ambos sin prioridad por extensión.
- `proxima.md`: contexto reciente opcional, no accionable por sí mismo.
- `REQUERIMIENTO DEL SPRINT ACTUAL`: única fuente que define la tarea vigente.

Para autodetectar el proyecto, el comando acepta cualquiera de las dos
extensiones. Estos archivos también pueden organizar conocimiento
tomando ideas del [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).
Los agentes deben aprovechar únicamente las ideas que aporten al proyecto, sin
exigir conformidad estricta con OKF ni aplicar su especificación a rajatabla.

Esto evita que los agentes confundan tareas históricas, notas de contexto o deuda
técnica preexistente con el requerimiento del sprint.
Si `proxima.md` lista tareas pendientes que no se alinean con el requerimiento
actual, los agentes deben separarlas como fuera de alcance y continuar con el
requerimiento vigente. Solo corresponde consultar si existe una contradicción
que impide tomar una decisión necesaria dentro del alcance.

Todos los modos aplican una política local-first común:

- El requerimiento se trabaja y valida localmente por defecto.
- Cuando un modo y su fase permiten modificar archivos, se prefiere la rama local
  `dev`, siempre que cambiar o crearla no ponga en riesgo trabajo preexistente.
- Sin una petición explícita del usuario, no se hace push, merge remoto, tag,
  release, publicación, promoción de entornos, migración en producción ni deploy.
- Tampoco se crean commits, se hace amend/rebase ni se modifica el historial sin
  una instrucción explícita. Cuando el usuario autoriza un commit, el agente debe
  revisar estado y diff, incluir solo archivos del alcance y reportar su hash.
- Completar una implementación, dejarla lista o encontrar instrucciones/scripts de
  despliegue no autoriza a ejecutarlos. El entorno de destino debe estar indicado
  expresamente por el usuario.

---

## Requisitos en cada proyecto

El comando se ejecuta **desde el directorio del proyecto**, que debe tener:

- Al menos un archivo `context_inicial_<proyecto>.txt` o
  `context_inicial_<proyecto>.md`.
- Si existen ambos, ambos se usan como contexto inicial sin prioridad por
  extensión.
- Un directorio `_temps/` (si no existe, el script lo crea).

Ejemplo:

```
mi-proyecto/
├── context_inicial_mi-proyecto.txt
├── context_inicial_mi-proyecto.md  ← opcional
└── _temps/
    ├── REQUERIMIENTO.txt   ← persistido, pre-cargado en la próxima corrida
    ├── DEV.txt             ← generado
    ├── TESTING.txt         ← generado
    ├── TEST_EN_BROWSER.txt ← prueba funcional en navegador real
    ├── SINGLE_DEVELOPER.txt ← generado
    ├── REQUIERE_ANALISIS.txt ← generado
    ├── ANALISIS_A.txt       ← análisis y consolidación
    └── ANALISIS_B.txt       ← análisis y validación
```

---

## Instalación

```bash
# 1. Clonar el repo donde te resulte cómodo
git clone git@github.com:walteru/prompt-equipos.git ~/prompt-equipos

# 2. Asegurar que el script sea ejecutable
chmod +x ~/prompt-equipos/prompts.py

# 3. Agregar el alias a ~/.bashrc (ajustar la ruta si clonaste en otro lado)
echo "alias prompts='python3 \$HOME/prompt-equipos/prompts.py'" >> ~/.bashrc
source ~/.bashrc
```

Requisitos: Python 3 y un editor (por defecto usa `vim`; respeta `$EDITOR` o `$VISUAL` si están seteados).

---

## Uso

Desde el directorio del proyecto:

```bash
prompts
```

Flujo:

1. Autodetecta el proyecto buscando `context_inicial_*.txt`; si no encuentra ninguno, busca `context_inicial_*.md`.
2. Abre tu editor (`vim` por defecto) sobre `_temps/REQUERIMIENTO.txt`:
   - La **primera vez** arranca con un header de instrucciones comentado.
   - En **corridas siguientes** ya viene pre-cargado con lo que escribiste antes (podés editar, agregar lo olvidado o reemplazarlo).
3. Escribís solo el requerimiento accionable del sprint/iteración (multilínea, sin problema). Las líneas que empiezan con `#` se ignoran al generar los prompts.
4. Guardás y salís del editor (`:wq` en vim).
5. Se generan `_temps/DEV.txt`, `_temps/TESTING.txt`, `_temps/TEST_EN_BROWSER.txt`,
   `_temps/SINGLE_DEVELOPER.txt`, `_temps/REQUIERE_ANALISIS.txt`, `_temps/ANALISIS_A.txt` y
   `_temps/ANALISIS_B.txt`, sobrescribiendo cualquier versión previa.
6. `_temps/REQUERIMIENTO.txt` queda guardado para la próxima corrida. Si querés arrancar en blanco, borralo manualmente.

Luego, en los agentes, basta decir algo como:

> *"leé `_temps/DEV.txt`"* (o `_temps/TESTING.txt` según el equipo)

Para asignar el requerimiento a un solo agente que asuma DEV y TESTING:

> *"debes leer `_temps/SINGLE_DEVELOPER.txt`"*

Ese agente analiza, implementa, prueba y auto-revisa el cambio en una misma
intervención, sin necesitar el circuito separado entre DEV y TESTING. El agente
no presupone que el requerimiento sea chico: evalúa si el alcance es razonable
para el sprint y, si resulta excesivo, propone una división incremental con un
alcance recomendado para la iteración actual.

Cuando el pedido consiste únicamente en comprender, diagnosticar o evaluar una
situación, sin codificar ni modificar archivos, usar:

> *"debes leer `_temps/REQUIERE_ANALISIS.txt`"*

Este modo inspecciona el proyecto en forma no destructiva, separa hechos de
hipótesis y entrega impacto, alternativas, recomendación y próximos pasos. No
implementa la solución propuesta.

Cuando se necesite validar el flujo como una persona usuaria en Chrome/Chromium:

> *"debes leer `_temps/TEST_EN_BROWSER.txt`"*

Esta modalidad exige abrir y usar una instancia real de navegador mediante
Chrome DevTools, Playwright u otra herramienta disponible. No acepta `curl`,
requests HTTP, tests unitarios o inspección de código como sustituto silencioso.
El agente debe informar herramienta, modo `HEADED`, `HEADLESS` o `REMOTO`, URL,
escenarios recorridos, consola/red y rutas de screenshots, trace o video. Si no
dispone de browser, URL o autenticación necesaria, finaliza `BLOCKED` en lugar de
afirmar que probó.

Que no aparezca una ventana en tu escritorio no significa necesariamente que no
haya browser: Playwright puede ejecutar el mismo motor Chromium en modo headless
y algunas herramientas controlan una instancia remota. Para lógica, navegación,
DOM, formularios, consola y red suele ser igual de efectivo. El modo visible es
preferible para observar animaciones, foco, diálogos nativos o defectos puramente
visuales; el harness lo prioriza cuando el entorno lo permite y obliga a declarar
qué modo se usó. Si el requerimiento exige ver una ventana, headless no cuenta
como validación completa.

Al terminar cualquier prueba de navegador con Chrome DevTools, Playwright u otra
automatización, también cuando se accede mediante MCP, el agente debe cerrar por
completo las instancias que abrió o controló. No basta con cerrar pestañas ni con
dejar una ventana en `about:blank`: antes de responder debe usar el cierre total
de la herramienta y comprobar que no queden ventanas o procesos de prueba
abiertos, sin afectar instancias preexistentes ajenas a la prueba.

Cuando dos equipos deban analizar el mismo requerimiento y confirmar una
interpretación común, usar en conversaciones separadas:

```text
debes leer _temps/ANALISIS_A.txt
debes leer _temps/ANALISIS_B.txt
```

Ambos comienzan con una línea base independiente. Después se intercambian
`_temps/ANALISIS_A_RESULTADO.md` y `_temps/ANALISIS_B_RESULTADO.md`, o sus
respuestas equivalentes. A consolida `_temps/ANALISIS_UNIFICADO.md`; B lo valida
con `CONSENSUS_READY` o solicita correcciones concretas con
`CONSENSUS_CHANGES_REQUESTED`. Las rondas continúan hasta representar fielmente
los acuerdos, supuestos, desacuerdos y preguntas externas. Ninguno de los dos
roles autoriza ni realiza implementación.

Cada generación asigna un `CONSENSUS_RUN_ID` común a A y B. Ese identificador
debe conservarse en resultados, handoffs y versiones del documento unificado.
Los agentes rechazan artefactos sin identificador verificable o pertenecientes a
otra ronda, evitando mezclar respuestas antiguas que todavía estén en `_temps/`.

Fases explícitas del flujo coordinado:

- `DEV=plan` y `TESTING=baseline` son los valores iniciales: ninguno modifica archivos.
- `DEV=implement` autoriza la implementación dentro del requerimiento.
- `TESTING=review` revisa la entrega concreta, el diff, tests y evidencia de DEV.
- La fase escrita en cada prompt es la fase inicial, no un estado que el archivo deba ir actualizando durante la conversación.
- Un handoff explícito para el requerimiento vigente cambia la fase efectiva sin editar ni regenerar `_temps/DEV.txt` o `_temps/TESTING.txt`:
  - TESTING emite `DEV_IMPLEMENT_READY` para pasar DEV de `plan` a `implement`.
  - DEV emite `TESTING_REVIEW_READY` para pasar TESTING de `baseline` a `review`.
  - Una instrucción explícita equivalente del coordinador también es válida.
- Los agentes no deben releer ni pedir que se actualice su `.txt` para confirmar uno de esos handoffs. Un comentario ambiguo o perteneciente a otro requerimiento no cambia la fase.

Regla de interpretación para ambos agentes:

- Cada archivo de contexto inicial que exista se lee como tal, sea `.txt`, `.md`
  o ambos, sin prioridad por extensión.
- Los archivos de contexto inicial y `proxima.md` explican el estado del proyecto.
- El bloque `REQUERIMIENTO DEL SPRINT ACTUAL` define qué se debe analizar, implementar o revisar.
- Si `proxima.md` contiene pendientes posiblemente heredados de otro sprint y no coinciden con el requerimiento actual, el agente los separa como fuera de alcance y avanza. Solo consulta ante una contradicción realmente bloqueante.
- Si el contexto menciona algo parecido pero no igual al requerimiento, debe tratarse como supuesto, duda o seguimiento opcional, no como parte automática del alcance.
- Si hay conflicto entre contexto y requerimiento, el requerimiento actual tiene prioridad.

Flujo recomendado de trabajo:

1. Ejecutar `prompts`, escribir el requerimiento y guardar.
2. Generar la primera fase y pasar los prompts en paralelo:

   ```bash
   prompts --dev-phase plan --testing-phase baseline
   ```

   - A DEV: `leé _temps/DEV.txt`
   - A TESTING: `leé _temps/TESTING.txt`
3. Esperar ambos outputs:
   - DEV entrega análisis inicial, criterios de aceptación, estrategia de validación y plan de implementación. En esta primera pasada no debe modificar código.
   - TESTING entrega su análisis inicial independiente como línea base.
4. Contrastar el plan de DEV con la línea base de TESTING y resolver únicamente dudas o bloqueantes reales. TESTING debe cerrar con `DEV_IMPLEMENT_READY` si se puede avanzar o `DEV_IMPLEMENT_BLOCKED` si falta una decisión realmente bloqueante. Opcionalmente, guardar las respuestas en `_temps/DEV_RESULTADO.md` y `_temps/TESTING_RESULTADO.md` para que las siguientes rondas puedan inspeccionarlas.
5. Pasar el handoff a DEV en la conversación. No hace falta modificar `_temps/DEV.txt`. Si se prefiere iniciar una conversación nueva directamente en implementación, se puede regenerar el prompt:

   ```bash
   prompts --dev-phase implement --testing-phase baseline --non-interactive
   ```

6. Tras implementar, DEV emite `TESTING_REVIEW_READY`; pasarlo a TESTING para que adopte REVIEW e inspeccione la entrega real, sin modificar `_temps/TESTING.txt`. Para iniciar una conversación nueva directamente en REVIEW, se puede regenerar el prompt:

   ```bash
   prompts --dev-phase implement --testing-phase review --non-interactive
   ```

   Si solo aparecen mejoras opcionales o riesgos no bloqueantes, cerrar el alcance actual.

En REVIEW, TESTING informa por separado el cumplimiento del requerimiento y los
estándares/diseño: aprobar un eje no compensa defectos del otro. Para bugs
difíciles o intermitentes, DEV y SINGLE_DEVELOPER deben construir primero un loop
que detecte el síntoma exacto, minimizarlo, probar hipótesis falsables y retirar
toda instrumentación temporal antes de cerrar.

Cuando un solo agente vaya a asumir DEV y TESTING, reemplazar los pasos 2 a 6
por una sola instrucción:
`debes leer _temps/SINGLE_DEVELOPER.txt`.

### Flujo de análisis consensuado

#### Versión simple y directa (sin archivos entre iteraciones)

Esta variante conserva las conversaciones de A y B como historial. No hace falta
guardar `ANALISIS_A_RESULTADO.md` ni `ANALISIS_B_RESULTADO.md`: el coordinador
copia y pega las respuestas necesarias de una conversación en la otra.

1. Abrir dos conversaciones y lanzar los análisis en simultáneo:

   ```text
   # Conversación del equipo A
   debes leer _temps/ANALISIS_A.txt

   # Conversación del equipo B
   debes leer _temps/ANALISIS_B.txt
   ```

2. Esperar las dos respuestas independientes. Elegir una, copiarla completa y
   mostrársela al otro equipo. Por ejemplo, copiar la respuesta de A en la
   conversación de B y decir:

   ```text
   Este es el análisis del equipo A para el mismo CONSENSUS_RUN_ID:

   [pegar aquí la respuesta completa de A]

   Revisalo contra tu propio análisis. Indicame coincidencias, diferencias
   materiales y comentarios que convenga discutir. Todavía no crees el
   documento unificado.
   ```

   También se puede hacer al revés: mostrarle a A la respuesta de B. No es
   obligatorio intercambiar ambos outputs si con una revisión cruzada alcanza.
3. Como coordinador, trasladar entre las conversaciones únicamente los
   comentarios o respuestas necesarios para resolver diferencias. Por ejemplo:

   ```text
   El otro equipo hizo este comentario:

   [pegar comentario]

   Evaluá el punto según la evidencia e indicá si estás de acuerdo o qué
   diferencia concreta continúa abierta.
   ```

   Repetir solo mientras haya diferencias relevantes; no hace falta guardar un
   archivo por cada intercambio.
4. Cuando la interpretación esté clara, pedirle a A:

   ```text
   Con lo acordado en esta conversación y los comentarios trasladados del
   equipo B, creá _temps/ANALISIS_UNIFICADO.md. Conservá el CONSENSUS_RUN_ID y
   dejá explícitos cualquier supuesto, pendiente o desacuerdo que siga abierto.
   ```

5. Para una comprobación final opcional, mostrarle a B el documento unificado y
   pedirle una revisión. Si B propone un cambio importante, trasladarlo a A para
   que ajuste el documento. Si responde `CONSENSUS_READY`, comunicárselo a A
   para que lo cierre como `COMPLETE`.

En este flujo, **A sigue creando el documento unificado y B funciona como
contraparte crítica**. El coordinador decide qué mensajes trasladar y cuándo la
discusión ya es suficiente para consolidar. El único archivo nuevo necesario es
el resultado final: `_temps/ANALISIS_UNIFICADO.md`.

#### Versión completa con resultados guardados

1. Ejecutar `prompts`, escribir la situación que se quiere analizar y guardar.
   Esto genera los dos prompts con el mismo `CONSENSUS_RUN_ID`.
2. Abrir dos conversaciones separadas y, en simultáneo, indicar:

   ```text
   # Conversación del equipo A
   debes leer _temps/ANALISIS_A.txt

   # Conversación del equipo B
   debes leer _temps/ANALISIS_B.txt
   ```

   En esta primera ronda ninguno debe conocer el análisis del otro.
3. Cuando ambos terminen, guardar sus respuestas completas —incluido el
   `CONSENSUS_RUN_ID`— en:

   ```text
   _temps/ANALISIS_A_RESULTADO.md
   _temps/ANALISIS_B_RESULTADO.md
   ```

4. Intercambiar los resultados y autorizar el contraste:
   - pasarle al equipo A `_temps/ANALISIS_B_RESULTADO.md`;
   - pasarle al equipo B `_temps/ANALISIS_A_RESULTADO.md`.

   Por ejemplo:

   ```text
   # Para A
   Contrasta tu análisis con _temps/ANALISIS_B_RESULTADO.md y prepara la consolidación.

   # Para B
   Contrasta tu análisis con _temps/ANALISIS_A_RESULTADO.md y reporta diferencias materiales.
   ```

5. Pedirle al equipo A que confeccione el borrador
   `_temps/ANALISIS_UNIFICADO.md`. **A es responsable de crear, actualizar y
   cerrar el documento unificado.**
6. Cuando A emita `CONSENSUS_REVIEW_READY`, pasarle a B ese handoff y
   `_temps/ANALISIS_UNIFICADO.md`. **B es responsable de validar el documento.**
7. Si B responde `CONSENSUS_CHANGES_REQUESTED`, pasar sus observaciones completas
   a A. A actualiza el documento y vuelve a emitir `CONSENSUS_REVIEW_READY`;
   repetir este intercambio hasta que B responda `CONSENSUS_READY`.
8. Pasar `CONSENSUS_READY` a A para que registre las validaciones y cierre
   `_temps/ANALISIS_UNIFICADO.md` con `ESTADO: COMPLETE`.
9. Si queda una decisión imprescindible que el repositorio no permite resolver,
   cerrar el análisis con `EXTERNAL_CLARIFICATION_REQUIRED` y la pregunta aislada.

En resumen, primero se intercambian las dos líneas base: **el resultado de B va
a A y el resultado de A va a B**. Después, el documento unificado circula de A
hacia B para su validación, y las correcciones solicitadas por B vuelven a A.

Si una ronda continúa en conversaciones nuevas, cada equipo debe recibir su
propio resultado anterior y el de la contraparte, ambos con el mismo
`CONSENSUS_RUN_ID`. El documento final incluye una matriz que relaciona cada
elemento del requerimiento con su interpretación, evidencia y estado, además de
las validaciones de A y B.

### Opciones

| Flag | Uso |
|------|-----|
| `--proyecto <nombre>` | Forzar el nombre del proyecto. Útil si hay varios archivos de la extensión detectada. |
| `--plantilla <ruta>`  | Usar otra plantilla en vez de `inicial.txt` del repo. |
| `-r`, `--requirement`, `--requerimiento`, `--archivo` | Leer el requerimiento desde un archivo; `-` usa stdin. También lo persiste en `_temps/REQUERIMIENTO.txt`. Los alias históricos se conservan por compatibilidad. |
| `--non-interactive` | No abrir editor; reutilizar el requerimiento persistido. |
| `--dev-phase plan\|implement` | Declarar explícitamente si DEV planifica o implementa. |
| `--testing-phase baseline\|review` | Declarar si TESTING crea línea base o revisa una entrega. |
| `--profile auto\|mixed\|php\|frontend\|javascript\|python\|mysql\|scripting` | Elegir perfil tecnológico; `auto` inspecciona marcadores del proyecto. |

Ejemplos:

```bash
prompts --proyecto chatbot
prompts --plantilla /ruta/a/otra-plantilla.txt
prompts --requirement historia.md --non-interactive
printf 'Corregir el flujo de login' | prompts --requirement - --non-interactive
prompts --dev-phase implement --testing-phase review --profile mixed --non-interactive
```

---

## La plantilla (`inicial.txt`)

Estructura esperada:

```
---------------------------------------------------------------------------------------------------------------------------------------------------
TESTING
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido del prompt TESTING, con context_inicial_AAAA.txt y <REQUERIMIENTO>>

---------------------------------------------------------------------------------------------------------------------------------------------------
TEST_EN_BROWSER
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido del prompt de validación obligatoria en navegador real>

---------------------------------------------------------------------------------------------------------------------------------------------------
DEV
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido del prompt DEV, con context_inicial_AAAA.txt y <REQUERIMIENTO>>

---------------------------------------------------------------------------------------------------------------------------------------------------
SINGLE_DEVELOPER
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido del prompt combinado de desarrollo y testing>

---------------------------------------------------------------------------------------------------------------------------------------------------
ANALISIS
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido del prompt de análisis sin modificación de código>

---------------------------------------------------------------------------------------------------------------------------------------------------
ANALISIS_A
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido para análisis independiente y consolidación>

---------------------------------------------------------------------------------------------------------------------------------------------------
ANALISIS_B
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido para análisis independiente y validación del consenso>
```

Los separadores son líneas con 20+ guiones. Los headers `TESTING`, `TEST_EN_BROWSER`,
`DEV`, `SINGLE_DEVELOPER`, `ANALISIS`, `ANALISIS_A` y `ANALISIS_B` se detectan entre
separadores. `TESTING`, `DEV`, `SINGLE_DEVELOPER` y `ANALISIS` son obligatorias.
`TEST_EN_BROWSER` es opcional para conservar compatibilidad con plantillas
personalizadas anteriores; cuando existe, genera el archivo homónimo. `ANALISIS_A` y
`ANALISIS_B` forman una pareja opcional para conservar compatibilidad con
plantillas personalizadas anteriores: pueden omitirse ambas, pero no solamente
una. Podés editar libremente el
contenido de cada bloque sin tocar el script; los reemplazos siguen funcionando
mientras se mantengan los placeholders `context_inicial_AAAA`, `<REQUERIMIENTO>`,
`<DEV_PHASE>`, `<TESTING_PHASE>`, `<TECH_PROFILE>`, `<GENERATED_METADATA>` y
`<CONSENSUS_RUN_ID>` cuando corresponda.

El perfil `auto` detecta marcadores habituales (`composer.json`, `package.json`,
`pyproject.toml`, migraciones, SQL y scripts). El harness siempre ordena inspeccionar
la configuración real antes de asumir frameworks, versiones o comandos.

## Validación del proyecto

```bash
python3 -m unittest discover -s tests -v
```

---

## Casos de error manejados

- **No hay `context_inicial_*.txt` ni `context_inicial_*.md`** → mensaje claro y exit 1.
- **Hay varios** archivos de la extensión prioritaria detectada → lista los nombres y pide usar `--proyecto`.
- **Requerimiento vacío** (cerraste el editor sin escribir nada útil) → cancela sin generar archivos.
- **Plantilla sin alguna sección requerida** → indica exactamente qué sección falta.
- **Plantilla con solo ANALISIS_A o ANALISIS_B** → exige completar u omitir la pareja.

---

## Créditos e inspiración

Varias ideas de este proyecto se tomaron de:

- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
- [mattpocock/skills](https://github.com/mattpocock/skills)

---

## Licencia

Este proyecto se distribuye bajo licencia MIT. Consulta [LICENSE](LICENSE).
