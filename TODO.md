# TODO

## Doing
<!-- vacío -->

## Next

## Done
- [x] v0.9.9 - fix: install.sh compatible con `sh` (dash) para `curl | sh` (sin `set -o pipefail` en sh)
- [x] v0.9.8 - Historial persistente entre sesiones (`history.json`, carga/guarda con escritura atómica)
- [x] v0.9.7 - README (uso, teclas, operadores, variables, configuración y desarrollo)
- [x] v0.9.6 - Tests de install.sh en tests/ (+ guard de wrapper ajeno en install.sh --uninstall)
- [x] v0.9.5 - Cursor en modo edición (flechas/home/end/del, insertar en medio)
- [x] v0.9.4 - Bump de versión a v0.9 (main.py --version y install.sh)
- [x] v0.9.3 - Loop sin despertar en reposo (timeout solo durante el chequeo de update)
- [x] v0.9.2 - Pista `e editar` en la barra/ayuda y panel de ayuda desplazable con j/k
- [x] v0.9.1 - Modo edición (`e`): tipeo libre; enter/space evalúa y sale, esc sale sin evaluar; en modo normal las letras ya no se insertan (son comandos)
- [x] v0.8.4 - Auditoría: hardening de uninstall/wrapper, rama remota por defecto, validación de --purge, reinicio robusto
- [x] v0.8.3 - install.sh con flags (--update/--upgrade/--reinstall/--uninstall [--purge]/--version/--help)
- [x] v0.8.2 - Update + reinicio en la app: auto-check en background (CALC_NO_AUTO_UPDATE), tecla U, aviso en la barra de estado
- [x] v0.8.1 - Ciclo de vida en el CLI: `tui/update.py` + `--update`/`--check-update`/`--reinstall`/`--uninstall [--purge]`
- [x] v0.7.1 - Las asignaciones (`x = 5`) ya no van al historial; solo a variables
- [x] v0.7 - Persistencia de variables de usuario en `variables.json` (carga al arrancar, guarda al asignar/borrar)
- [x] v0.6.9 - fix: alinear la fila de funciones con el pad del teclado
- [x] v0.6.8 - Cierre de fase: VERSION v0.6 e install.sh testeado (overrides CALC_DIR/CALC_BIN)
- [x] v0.6.7 - Teclado por bloques (mockup B) + glifos Unicode con fallback
- [x] v0.6.6 - Layout adaptativo del medio (D/E/F) + scroll/overflow por panel + divisiones y títulos
- [x] v0.6.5 - Barra de estado: `<Modo> · «acción bajo cursor» · tab <destino> · ? · q`
- [x] v0.6.4 - Tema: T cicla solo color (mono/calido/frio/contraste), bordes automáticos por tamaño
- [x] v0.6.3 - fix: arranque en negro y resize (bucle KEY_RESIZE + tamaños chicos)
- [x] v0.6.2 - Display: barra de estado contextual + live notation
- [x] v0.6.1 - theme.py + config.json + tecla T (ciclar temas) y colores por rol
- [x] v0.5.3 - Leyenda toggleable de operadores/teclas con `?`
- [x] v0.5.2 - Notación semántica en historial (`[floor]`, `[sqrt]`, `[cbrt]`, `[nroot]`)
- [x] v0.5.1 - `//` división entera, `root(x, n)` raíz n-ésima, fuera `:`
- [x] v0.4 - Variables: builtins pi/e, asignación `x = 5` y panel de variables
- [x] v0.3.5 - `//` raíz n-ésima y `:` división entera (reemplazado en v0.5.1)
- [x] v0.3.4 - Historial: re-activar el mismo ítem ya no duplica la bandeja
- [x] v0.3.3 - Fix crash por KeyError y salida segura de curses
- [x] v0.3 - Historial session: guarda evaluaciones, scroll ↑/↓, limpia con `c`
- [x] v0.2 - Científica: `**` potencia, `%` módulo, `!` factorial, `sqrt()`, botón ANS
- [x] v0.1 - Básica: parser + layout display/teclado (TUI curses) + fixes de arranque y foco
