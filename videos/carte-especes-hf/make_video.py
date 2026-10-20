"""Pipeline complet : transcription → composition → contrôle → rendu.

    GROQ_API_KEY=gsk_... python3 -I make_video.py            # tout
    python3 -I make_video.py --skip-transcribe                # garde transcript.json
    python3 -I make_video.py --no-render                      # s'arrête après le contrôle

La clé Groq est lue dans l'environnement, jamais écrite sur le disque.
La voix off et le reste du contenu viennent de plan.json.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
HF = ["npx", "--yes", "hyperframes@0.8.177"]
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def run(cmd, **kw):
    print("→", " ".join(cmd[:4]), "…" if len(cmd) > 4 else "")
    subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def transcribe(plan):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        sys.exit("GROQ_API_KEY manquante (ou relancer avec --skip-transcribe).")
    out = ROOT / plan["transcript"]
    res = subprocess.run(
        [
            "curl", "-sS", "--fail-with-body", "-X", "POST", GROQ_URL,
            "-H", f"Authorization: Bearer {key}",
            "-F", f"file=@{ROOT / plan['voice']['src']}",
            "-F", "model=whisper-large-v3",
            "-F", "language=fr",
            "-F", "response_format=verbose_json",
            "-F", "timestamp_granularities[]=word",
            "-F", "timestamp_granularities[]=segment",
        ],
        capture_output=True, text=True,
    )
    if res.returncode:
        sys.exit(f"Échec de la transcription Groq : {res.stdout or res.stderr}")
    data = json.loads(res.stdout)
    out.write_text(json.dumps(data, ensure_ascii=False))
    print(f"Transcription : {len(data.get('words', []))} mots, {data.get('duration', 0):.2f} s")


def voice_duration(path):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(res.stdout.strip()), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-transcribe", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("-o", "--output", default="renders/video.mp4")
    args = ap.parse_args()

    plan = json.loads((ROOT / "plan.json").read_text())
    dur = voice_duration(ROOT / plan["voice"]["src"])
    if abs(dur - plan["voice"]["duration"]) > 0.05:
        print(f"⚠ La voix dure {dur} s mais plan.json indique {plan['voice']['duration']} s : à mettre à jour.")

    if not args.skip_transcribe:
        transcribe(plan)
    run([sys.executable, "-I", "build.py"])
    if (ROOT / plan.get("music", {}).get("src", "-")).exists():
        # Creuse la musique sous la voix (dips de fréquence + niveau), voir /hyperframes-audio
        run(["node", str(ROOT.parent.parent / ".claude/skills/hyperframes-audio/scripts/carve.mjs"),
             "--comp", "index.html", "--bed", "music", "--voice", "voice"])
    run(HF + ["check"])
    if not args.no_render:
        run(HF + ["render", "-o", args.output, "-q", "delivery"])
        print(f"Vidéo : {ROOT / args.output}")


if __name__ == "__main__":
    main()
