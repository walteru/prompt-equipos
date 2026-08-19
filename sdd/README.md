# sdd

CLI interactiva para generar documentos de Spec-Driven Development y prompts
para equipos `DEV`, `TESTING`, `TEST_EN_BROWSER`, `SINGLE_DEVELOPER`, `ANALISIS` y el par
`ANALISIS_A`/`ANALISIS_B` de análisis consensuado.

La herramienta esta pensada como una capa simple alrededor del flujo:

1. Constitucion del proyecto.
2. Spec funcional.
3. Plan tecnico.
4. Tasks verificables.
5. Prompts para agentes.

No requiere instalar Spec Kit ni ninguna dependencia externa. Genera Markdown
simple para que puedas mover, versionar o adaptar los archivos.

## Instalacion local

Desde este repo:

```bash
chmod +x sdd/sdd.py
```

Alias sugerido:

```bash
alias sdd='python3 /ruta/a/sdd/sdd.py'
```

## Uso

Ejecutar siempre desde la raiz del proyecto donde queres crear la spec.

```bash
sdd init
sdd spec
sdd plan
sdd tasks
sdd prompts
```

O todo junto:

```bash
sdd all
```

## Estructura generada

```text
.specify/
  memory/
    constitution.md

specs/
  001-nombre-feature/
    spec.md
    plan.md
    tasks.md
    prompts/
      DEV.txt
      TESTING.txt
      TEST_EN_BROWSER.txt
      SINGLE_DEVELOPER.txt
      ANALISIS.txt
      ANALISIS_A.txt
      ANALISIS_B.txt
```

## Comandos

| Comando | Resultado |
|---|---|
| `sdd init` | Crea `.specify/memory/constitution.md`. |
| `sdd spec` | Crea `specs/NNN-feature/spec.md`. |
| `sdd plan` | Crea `plan.md` para la ultima feature o la indicada con `--feature`. |
| `sdd tasks` | Crea `tasks.md` como slices verticales por criterio, con dependencias explícitas. |
| `sdd prompts` | Crea prompts para `DEV`, `TESTING`, `TEST_EN_BROWSER`, `SINGLE_DEVELOPER`, `ANALISIS` y `ANALISIS_A/B`. |
| `sdd all` | Ejecuta el flujo completo. |

Ejemplos:

```bash
sdd spec --number 7
sdd plan --feature 007
sdd prompts --feature nombre-feature --force
sdd prompts --feature 007 --dev-phase implement --testing-phase review --profile mixed
```

El flujo sigue siendo local-first. Los prompts no autorizan push, merge remoto,
release, deploy ni operaciones de producción. Tampoco autorizan commits, amend,
rebase o cambios de historial: cada commit requiere una instrucción explícita y
debe contener solamente los archivos del alcance confirmado. Cuando una fase
permite cambios se conserva la preferencia por la rama local `dev`, sin pisar
trabajo preexistente.

Al ejecutar `sdd tasks`, las dependencias se ingresan con el formato `CA2: CA1`.
Si un criterio no depende de otro, se deja sin declarar. La herramienta rechaza
referencias inexistentes, dependencias sobre sí mismas y ciclos.

## Criterio de uso

Usa `sdd` antes de pasar trabajo a los agentes. La idea es transformar una idea
ambigua en una unidad de trabajo con alcance, criterios de aceptacion, riesgos,
plan tecnico y tasks. Despues podes pasar el prompt generado:

```text
debes leer specs/001-nombre-feature/prompts/DEV.txt
```

O para un solo agente:

```text
debes leer specs/001-nombre-feature/prompts/SINGLE_DEVELOPER.txt
```

Para investigar sin modificar el proyecto:

```text
debes leer specs/001-nombre-feature/prompts/ANALISIS.txt
```

Para validar la spec recorriendo la interfaz en Chrome/Chromium real:

```text
debes leer specs/001-nombre-feature/prompts/TEST_EN_BROWSER.txt
```

El agente debe declarar si la sesión fue `HEADED`, `HEADLESS` o `REMOTO` y
reportar escenarios, consola, red y evidencia. Un test unitario o HTTP no
reemplaza esta modalidad; si no hay browser, URL o autenticación, responde
`BLOCKED` con el impedimento exacto.

Al terminar, incluso ante fallos o bloqueos, debe cerrar por completo todas las
instancias de navegador que abrió o controló, también si accedió mediante MCP,
Chrome DevTools o Playwright. Cerrar pestañas o dejar una ventana en
`about:blank` no cuenta como cierre; tampoco debe afectar instancias
preexistentes ajenas a la prueba.

Para que dos equipos construyan y validen una interpretación común sin
implementar, iniciar conversaciones separadas con:

```text
debes leer specs/001-nombre-feature/prompts/ANALISIS_A.txt
debes leer specs/001-nombre-feature/prompts/ANALISIS_B.txt
```

Ambos generan primero una línea base independiente. Luego A contrasta y
consolida `specs/NNN-feature/prompts/ANALISIS_UNIFICADO.md`; B responde `CONSENSUS_READY` o
`CONSENSUS_CHANGES_REQUESTED`. Si la inspección no permite resolver una decisión
imprescindible, el circuito registra lo acordado y cierra con
`EXTERNAL_CLARIFICATION_REQUIRED`.

Los dos prompts comparten un `CONSENSUS_RUN_ID` calculado para esa generación y
el contenido vigente de la feature. Resultados, handoffs y documento unificado
deben conservarlo; cualquier artefacto de otra ronda se rechaza. Si se retoma el
flujo en conversaciones nuevas, cada equipo debe recibir también su resultado
anterior. El documento final contiene una matriz de trazabilidad y las
validaciones explícitas de A y B.

Las fases `plan/baseline` son las predeterminadas. Usa `implement/review` para
generar una ronda que autorice a DEV a implementar y pida a TESTING revisar la
entrega concreta. El perfil tecnológico orienta la inspección, pero los agentes
deben respetar siempre los manifiestos, versiones y comandos reales del proyecto.
