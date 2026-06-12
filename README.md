# prompt-equipos

Generador de prompts para los equipos **DEV** y **TESTING** que asisten en proyectos.

A partir de una plantilla maestra (`inicial.txt`), produce dos archivos listos para
pasar a los agentes:

- `_temps/DEV.txt`
- `_temps/TESTING.txt`

Reemplaza dos placeholders en la plantilla:

| Placeholder en plantilla         | Se reemplaza por                                |
|----------------------------------|-------------------------------------------------|
| `context_inicial_AAAA.txt`       | `context_inicial_<proyecto>.txt` (autodetectado)|
| `<REQUERIMIENTO>`                | Texto del sprint/iteración (ingresado en vim)   |

---

## Requisitos en cada proyecto

El comando se ejecuta **desde el directorio del proyecto**, que debe tener:

- Un archivo `context_inicial_<proyecto>.txt` (de ahí sale el nombre del proyecto).
- Un directorio `_temps/` (si no existe, el script lo crea).

Ejemplo:

```
mi-proyecto/
├── context_inicial_mi-proyecto.txt
└── _temps/
    ├── REQUERIMIENTO.txt   ← persistido, pre-cargado en la próxima corrida
    ├── DEV.txt             ← generado
    └── TESTING.txt         ← generado
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

1. Autodetecta el proyecto buscando `context_inicial_*.txt` en el directorio actual.
2. Abre tu editor (`vim` por defecto) sobre `_temps/REQUERIMIENTO.txt`:
   - La **primera vez** arranca con un header de instrucciones comentado.
   - En **corridas siguientes** ya viene pre-cargado con lo que escribiste antes (podés editar, agregar lo olvidado o reemplazarlo).
3. Escribís el requerimiento del sprint/iteración (multilínea, sin problema). Las líneas que empiezan con `#` se ignoran al generar los prompts.
4. Guardás y salís del editor (`:wq` en vim).
5. Se generan `_temps/DEV.txt` y `_temps/TESTING.txt` sobrescribiendo cualquier versión previa.
6. `_temps/REQUERIMIENTO.txt` queda guardado para la próxima corrida. Si querés arrancar en blanco, borralo manualmente.

Luego, en los agentes, basta decir algo como:

> *"leé `_temps/DEV.txt`"* (o `_temps/TESTING.txt` según el equipo)

Uso esperado de TESTING:

- En la primera pasada, si todavía no existe respuesta de DEV, TESTING debe hacer un análisis inicial independiente del requerimiento.
- Cuando DEV entregue su respuesta o implementación, TESTING debe contrastarla contra esa línea base y marcar coincidencias, omisiones, riesgos y bloqueantes reales.

Flujo recomendado de trabajo:

1. Ejecutar `prompts`, escribir el requerimiento y guardar.
2. Pasar en paralelo los prompts generados:
   - A DEV: `leé _temps/DEV.txt`
   - A TESTING: `leé _temps/TESTING.txt`
3. Esperar ambos outputs:
   - DEV entrega análisis inicial, criterios de aceptación, estrategia de validación y plan de implementación. En esta primera pasada no debe modificar código.
   - TESTING entrega su análisis inicial independiente como línea base.
4. Pasar el output de DEV a TESTING para que lo contraste contra su línea base.
5. Con el contraste de TESTING, pedir explícitamente a DEV que implemente o corrija los bloqueantes reales del requerimiento actual.
6. Si TESTING solo detecta mejoras opcionales, riesgos no bloqueantes o temas fuera de alcance, decidir si se implementa el plan de DEV, se cierra la iteración de análisis o se abre un requerimiento nuevo.

### Opciones

| Flag | Uso |
|------|-----|
| `--proyecto <nombre>` | Forzar el nombre del proyecto. Útil si hay varios `context_inicial_*.txt` en el directorio. |
| `--plantilla <ruta>`  | Usar otra plantilla en vez de `inicial.txt` del repo. |
| `-r`, `--requerimiento`, `--archivo` | Leer el requerimiento desde un archivo local (modo no interactivo, evita abrir el editor). |

Ejemplos:

```bash
prompts --proyecto chatbot
prompts --plantilla /ruta/a/otra-plantilla.txt
prompts --requerimiento mis_sprints/sprint1.txt
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
DEV
---------------------------------------------------------------------------------------------------------------------------------------------------
<contenido del prompt DEV, con context_inicial_AAAA.txt y <REQUERIMIENTO>>
```

Los separadores son líneas con 20+ guiones. Los headers `TESTING` y `DEV` se detectan entre separadores. Podés editar libremente el contenido de cada bloque sin tocar el script — los reemplazos siguen funcionando mientras se mantengan los placeholders `context_inicial_AAAA.txt` y `<REQUERIMIENTO>`.

---

## Principios de trabajo de los equipos

La plantilla incorpora cuatro ideas para reducir errores habituales de los
agentes de código:

- **Pensar antes de modificar:** explicitar supuestos, dudas y tradeoffs.
- **Simplicidad primero:** resolver el pedido sin abstracciones o flexibilidad
  especulativa.
- **Cambios quirúrgicos:** tocar únicamente lo necesario y respetar el estilo
  existente.
- **Ejecución orientada a objetivos:** definir criterios verificables y aportar
  evidencia concreta antes de cerrar.

DEV aplica estos principios al planificar e implementar. TESTING los usa como
criterios de revisión para detectar supuestos silenciosos, complejidad
innecesaria, cambios fuera de alcance y cierres sin validación suficiente.

Estas ideas están inspiradas en
[`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills),
publicado bajo licencia MIT. La redacción y adaptación al flujo DEV/TESTING de
este proyecto son propias.

---

## Casos de error manejados

- **No hay `context_inicial_*.txt`** en el directorio → mensaje claro y exit 1.
- **Hay varios** `context_inicial_*.txt` → lista los nombres y pide usar `--proyecto`.
- **Requerimiento vacío** (cerraste el editor sin escribir nada útil) → cancela sin generar archivos.
- **Plantilla sin secciones TESTING/DEV** → indica qué sección falta.
