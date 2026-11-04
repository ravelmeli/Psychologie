"""Recale le texte exact du script sur les horodatages d'une transcription Whisper.

    python3 -I align_script.py SCRIPT.md transcript_whisper.json transcript.json

Whisper se trompe parfois sur les noms propres et les nombres (« Kaneman »,
« version à la perte »). Ce script garde les mots du script (fiables) et leur
donne les temps de la voix (fiables) : les sous-titres sont donc corrects.
Le script est lu entre les deux premières lignes « --- » du fichier markdown.
"""
import difflib
import json
import re
import sys
import unicodedata


def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def script_words(path):
    text = open(path, encoding="utf-8").read()
    parts = re.split(r"^---\s*$", text, flags=re.M)
    body = parts[1] if len(parts) > 2 else text
    out, pending = [], ""
    for t in body.split():
        if not norm(t):
            if t in ("«", "“", "„"):  # guillemet ouvrant : se colle au mot suivant
                pending = t + "\u00a0"
            elif out:  # symbole isolé (« % », « € », « » ») : collé au mot précédent
                out[-1] += "\u00a0" + t
        else:
            out.append(pending + t)
            pending = ""
    return out


def main(script_md, whisper_json, out_json):
    sw = script_words(script_md)
    d = json.load(open(whisper_json))
    ww = []
    for w in d["words"]:  # jeton de ponctuation seul (« ? ») : on le fond dans le mot précédent
        if not norm(w["word"]) and ww:
            ww[-1] = {**ww[-1], "end": w["end"]}
        else:
            ww.append(w)
    a = [norm(w) for w in sw]
    b = [norm(w["word"]) for w in ww]
    out = [None] * len(sw)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1):
                out[i1 + k] = (ww[j1 + k]["start"], ww[j1 + k]["end"])
        elif tag in ("replace", "insert") or tag == "delete":
            if i2 > i1:
                if j2 > j1:
                    t0, t1 = ww[j1]["start"], ww[j2 - 1]["end"]
                else:  # mots du script sans équivalent : on les loge entre les voisins
                    prev = ww[j1 - 1]["end"] if j1 > 0 else 0.0
                    nxt = ww[j1]["start"] if j1 < len(ww) else d["duration"]
                    t0, t1 = prev, max(prev + 0.05 * (i2 - i1), nxt)
                n = i2 - i1
                for k in range(n):
                    out[i1 + k] = (t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n)
    words = [{"word": w, "start": round(t[0], 2), "end": round(t[1], 2)} for w, t in zip(sw, out)]
    segs = d.get("segments", [])
    json.dump({**d, "words": words, "segments": segs, "aligned_to_script": True}, open(out_json, "w"), ensure_ascii=False)
    exact = sum(1 for tag, *_ in sm.get_opcodes() if tag == "equal")
    print(f"{len(words)} mots du script alignés ({sm.ratio():.0%} identiques à Whisper)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
