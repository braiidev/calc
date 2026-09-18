#!/bin/bash
# Instalador patrón A: repo raw a ~/.config/calc/ + wrapper en /usr/local/bin/calc
# Uso: curl -fsSL <repo>/install.sh | sh
#      bash install.sh [--update|--upgrade|--reinstall|--uninstall [--purge]|--version]
#
# --uninstall conserva config.json y variables.json; agregá --purge para borrarlos.

# Compatible con `sh` (dash). `pipefail` solo existe en bash, se activa si está.
set -eu
if [ -n "${BASH_VERSION:-}" ]; then
    set -o pipefail
fi

REPO_URL="${REPO_URL:-https://github.com/braiidev/calc.git}"
APP_DIR="${CALC_DIR:-$HOME/.config/calc}"
BIN="${CALC_BIN:-/usr/local/bin/calc}"

ACTION="install"
PURGE=0
for arg in "$@"; do
    case "$arg" in
        --update | --upgrade) ACTION="update" ;;
        --reinstall) ACTION="install" ;;
        --uninstall) ACTION="uninstall" ;;
        --purge) PURGE=1 ;;
        --version) ACTION="version" ;;
        -h | --help) ACTION="help" ;;
        *)
            echo "Argumento desconocido: $arg" >&2
            exit 2
            ;;
    esac
done

if [ "$ACTION" = "version" ]; then
    echo "calc-installer v1.0.0"
    exit 0
fi

if [ "$ACTION" = "help" ]; then
    echo "uso: install.sh [--update|--upgrade|--reinstall|--uninstall [--purge]|--version]"
    echo "  (sin flags)    instala o actualiza y crea el wrapper"
    echo "  --update       solo actualiza el repo (git pull --ff-only)"
    echo "  --reinstall    reinstala (clonar/pull + wrapper)"
    echo "  --uninstall    quita wrapper y código; conserva config.json/variables.json"
    echo "  --purge        con --uninstall: borra también los datos"
    exit 0
fi

# Prerrequisitos
for cmd in git python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: falta '$cmd'. Instálalo e inténtalo de nuevo."
        exit 1
    fi
done

if [ "$ACTION" = "uninstall" ]; then
    echo "== Calculadora TUI — desinstalador =="
    case "$APP_DIR" in
        / | "$HOME")
            echo "Error: APP_DIR inseguro ($APP_DIR); se aborta por seguridad." >&2
            exit 1
            ;;
    esac
    if [ ! -f "$APP_DIR/main.py" ] || [ ! -f "$APP_DIR/install.sh" ]; then
        echo "Error: no parece una instalación en $APP_DIR." >&2
        exit 1
    fi
    if [ -e "$BIN" ]; then
        if ! command -v sudo >/dev/null 2>&1; then
            echo "Aviso: falta 'sudo'; no se pudo quitar $BIN. Borralo a mano." >&2
        elif ! grep -q "main.py" "$BIN" 2>/dev/null; then
            echo "Aviso: $BIN no parece el wrapper de calc; no se borra." >&2
        else
            echo "Eliminando wrapper $BIN (pedirá sudo)..."
            sudo rm -f "$BIN"
        fi
    fi
    if [ "$PURGE" = "1" ]; then
        echo "Eliminando instalación y datos: $APP_DIR"
        rm -rf "$APP_DIR"
    else
        TMP="$(mktemp -d)"
        trap 'rm -rf "$TMP"' EXIT
        for f in config.json variables.json; do
            if [ -f "$APP_DIR/$f" ]; then
                cp -p "$APP_DIR/$f" "$TMP/"
            fi
        done
        rm -rf "$APP_DIR"
        mkdir -p "$APP_DIR"
        for f in "$TMP"/*; do
            if [ -e "$f" ]; then
                mv "$f" "$APP_DIR/"
            fi
        done
        rmdir "$TMP" 2>/dev/null || true
        echo "Datos conservados en $APP_DIR (config.json/variables.json)"
    fi
    echo "Listo. calc desinstalado."
    exit 0
fi

if [ "$ACTION" = "update" ]; then
    echo "== Calculadora TUI — actualización =="
    if [ ! -d "$APP_DIR/.git" ]; then
        echo "Error: $APP_DIR no es un repo git; usá --reinstall." >&2
        exit 1
    fi
    echo "Actualizando repo en $APP_DIR..."
    git -C "$APP_DIR" pull --ff-only
    echo "Listo. Actualizado."
    exit 0
fi

echo "== Calculadora TUI — instalador =="

# (Re)clonar o pull
if [ -d "$APP_DIR/.git" ]; then
    echo "Actualizando repo en $APP_DIR..."
    git -C "$APP_DIR" pull --ff-only
else
    if [ -e "$APP_DIR" ]; then
        echo "Moviendo $APP_DIR a $APP_DIR.bak"
        mv "$APP_DIR" "$APP_DIR.bak"
    fi
    echo "Clonando $REPO_URL..."
    git clone "$REPO_URL" "$APP_DIR"
fi

# Verificar que curses existe
if ! python3 -c "import curses" >/dev/null 2>&1; then
    echo "Error: el módulo 'curses' no está disponible en este Python."
    exit 1
fi

# Crear wrapper (requiere sudo). Se fija la ruta resuelta de $APP_DIR para que
# el comando funcione sin depender de variables de entorno en runtime.
if ! command -v sudo >/dev/null 2>&1; then
    echo "Error: falta 'sudo' para crear el wrapper en $BIN." >&2
    exit 1
fi
echo "Creando wrapper en $BIN (pedirá sudo)..."
sudo mkdir -p "$(dirname "$BIN")"
sudo tee "$BIN" >/dev/null <<EOF
#!/bin/bash
exec python3 "$APP_DIR/main.py" "\$@"
EOF
sudo chmod +x "$BIN"

echo "Listo. Ejecuta 'calc' para abrir la calculadora."
