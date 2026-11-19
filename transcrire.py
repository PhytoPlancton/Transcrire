"""Transcrire : glisser un MP4 (ou tout fichier audio/vidéo) dans la page, récupérer le texte.

Tout tourne en local sur le Mac, avec Whisper (faster-whisper). Rien n'est envoyé en ligne.
Lancement : double-clic sur « Transcrire.command », ou `python3 transcrire.py`.
"""

import json
import os
import sys
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import av
from faster_whisper import WhisperModel

# PyAV 15+ a supprimé l'option metadata_errors que faster-whisper passe encore à av.open.
_av_open = av.open


def _av_open_compat(*args, **kwargs):
    try:
        return _av_open(*args, **kwargs)
    except TypeError:
        kwargs.pop("metadata_errors", None)
        return _av_open(*args, **kwargs)


av.open = _av_open_compat

PORT = int(os.environ.get("TRANSCRIRE_PORT", "8765"))
MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v3-turbo")  # précis et ~8x plus rapide que large-v3

_model = None
_model_lock = threading.Lock()
jobs = {}  # id -> {"status", "progress", "text", "error", "name"}


def get_model():
    global _model
    with _model_lock:
        if _model is None:
            print(f"Chargement du modèle Whisper « {MODEL_NAME} » (premier lancement : téléchargement)...")
            _model = WhisperModel(
                MODEL_NAME, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4
            )
        return _model


def fmt_ts(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def run_job(job_id, path, language):
    job = jobs[job_id]
    try:
        job["status"] = "chargement du modèle"
        model = get_model()
        job["status"] = "transcription"
        segments, info = model.transcribe(
            path, language=language or None, vad_filter=True, beam_size=5
        )
        lines, timed = [], []
        for seg in segments:
            text = seg.text.strip()
            lines.append(text)
            timed.append(f"[{fmt_ts(seg.start)}] {text}")
            if info.duration:
                job["progress"] = min(99, int(seg.end / info.duration * 100))
            job["text"] = "\n".join(lines)
            job["timed"] = "\n".join(timed)
        job["language"] = info.language
        job["progress"] = 100
        job["status"] = "terminé"
    except Exception as e:  # noqa: BLE001
        job["status"] = "erreur"
        job["error"] = str(e)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Transcrire</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--fg:#1d1c1a;--muted:#77736b;--line:#dedad2;--accent:#2f6fec}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#1f1f1d;--fg:#ecebe7;--muted:#9a968e;--line:#33322f;--accent:#6c9cff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,sans-serif}
main{max-width:760px;margin:0 auto;padding:40px 16px}
h1{font-size:22px;margin:0 0 4px}p.sub{color:var(--muted);margin:0 0 24px}
#drop{border:2px dashed var(--line);border-radius:14px;background:var(--card);padding:48px 16px;text-align:center;cursor:pointer;transition:.15s}
#drop.over{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,var(--card))}
#drop strong{display:block;font-size:17px;margin-bottom:4px}#drop span{color:var(--muted)}
.row{display:flex;gap:12px;align-items:center;margin:14px 0;flex-wrap:wrap}
select,button{font:inherit;padding:7px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;flex:1;min-width:120px}.bar>i{display:block;height:100%;width:0;background:var(--accent);transition:width .3s}
#status{color:var(--muted);font-size:14px}
textarea{width:100%;min-height:340px;padding:14px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg);font:14px/1.55 ui-monospace,Menlo,monospace;resize:vertical}
.hidden{display:none}
</style></head><body><main>
<h1>Transcrire</h1>
<p class="sub">Dépose un MP4 (ou MOV, MP3, M4A, WAV…). La transcription se fait en local avec Whisper.</p>
<div id="drop"><strong>Glisse ton fichier ici</strong><span>ou clique pour le choisir</span>
<input id="file" type="file" accept="video/*,audio/*" class="hidden"></div>
<div class="row"><label>Langue <select id="lang"><option value="">Détection auto</option><option value="fr" selected>Français</option><option value="en">Anglais</option><option value="es">Espagnol</option><option value="de">Allemand</option><option value="it">Italien</option></select></label>
<label><input type="checkbox" id="ts"> Horodatage</label></div>
<div id="prog" class="row hidden"><div class="bar"><i id="fill"></i></div><span id="status"></span></div>
<div id="out" class="hidden"><textarea id="text" readonly></textarea>
<div class="row"><button class="primary" id="copy">Copier</button><button id="dl">Télécharger .txt</button></div></div>
</main><script>
const $=id=>document.getElementById(id);let job=null,name="transcription";
const drop=$("drop"),file=$("file");
drop.onclick=()=>file.click();file.onchange=()=>file.files[0]&&send(file.files[0]);
["dragenter","dragover"].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add("over")}));
["dragleave","drop"].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove("over")}));
drop.addEventListener("drop",ev=>ev.dataTransfer.files[0]&&send(ev.dataTransfer.files[0]));
$("ts").onchange=render;
async function send(f){name=f.name.replace(/\.[^.]+$/,"");$("prog").classList.remove("hidden");$("out").classList.add("hidden");
 $("fill").style.width="0";$("status").textContent="Envoi de "+f.name+"…";
 const r=await fetch("/upload?lang="+$("lang").value+"&name="+encodeURIComponent(f.name),{method:"POST",body:f});
 const d=await r.json();poll(d.id)}
let last={};
async function poll(id){const d=await (await fetch("/job/"+id)).json();last=d;
 $("fill").style.width=(d.progress||0)+"%";$("status").textContent=d.status+(d.progress?" · "+d.progress+"%":"");
 if(d.text){$("out").classList.remove("hidden");render()}
 if(d.status==="erreur"){$("status").textContent="Erreur : "+d.error;return}
 if(d.status!=="terminé")setTimeout(()=>poll(id),1000)}
function render(){$("text").value=($("ts").checked?last.timed:last.text)||""}
$("copy").onclick=()=>{navigator.clipboard.writeText($("text").value);$("copy").textContent="Copié ✓";setTimeout(()=>$("copy").textContent="Copier",1500)};
$("dl").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([$("text").value],{type:"text/plain"}));a.download=name+".txt";a.click()};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/job/"):
            job = jobs.get(self.path[5:])
            self._json(job or {"status": "erreur", "error": "job inconnu"}, 200 if job else 404)
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.path.startswith("/upload"):
            return self.send_error(404)
        from urllib.parse import parse_qs, urlparse

        q = parse_qs(urlparse(self.path).query)
        lang = (q.get("lang") or [""])[0]
        name = (q.get("name") or ["fichier"])[0]
        ext = os.path.splitext(name)[1] or ".mp4"
        length = int(self.headers.get("Content-Length", 0))
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, "wb") as f:
            remaining = length
            while remaining > 0:
                chunk = self.rfile.read(min(1 << 20, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        job_id = uuid.uuid4().hex
        jobs[job_id] = {"status": "en attente", "progress": 0, "text": "", "timed": "", "name": name}
        threading.Thread(target=run_job, args=(job_id, path, lang), daemon=True).start()
        self._json({"id": job_id})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Transcrire tourne sur {url}  (Ctrl+C pour arrêter)")
    threading.Thread(target=get_model, daemon=True).start()  # précharge le modèle
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
