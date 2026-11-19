# Transcrire

Glisse un MP4 dans une page, récupère le texte. La transcription tourne en local sur le Mac avec Whisper
(via faster-whisper) : aucun fichier n'est envoyé en ligne.

## Lancer

1. Télécharge le ZIP : https://github.com/PhytoPlancton/transcrire/archive/refs/heads/main.zip
   puis dans le Terminal, une seule fois : `chmod +x ~/Downloads/transcrire-main/Transcrire.command`
2. Double-clic sur **Transcrire.command**.
   - Au premier lancement, il installe Whisper dans `.venv` puis télécharge le modèle (~1,6 Go, modèle `large-v3-turbo`).
   - Si macOS bloque l'ouverture : clic droit > Ouvrir.
3. La page s'ouvre dans le navigateur : dépose ton fichier (MP4, MOV, MP3, M4A, WAV…), choisis la langue,
   puis copie le texte ou télécharge le `.txt`. Option « Horodatage » pour avoir `[mm:ss]` devant chaque phrase.

Pour arrêter : ferme la fenêtre du Terminal.

## Windows

1. Installe Python : ouvre PowerShell et tape `winget install Python.Python.3.12`, puis ferme et rouvre PowerShell.
2. Télécharge le ZIP : https://github.com/PhytoPlancton/transcrire/archive/refs/heads/main.zip, puis clic droit > Extraire tout.
3. Double-clic sur **Transcrire.bat** (si Windows affiche « Windows a protégé votre ordinateur » : Informations complémentaires > Exécuter quand même).

## Réglages

- Modèle : `large-v3-turbo` par défaut (précision proche du meilleur modèle, bien plus rapide).
  Pour aller plus vite : `WHISPER_MODEL=small ./Transcrire.command`. Pour le maximum de précision : `WHISPER_MODEL=large-v3`.
- Port : `TRANSCRIRE_PORT=9000` (8765 par défaut).

Prérequis : Python 3.9+ (`xcode-select --install` ou `brew install python`). Pas besoin d'ffmpeg, il est inclus.
