# calc

Calculadora TUI en Python (curses), sin dependencias externas. Interfaz de tres
zonas (display, historial/variables, teclado), temas de color, notación
semántica y actualización integrada.

## Requisitos

- Linux/macOS con `python3` (3.10+; `curses` incluido en la stdlib).
- `git` (para instalar/actualizar vía el instalador).
- No usa paquetes externos: `requirements.txt` está vacío.

## Instalación

```sh
curl -fsSL https://github.com/braiidev/calc/raw/main/install.sh | sh
```

El instalador (patrón A) clona el repo en `~/.config/calc/` y crea el wrapper
`/usr/local/bin/calc` (pide `sudo`). Si el destino ya existe y no es un repo,
lo respalda en `<destino>.bak`.

Manual:

```sh
git clone https://github.com/braiidev/calc.git ~/.config/calc
python3 ~/.config/calc/main.py
```

## Uso

```sh
calc                 # abre la TUI
calc --update        # actualiza (git pull) y sale
calc --check-update  # verifica si hay versión nueva
calc --reinstall     # reinstala corriendo install.sh
calc --uninstall     # desinstala (conserva config.json y variables.json)
calc --uninstall --purge  # desinstala y borra también los datos
calc --version
```

### Teclas

Modo normal (los dígitos `0-9`, `.`, operadores y la capa homerow se insertan
directo; las demás letras son comandos):

| Tecla | Acción |
|-------|--------|
| `w a s d` / flechas | mover la selección (teclado, historial, variables, ayuda) |
| `u i o` → `4 5 6` · `j k l` → `1 2 3` · `m` → `0` | capa numérica homerow (sin numpad; además de la fila `0-9` física) |
| `h` | toggle hints de capa homerow en el teclado |
| `tab` | cicla el foco: teclado → historial → variables |
| `enter` / `space` | evaluar (teclado) o traer el valor bajo el cursor (historial/variables) |
| `e` | entrar al modo edición (texto libre) |
| `esc` | limpiar el display |
| `x` | borrar bajo el cursor: display (teclado) o ítem (historial/variables) |
| `X` | borrar todo (historial/variables, pide confirmación) |
| `g` / `G` | ir al inicio / al final (historial/variables) |
| `c` | borrar hacia atrás (solo foco teclado) |
| `T` | ciclar el color del tema |
| `U` | aplicar actualización si hay, o verificarla |
| `?` | ayuda (`w`/`s` o flechas para desplazar, `?`/`esc` cierra) |
| `q` | salir |

Modo edición (`e`): todo carácter imprimible se inserta (sin espacios).

| Tecla | Acción |
|-------|--------|
| `enter` / `space` | evaluar/guardar y salir del modo edición |
| `esc` | salir sin evaluar |
| `←` / `→` | mover el cursor |
| `home` / `end` (o `ctrl-a` / `ctrl-e`) | inicio / fin |
| `backspace` | borrar antes del cursor |
| `del` | borrar después del cursor |

Para escribir identificadores (p. ej. `hola=5`, `raiz=sqrt(2)`) usá el modo
edición: en modo normal `w a s d` y `u i o j k l m` son atajos.

## Operadores y funciones

- Básicos: `+ - * /`, agrupar con `( )`.
- `**` potencia (asociativa a la derecha), `%` módulo, `!` factorial.
- `//` división entera, `sqrt(x)` raíz cuadrada, `root(x, n)` raíz n-ésima.
- Constantes: `pi`, `e` (no se pueden reasignar).
- Asignación: `x = 5`.

La notación semántica aparece en el historial: `[floor]`, `[sqrt]`, `[cbrt]`,
`[nroot]`.

## Variables e historial

- Al asignar (`x = 5`) el valor se guarda en `variables.json` (escritura
  atómica). Las asignaciones **no** van al historial.
- El historial se guarda en `history.json` (máximo 20 entradas) y se restaura
  al arrancar.
- Datos en `~/.config/calc/` junto al config.

## Configuración

`~/.config/calc/config.json`:

```json
{
  "theme": "frio",
  "glyphs": "auto",
  "live_notation": true,
  "status_bar": true,
  "colors": {}
}
```

- Temas: `mono`, `calido`, `frio` (por defecto), `contraste` — o `T` en la app.
- Override del archivo: variable `CALC_CONFIG`.
- Para desactivar el chequeo automático de actualizaciones: `CALC_NO_AUTO_UPDATE=1`.

## Desarrollo

```sh
python3 -m pytest -q          # suite de tests
python3 -m black tui tests main.py
python3 -m pyright
bash install.sh --version
```

Estructura: `main.py` (entrada y ciclo de vida), `calculator.py`
(lexer/parser/eval), `models/` (historial y variables), `tui/` (app, widgets,
tema, actualización, persistencia), `tests/`.
