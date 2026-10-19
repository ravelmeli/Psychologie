"""Génère index.html à partir de transcript.json et du plan de poses.

Relancer après toute modification : python3 -I build.py
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
DURATION = 61.16

# Personnage : échelle commune, aligné sur les pieds
SCALE = 0.656
FEET_X = 268
BASELINE = 1420

# (début, pose) — une pose toutes les 2 à 4 s, comme dans les références
POSES = [
    (0.00, "04_reflechit"),
    (3.08, "06_inquiet"),
    (4.88, "03_designe_droite"),
    (7.14, "02_explique"),
    (11.14, "03_designe_droite"),
    (14.04, "06_inquiet"),
    (16.56, "12_tient_telephone"),
    (19.40, "08_rassure"),
    (22.14, "02_explique"),
    (26.50, "07_surpris"),
    (29.74, "13_compte_doigts"),
    (33.70, "02_explique"),
    (37.44, "03_designe_droite"),
    (39.34, "05_tente_achat"),
    (42.50, "14_enerve"),
    (45.72, "06_inquiet"),
    (48.24, "11_triste_decu"),
    (50.98, "02_explique"),
    (53.08, "03_designe_droite"),
    (56.54, "08_rassure"),
    (57.96, "01_neutre"),
]

# (début, texte) du bandeau
SECTIONS = [
    (0.00, "INTRO"),
    (7.14, "01 · LA DOULEUR"),
    (22.14, "02 · L'ÉTUDE"),
    (37.44, "03 · LE PIÈGE"),
    (50.98, "04 · LA SOLUTION"),
]


def pose_layout(name):
    im = Image.open(ROOT / "assets/poses" / f"{name}.png")
    alpha = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    x0, y0, x1, y1 = alpha.getbbox()
    feet = alpha.crop((0, int(y1 - (y1 - y0) * 0.05), im.width, y1)).getbbox()
    feet_cx = (feet[0] + feet[2]) / 2
    w, h = im.width * SCALE, im.height * SCALE
    return {
        "left": round(FEET_X - feet_cx * SCALE, 1),
        "top": round(BASELINE - y1 * SCALE, 1),
        "w": round(w, 1),
        "h": round(h, 1),
    }


# Corrections de la transcription pour coller au script
FIXES = {"quelles": "quelle", "dépenses": "dépense"}


def caption_chunks():
    words = json.loads((ROOT / "transcript.json").read_text())["words"]
    for w in words:
        w["word"] = FIXES.get(w["word"].strip(), w["word"])
    chunks, cur = [], []
    for w in words:
        cur.append({"w": w["word"].strip(), "s": round(w["start"], 2)})
        if len(cur) >= 4 or w["word"].strip()[-1:] in ",.?!:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else DURATION
        out.append({"start": c[0]["s"], "end": round(end, 2), "words": c})
    return out


def main():
    names = sorted({p for _, p in POSES})
    pose_imgs = "\n".join(
        f'        <img id="pose-{n}" class="pose" src="assets/poses/{n}.png" alt="" '
        f'style="left:{l["left"]}px;top:{l["top"]}px;width:{l["w"]}px;height:{l["h"]}px" />'
        for n in names
        for l in [pose_layout(n)]
    )
    chunks = caption_chunks()
    caps = "\n".join(
        f'        <div class="cap" id="cap-{i}"><p>'
        + " ".join(f'<span class="w" id="w-{i}-{j}">{w["w"]}</span>' for j, w in enumerate(c["words"]))
        + "</p></div>"
        for i, c in enumerate(chunks)
    )
    sections = "\n".join(
        f'            <span class="sec" id="sec-{i}">{t}</span>' for i, (_, t) in enumerate(SECTIONS)
    )
    html = (ROOT / "src/template.html").read_text()
    html = (
        html.replace("{{POSE_IMGS}}", pose_imgs)
        .replace("{{CAPTIONS}}", caps)
        .replace("{{SECTIONS}}", sections)
        .replace("{{DATA}}", json.dumps({
            "poses": POSES,
            "sections": [s for s, _ in SECTIONS],
            "caps": [{"start": c["start"], "end": c["end"], "words": [w["s"] for w in c["words"]]} for c in chunks],
        }))
        .replace("{{DURATION}}", str(DURATION))
    )
    (ROOT / "index.html").write_text(html)
    print(f"index.html : {len(names)} poses, {len(chunks)} blocs de sous-titres")


if __name__ == "__main__":
    main()
