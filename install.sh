#!/bin/bash
# Instalador patrón A: repo raw a ~/.config/calc/ + wrapper en /usr/local/bin/calc
# Uso: curl -fsSL <repo>/install.sh | sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/braiidev/calc.git}"
APP_DIR="$HOME/.config/calc"
BIN="/usr/local/bin/calc"

echo "== Calculadora TUI — instalador =="

# Prerrequisitos
for cmd in git python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: falta '$cmd'. Instálalo e inténtalo de nuevo."
        exit 1
    fi
done

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

# Crear wrapper (requiere sudo)
echo "Creando wrapper en $BIN (pedirá sudo)..."
sudo tee "$BIN" >/dev/null <<'EOF'
#!/bin/bash
exec python3 "$HOME/.config/calc/main.py" "$@"
EOF
sudo chmod +x "$BIN"

echo "Listo. Ejecuta 'calc' para abrir la calculadora."