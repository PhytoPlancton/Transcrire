#!/bin/bash
# Double-clic dans le Finder pour lancer Transcrire.
# Le premier lancement installe faster-whisper dans un environnement local (.venv).
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 est introuvable. Installe-le avec : xcode-select --install  (ou brew install python)"
  read -r -p "Entrée pour fermer..."
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Premier lancement : installation de Whisper (une à deux minutes)..."
  python3 -m venv .venv || exit 1
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -q -r requirements.txt || { read -r -p "Échec de l'installation. Entrée pour fermer..."; exit 1; }
fi

# Modèle Whisper large-v3-turbo, téléchargé une fois avec curl (barre de progression visible).
MODEL_DIR="$HOME/whisper-turbo"
if [ -z "$WHISPER_MODEL" ] && [ ! -s "$MODEL_DIR/model.bin" ]; then
  echo "Téléchargement du modèle Whisper (environ 1,6 Go, une seule fois)..."
  mkdir -p "$MODEL_DIR"
  for f in config.json preprocessor_config.json tokenizer.json vocabulary.json model.bin; do
    curl -L -# -C - -o "$MODEL_DIR/$f" "https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo/resolve/main/$f" \
      || { read -r -p "Échec du téléchargement ($f). Entrée pour fermer..."; exit 1; }
  done
fi
export WHISPER_MODEL="${WHISPER_MODEL:-$MODEL_DIR}"

exec .venv/bin/python transcrire.py
