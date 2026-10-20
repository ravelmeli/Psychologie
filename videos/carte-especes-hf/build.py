"""Génère la composition HyperFrames à partir de plan.json.

    python3 -I build.py

Sorties : index.html (racine) et compositions/*.html (une sous-composition
par carte, plus décor, personnage, bandeau et sous-titres).
Pour une nouvelle vidéo, ne modifier que plan.json (et les médias).
"""
import html
import json
import re
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
SFX_LIB = ROOT.parent.parent / ".claude/skills/media-use/audio/assets/sfx"

W, H = 1080, 1920
# Personnage : échelle commune, aligné sur les pieds
SCALE = 0.68
FEET_X = 228
BASELINE = 1470
# Cartes : dans la zone sûre titre (80 %), à gauche de la colonne d'icônes TikTok
CARD_LEFT, CARD_TOP, CARD_W = 558, 330, 414

COLORS = {
    "red": "#d9453b",
    "green": "#3f8f4a",
    "dark": "#3f6b3c",
    "light": "#8db580",
    "yellow": "#f2b84b",
}

SUB = """<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
  </head>
  <body>
    <template>
      <style>
        #%ID% {
          position: absolute;
          inset: 0;
          font-family: Montserrat, sans-serif;
          color: #16140f;
        }
%CSS%
      </style>
      <div id="%ID%" data-composition-id="%ID%" data-width="1080" data-height="1920">
%HTML%
      </div>
      <script>
        (() => {
          const tl = gsap.timeline({ paused: true });
%JS%
          window.__timelines["%ID%"] = tl;
        })();
      </script>
    </template>
  </body>
</html>
"""

JS_HELPERS = """          const pop = (s, t) =>
            tl.fromTo(s, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2.2)" }, t);
          const stamp = (s, t, r) =>
            tl.fromTo(s, { opacity: 0, scale: 1.8, rotation: r }, { opacity: 1, scale: 1, rotation: r, duration: 0.28, ease: "power3.in" }, t);"""

CARD_CSS = """        #%ID% .card {
          position: absolute;
          left: %LEFT%px;
          top: %TOP%px;
          width: %W%px;
          padding: 40px 34px;
          background: #ffffff;
          border: 2px solid #ece6d8;
          border-radius: 36px;
          box-shadow: 0 26px 60px rgba(40, 35, 20, 0.16);
          display: flex;
          flex-direction: column;
          gap: 28px;
        }
        #%ID% .card.center { align-items: center; text-align: center; top: 420px; }
        #%ID% .hid { opacity: 0; }
        #%ID% .label {
          font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 22px;
          letter-spacing: 0.12em; text-transform: uppercase; color: #3f6b3c;
        }
        #%ID% .title { font-weight: 900; font-size: 60px; line-height: 1.04; letter-spacing: -0.02em; }
        #%ID% .hl { position: relative; display: inline-block; }
        #%ID% .hlt { position: relative; }
        #%ID% .mark {
          position: absolute; left: -6px; right: -6px; bottom: 4px; height: 24px;
          background: #f2b84b; border-radius: 6px; transform-origin: left center;
        }
        #%ID% .chips { display: flex; gap: 14px; flex-wrap: wrap; }
        #%ID% .chips.col { flex-direction: column; }
        #%ID% .pill {
          align-self: flex-start; font-family: "JetBrains Mono", monospace; font-weight: 700;
          font-size: 24px; letter-spacing: 0.04em; padding: 14px 20px; border-radius: 30px;
          background: #f4f1ea; color: #16140f; white-space: nowrap;
        }
        #%ID% .pill.red { background: #d9453b; color: #ffffff; }
        #%ID% .pill.green { background: #3f6b3c; color: #ffffff; }
        #%ID% .duel { display: flex; align-items: center; justify-content: space-between; height: 130px; }
        #%ID% .note, #%ID% .bankcard { width: 160px; height: 104px; border-radius: 14px; }
        #%ID% .note {
          background: #4f7d4b; border: 5px solid #3f6b3c; color: #ffffff; font-weight: 900; font-size: 40px;
          display: flex; align-items: center; justify-content: center;
        }
        #%ID% .bankcard { background: linear-gradient(135deg, #1f3a2c, #3f6b3c); padding: 16px 18px; }
        #%ID% .bankcard .chip { width: 40px; height: 30px; border-radius: 6px; background: #f2b84b; }
        #%ID% .bankcard .pan {
          margin-top: 26px; font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 15px;
          letter-spacing: 0.06em; color: #ffffff; white-space: nowrap;
        }
        #%ID% .vs {
          width: 58px; height: 58px; border-radius: 29px; background: #16140f; color: #ffffff;
          font-weight: 900; font-size: 22px; display: flex; align-items: center; justify-content: center;
        }
        #%ID% .meter-top {
          display: flex; justify-content: space-between; font-family: "JetBrains Mono", monospace;
          font-weight: 700; font-size: 22px; letter-spacing: 0.1em; margin-bottom: 14px;
        }
        #%ID% .bar { height: 38px; border-radius: 19px; background: #f4f1ea; overflow: hidden; }
        #%ID% .fill { width: 100%; height: 100%; border-radius: 19px; transform-origin: left center; }
        #%ID% .stamp {
          align-self: center; font-weight: 900; font-size: 34px; letter-spacing: 0.02em; text-align: center;
          padding: 14px 20px; border: 6px solid #d9453b; color: #c0352c; border-radius: 14px;
        }
        #%ID% .stamp.yellow { border-color: #c98a12; color: #16140f; background: #f2b84b; }
        #%ID% .chart { position: relative; height: 420px; display: flex; align-items: flex-end; justify-content: center; gap: 60px; }
        #%ID% .col { display: flex; flex-direction: column; align-items: center; gap: 14px; }
        #%ID% .barv { width: 130px; height: 340px; border-radius: 18px 18px 6px 6px; transform-origin: center bottom; }
        #%ID% .cl { font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 22px; letter-spacing: 0.08em; }
        #%ID% .badge {
          position: absolute; right: 10px; top: 0; width: 120px; height: 120px; border-radius: 60px;
          background: #f2b84b; display: flex; align-items: center; justify-content: center;
          font-weight: 900; font-size: 50px;
        }
        #%ID% .rows { display: flex; flex-direction: column; gap: 26px; }
        #%ID% .row { display: flex; align-items: center; gap: 20px; font-weight: 700; font-size: 38px; line-height: 1.15; }
        #%ID% .num {
          flex: none; width: 62px; height: 62px; border-radius: 31px; background: #3f6b3c; color: #ffffff;
          display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 32px;
        }
        #%ID% .num.yellow { background: #f2b84b; color: #16140f; }
        #%ID% .buy {
          align-self: stretch; text-align: center; font-weight: 900; font-size: 46px; letter-spacing: 0.04em;
          padding: 28px 0; border-radius: 24px; background: #f2b84b; box-shadow: 0 10px 0 #c98a12;
        }
        #%ID% .line {
          display: flex; justify-content: space-between; font-family: "JetBrains Mono", monospace;
          font-weight: 700; font-size: 28px; padding-bottom: 14px; border-bottom: 2px dashed #ece6d8;
        }
        #%ID% .total { display: flex; justify-content: space-between; gap: 16px; font-weight: 900; font-size: 42px; color: #c0352c; white-space: nowrap; }
        #%ID% .sub { font-weight: 700; font-size: 38px; line-height: 1.2; }
        #%ID% .cta {
          display: flex; align-items: center; gap: 14px; padding: 16px 22px; border-radius: 40px;
          background: #16140f; color: #ffffff; font-weight: 900; font-size: 20px; white-space: nowrap;
        }
        #%ID% .arrow {
          width: 18px; height: 18px; border-right: 5px solid #f2b84b; border-bottom: 5px solid #f2b84b;
          transform: rotate(45deg); margin-top: -8px;
        }"""


def esc(s):
    return html.escape(s, quote=False)


def fmt(t):
    return f"{max(t, 0):.3f}".rstrip("0").rstrip(".") or "0"


# ---------------------------------------------------------------- cartes


def render_card(card, is_last):
    cid, start, end = card["id"], card["start"], card["end"]
    dur = end - start
    L = lambda t: fmt(t - start)
    later = lambda t: t is not None and t > start + 0.05
    parts, js = [], [JS_HELPERS]
    n = 0

    def nid():
        nonlocal n
        n += 1
        return f"{cid}-e{n}"

    def hidden_pop(sel_id, at):
        if later(at):
            js.append(f'          pop("#{sel_id}", {L(at)});')
            return " hid"
        return ""

    for item in card["items"]:
        t = item["type"]
        if t == "label":
            parts.append(f'<div class="label">{esc(item["text"])}</div>')
        elif t == "title":
            i = nid()
            size = f' style="font-size:{item["size"]}px"' if "size" in item else ""
            out, marks = [], []
            for k, seg in enumerate(re.split(r"\*\*(.+?)\*\*", item["text"])):
                if k % 2:
                    m = f"{i}-m{k}"
                    marks.append(m)
                    out.append(f'<span class="hl"><span class="mark" id="{m}"></span><span class="hlt">{esc(seg)}</span></span>')
                else:
                    out.append(esc(seg))
            cls = hidden_pop(i, item.get("at"))
            parts.append(f'<div class="title{cls}" id="{i}"{size}>{"".join(out)}</div>')
            if later(item.get("mark_at")):
                for m in marks:
                    js.append(
                        f'          tl.fromTo("#{m}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.4, ease: "power2.out" }}, {L(item["mark_at"])});'
                    )
        elif t == "duel":
            i = nid()
            parts.append(
                f'<div class="duel"><div class="note" id="{i}-note">{esc(item["note"])}</div>'
                f'<div class="vs">VS</div>'
                f'<div class="bankcard" id="{i}-card"><div class="chip"></div><div class="pan">•••• 4021</div></div></div>'
            )
            s = L(item["switch_at"])
            js.append(
                f'          tl.fromTo("#{i}-note", {{ opacity: 1, scale: 1 }}, {{ opacity: 0.35, scale: 0.9, duration: 0.3, immediateRender: false }}, {s});'
            )
            js.append(
                f'          tl.fromTo("#{i}-card", {{ scale: 1.18 }}, {{ scale: 1, duration: 0.45, ease: "back.out(2.5)", immediateRender: false }}, {s});'
            )
        elif t == "pills":
            pills = []
            for p in item["items"]:
                i = nid()
                color = f' {p["color"]}' if "color" in p else ""
                cls = hidden_pop(i, p.get("at"))
                pills.append(f'<div class="pill{color}{cls}" id="{i}">{esc(p["text"])}</div>')
            col = " col" if item.get("dir") == "col" else ""
            parts.append(f'<div class="chips{col}">{"".join(pills)}</div>')
        elif t == "meter":
            i = nid()
            c_to = COLORS[item["color"]]
            c_from = COLORS[item.get("color_from", item["color"])]
            parts.append(
                f'<div><div class="meter-top"><span>{esc(item["label"])}</span><span>{esc(item["tag"])}</span></div>'
                f'<div class="bar"><div class="fill" id="{i}"></div></div></div>'
            )
            js.append(
                f'          tl.fromTo("#{i}", {{ scaleX: {item["from"]}, backgroundColor: "{c_from}" }}, '
                f'{{ scaleX: {item["to"]}, backgroundColor: "{c_to}", duration: 0.8, ease: "power2.out" }}, {L(item["at"])});'
            )
        elif t == "stamp":
            i = nid()
            yellow = item.get("color") == "yellow"
            parts.append(f'<div class="stamp{" yellow" if yellow else ""} hid" id="{i}">{esc(item["text"])}</div>')
            js.append(f'          stamp("#{i}", {L(item["at"])}, {-4 if yellow else -5});')
        elif t == "bars":
            cols = []
            for b in item["items"]:
                i = nid()
                color = COLORS[b.get("color", "dark")]
                cols.append(
                    f'<div class="col"><div class="barv" id="{i}" style="background:{color}"></div>'
                    f'<div class="cl">{esc(b["label"])}</div></div>'
                )
                js.append(
                    f'          tl.fromTo("#{i}", {{ scaleY: 0 }}, {{ scaleY: {b["to"]}, duration: 0.6, ease: "power2.out" }}, {L(b["at"])});'
                )
                if "grow_to" in b:
                    js.append(
                        f'          tl.fromTo("#{i}", {{ scaleY: {b["to"]} }}, {{ scaleY: {b["grow_to"]}, duration: 0.9, '
                        f'ease: "power3.out", immediateRender: false }}, {L(b["grow_at"])});'
                    )
            badge = ""
            if "badge" in item:
                i = nid()
                badge = f'<div class="badge hid" id="{i}">{esc(item["badge"]["text"])}</div>'
                js.append(f'          pop("#{i}", {L(item["badge"]["at"])});')
            parts.append(f'<div class="chart">{"".join(cols)}{badge}</div>')
        elif t == "rows":
            rows = []
            numcls = " yellow" if item.get("num") == "yellow" else ""
            for k, r in enumerate(item["items"], 1):
                i = nid()
                cls = hidden_pop(i, r.get("at"))
                rows.append(
                    f'<div class="row{cls}" id="{i}"><span class="num{numcls}">{k}</span><span>{esc(r["text"])}</span></div>'
                )
            parts.append(f'<div class="rows">{"".join(rows)}</div>')
        elif t == "button":
            i = nid()
            cls = hidden_pop(i, item.get("at"))
            parts.append(f'<div class="buy{cls}" id="{i}">{esc(item["text"])}</div>')
            if "pulse_at" in item:
                reps = int((item["pulse_until"] - item["pulse_at"]) / 0.35)
                reps -= 1 - reps % 2  # impair : finit à l'échelle 1
                js.append(
                    f'          tl.fromTo("#{i}", {{ scale: 1 }}, {{ scale: 1.06, duration: 0.35, ease: "sine.inOut", '
                    f'yoyo: true, repeat: {reps}, immediateRender: false }}, {L(item["pulse_at"])});'
                )
        elif t == "receipt":
            for k, (left, right) in enumerate(item["lines"]):
                i = nid()
                parts.append(f'<div class="line hid" id="{i}"><span>{esc(left)}</span><span>{esc(right)}</span></div>')
                js.append(
                    f'          tl.fromTo("#{i}", {{ opacity: 0, x: 30 }}, {{ opacity: 1, x: 0, duration: 0.25, ease: "power2.out" }}, '
                    f'{L(item["start"] + k * item["step"])});'
                )
            tot = item["total"]
            i = nid()
            parts.append(f'<div class="total hid" id="{i}"><span>{esc(tot["left"])}</span><span>{esc(tot["right"])}</span></div>')
            js.append(f'          stamp("#{i}", {L(tot["at"])}, 0);')
        elif t == "sub":
            i = nid()
            cls = hidden_pop(i, item.get("at"))
            parts.append(f'<div class="sub{cls}" id="{i}">{esc(item["text"])}</div>')
        elif t == "cta":
            i = nid()
            cls = hidden_pop(i, item.get("at"))
            parts.append(f'<div class="cta{cls}" id="{i}"><span>{esc(item["text"])}</span><span class="arrow"></span></div>')
            js.append(
                f'          tl.fromTo("#{i}", {{ y: 0 }}, {{ y: -10, duration: 0.45, ease: "sine.inOut", yoyo: true, repeat: 5, '
                f'immediateRender: false }}, {L(item["at"] + 0.4)});'
            )
        else:
            raise ValueError(f"type de carte inconnu : {t}")

    card_sel = f"#{cid}-card"
    if start > 0:
        js.append(
            f'          tl.fromTo("{card_sel}", {{ opacity: 0, x: 90, scale: 0.94 }}, '
            f'{{ opacity: 1, x: 0, scale: 1, duration: 0.45, ease: "back.out(1.6)" }}, 0.02);'
        )
    if "shake_at" in card:
        js.append(
            f'          tl.fromTo("{card_sel}", {{ x: -16 }}, {{ x: 0, duration: 0.5, ease: "elastic.out(1.2, 0.3)", '
            f'immediateRender: false }}, {L(card["shake_at"])});'
        )
    if not is_last:
        js.append(
            f'          tl.fromTo("{card_sel}", {{ opacity: 1, x: 0 }}, {{ opacity: 0, x: -70, duration: 0.25, ease: "power2.in", '
            f'immediateRender: false }}, {fmt(dur - 0.25)});'
        )

    center = " center" if card.get("center") else ""
    body = "\n".join(f"          {p}" for p in parts)
    markup = f'        <div class="card{center}" id="{cid}-card">\n{body}\n        </div>'
    css = (
        CARD_CSS.replace("%LEFT%", str(CARD_LEFT))
        .replace("%TOP%", str(CARD_TOP))
        .replace("%W%", str(CARD_W))
    )
    return sub(cid, css, markup, "\n".join(js))


def sub(cid, css, markup, js):
    return (
        SUB.replace("%CSS%", css)
        .replace("%HTML%", markup)
        .replace("%JS%", js)
        .replace("%ID%", cid)
    )


# ---------------------------------------------------------------- décor


def render_decor():
    css = """        #decor .wall {
          position: absolute; inset: 0;
          background:
            radial-gradient(ellipse 60% 35% at 22% 18%, rgba(255, 244, 214, 0.9), transparent 70%),
            linear-gradient(180deg, #f6f1e7 0%, #efe7d8 100%);
        }
        #decor .light {
          position: absolute; left: -120px; top: -200px; width: 520px; height: 1700px;
          background: linear-gradient(180deg, rgba(255, 250, 235, 0.55), rgba(255, 250, 235, 0));
          transform: rotate(-24deg); transform-origin: top left;
        }
        #decor .panel {
          position: absolute; left: 0; right: 0; top: 1180px; height: 240px;
          background:
            repeating-linear-gradient(90deg, transparent 0 176px, rgba(120, 100, 70, 0.12) 176px 180px),
            linear-gradient(180deg, #e9e0cf, #e2d7c3);
          border-top: 6px solid #d9ccb5;
        }
        #decor .base { position: absolute; left: 0; right: 0; top: 1420px; height: 22px; background: #cdbd9f; }
        #decor .floor {
          position: absolute; left: 0; right: 0; top: 1442px; bottom: 0;
          background:
            repeating-linear-gradient(0deg, rgba(110, 75, 40, 0.10) 0 3px, transparent 3px 84px),
            linear-gradient(180deg, #e8d6b8, #efe2ca);
        }
        #decor .shelf { position: absolute; left: 560px; top: 1240px; width: 400px; height: 16px; background: #b88f5e; border-radius: 4px; }
        #decor .book { position: absolute; width: 34px; border-radius: 4px 4px 0 0; }
        #decor .jar {
          position: absolute; left: 860px; top: 1156px; width: 70px; height: 84px; border-radius: 14px 14px 18px 18px;
          background: rgba(255, 255, 255, 0.55); border: 4px solid rgba(120, 100, 70, 0.25);
        }
        #decor .coin { position: absolute; width: 34px; height: 12px; border-radius: 50%; background: #e0a93a; border: 2px solid #c98a12; }
        #decor .plant { position: absolute; left: 60px; top: 1236px; width: 120px; height: 190px; }
        #decor .pot { position: absolute; left: 22px; bottom: 0; width: 76px; height: 70px; background: #c97b4a; border-radius: 6px 6px 18px 18px; }
        #decor .leaf { position: absolute; width: 46px; height: 100px; border-radius: 50%; background: #6f9a62; transform-origin: bottom center; }
        #decor .vignette {
          position: absolute; inset: 0;
          background: radial-gradient(ellipse 85% 75% at 50% 45%, transparent 60%, rgba(60, 45, 25, 0.16) 100%);
        }"""
    books = [(590, 120, "#3f6b3c"), (628, 104, "#f2b84b"), (666, 130, "#d9453b"), (704, 96, "#8db580"), (742, 116, "#1f3a2c")]
    book_html = "".join(
        f'<div class="book" style="left:{x}px;top:{1240 - h}px;height:{h}px;background:{c}"></div>'
        for x, h, c in books
    )
    coins = "".join(
        f'<div class="coin" style="left:{878 + dx}px;top:{1214 - k * 10}px"></div>'
        for k, dx in enumerate([0, 4, -2, 3])
    )
    leaves = "".join(
        f'<div class="leaf" style="left:{x}px;top:{y}px;transform:rotate({r}deg)"></div>'
        for x, y, r in [(10, 30, -35), (38, 0, -8), (64, 22, 24), (36, 40, 6)]
    )
    markup = (
        '        <div class="wall"></div>\n'
        '        <div class="light"></div>\n'
        '        <div class="panel"></div>\n'
        '        <div class="shelf"></div>\n'
        f"        {book_html}\n"
        f'        <div class="jar"></div>{coins}\n'
        f'        <div class="plant">{leaves}<div class="pot"></div></div>\n'
        '        <div class="base"></div>\n'
        '        <div class="floor"></div>\n'
        '        <div class="vignette"></div>'
    )
    return sub("decor", css, markup, "")


# ---------------------------------------------------------------- personnage


def pose_layout(name):
    im = Image.open(ROOT / "assets/poses" / f"{name}.png")
    alpha = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    x0, y0, x1, y1 = alpha.getbbox()
    feet = alpha.crop((0, int(y1 - (y1 - y0) * 0.05), im.width, y1)).getbbox()
    feet_cx = (feet[0] + feet[2]) / 2
    return {
        "left": round(FEET_X - feet_cx * SCALE, 1),
        "top": round(BASELINE - y1 * SCALE, 1),
        "w": round(im.width * SCALE, 1),
        "h": round(im.height * SCALE, 1),
    }


def render_character(plan):
    poses = plan["poses"]
    names = sorted({p for _, p in poses})
    imgs = "\n".join(
        f'            <img id="character-{n}" class="pose" src="assets/poses/{n}.png" alt="" '
        f'style="left:{l["left"]}px;top:{l["top"]}px;width:{l["w"]}px;height:{l["h"]}px" />'
        for n in names
        for l in [pose_layout(n)]
    )
    css = f"""        #character .floor-shadow {{
          position: absolute; left: {FEET_X - 230}px; top: {BASELINE - 30}px; width: 460px; height: 60px;
          border-radius: 50%; background: radial-gradient(ellipse at center, rgba(40, 28, 14, 0.28), transparent 70%);
        }}
        #character .rig, #character .inner {{ position: absolute; inset: 0; transform-origin: {FEET_X}px {BASELINE}px; }}
        #character .pose {{ position: absolute; opacity: 0; }}"""
    markup = (
        '        <div class="floor-shadow"></div>\n'
        '        <div class="rig" id="character-rig">\n'
        '          <div class="inner" id="character-inner">\n'
        f"{imgs}\n"
        "          </div>\n"
        "        </div>"
    )
    dur = plan["duration"]
    js = [f"          const POSES = {json.dumps(poses)};", f"          const DUR = {dur};"]
    js.append(
        """          POSES.forEach(([t, name], i) => {
            const el = "#character-" + name;
            const next = POSES[i + 1];
            if (i === 0) {
              tl.set(el, { opacity: 1 }, 0);
            } else {
              tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.12, ease: "none", immediateRender: false }, t - 0.06);
              tl.fromTo("#character-rig", { scale: 0.97 }, { scale: 1, duration: 0.4, ease: "back.out(2.5)", immediateRender: false }, t);
            }
            if (next) {
              tl.fromTo(el, { opacity: 1 }, { opacity: 0, duration: 0.12, ease: "none", immediateRender: false }, next[0] - 0.06);
            }
          });"""
    )
    js.append(
        f'          tl.fromTo("#character-inner", {{ scaleY: 1 }}, {{ scaleY: 1.008, duration: 1.5, ease: "sine.inOut", '
        f"yoyo: true, repeat: {int(dur / 1.5) - 1} }}, 0);"
    )
    return sub("character", css, markup, "\n".join(js))


# ---------------------------------------------------------------- bandeau


def render_hud(plan):
    secs = plan["sections"]
    css = """        #hud .bar {
          position: absolute; left: 108px; top: 196px; width: 864px; height: 92px; border-radius: 46px;
          background: #ffffff; box-shadow: 0 14px 40px rgba(40, 35, 20, 0.14);
          display: flex; align-items: center; gap: 18px; padding: 0 16px;
        }
        #hud .tag {
          background: #3f6b3c; color: #ffffff; font-family: "JetBrains Mono", monospace; font-weight: 700;
          font-size: 22px; letter-spacing: 0.08em; padding: 13px 18px; border-radius: 30px; white-space: nowrap;
        }
        #hud .name { font-weight: 900; font-size: 27px; white-space: nowrap; flex: 1; }
        #hud .secs { position: relative; width: 250px; height: 58px; }
        #hud .sec {
          position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
          background: #f4f1ea; border-radius: 29px; font-family: "JetBrains Mono", monospace; font-weight: 700;
          font-size: 20px; letter-spacing: 0.04em; white-space: nowrap; opacity: 0;
        }"""
    spans = "".join(f'<span class="sec" id="hud-sec-{i}">{esc(t)}</span>' for i, (_, t) in enumerate(secs))
    h = plan["header"]
    markup = (
        f'        <div class="bar"><span class="tag">{esc(h["tag"])}</span>'
        f'<span class="name">{esc(h["title"])}</span><div class="secs">{spans}</div></div>'
    )
    js = []
    for i, (t, _) in enumerate(secs):
        if i == 0:
            js.append(f'          tl.set("#hud-sec-0", {{ opacity: 1 }}, 0);')
        else:
            js.append(
                f'          tl.fromTo("#hud-sec-{i}", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power2.out" }}, {fmt(t)});'
            )
        if i + 1 < len(secs):
            js.append(
                f'          tl.fromTo("#hud-sec-{i}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.15, immediateRender: false }}, {fmt(secs[i + 1][0] - 0.15)});'
            )
    return sub("hud", css, markup, "\n".join(js))


# ---------------------------------------------------------------- sous-titres


def caption_chunks(plan):
    words = json.loads((ROOT / plan["transcript"]).read_text())["words"]
    fixes = plan.get("fixes", {})
    chunks, cur = [], []
    for w in words:
        text = fixes.get(w["word"].strip(), w["word"].strip())
        cur.append({"w": text, "s": round(w["start"], 2)})
        if len(cur) >= 4 or text[-1:] in ",.?!:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        end = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else plan["duration"]
        out.append({"start": c[0]["s"], "end": end, "words": c})
    return out


def render_captions(plan):
    kws = {k.lower() for k in plan.get("keywords", [])}
    chunks = caption_chunks(plan)
    css = """        #captions .cap {
          position: absolute; left: 108px; right: 108px; top: 1520px; height: 200px;
          display: flex; align-items: center; justify-content: center; text-align: center;
          font-weight: 900; font-size: 66px; line-height: 1.12; letter-spacing: -0.01em; opacity: 0;
        }
        #captions .w { display: inline-block; color: #6b6458; padding: 0 0.1em; margin: 0 0.05em; border-radius: 12px; }"""
    rows, data = [], []
    for i, c in enumerate(chunks):
        spans = " ".join(f'<span class="w" id="cap-{i}-{j}">{esc(w["w"])}</span>' for j, w in enumerate(c["words"]))
        rows.append(f'        <div class="cap" id="cap-{i}"><p>{spans}</p></div>')
        keys = [re.sub(r"[^\wÀ-ÿ']", "", w["w"].lower()) in kws for w in c["words"]]
        data.append([c["start"], c["end"], [[w["s"], int(k)] for w, k in zip(c["words"], keys)]])
    js = f"""          const CAPS = {json.dumps(data)};
          CAPS.forEach(([start, end, words], i) => {{
            const cap = "#cap-" + i;
            tl.fromTo(cap, {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.16, ease: "power2.out" }}, start);
            if (i < CAPS.length - 1) tl.set(cap, {{ opacity: 0 }}, end);
            words.forEach(([t, kw], j) => {{
              const w = "#cap-" + i + "-" + j;
              tl.set(w, kw ? {{ color: "#16140f", backgroundColor: "#f2b84b" }} : {{ color: "#16140f" }}, t);
              tl.fromTo(w, {{ scale: 1.18 }}, {{ scale: 1, duration: 0.22, ease: "back.out(3)", immediateRender: false }}, t);
            }});
          }});"""
    return sub("captions", css, "\n".join(rows), js), len(chunks)


# ---------------------------------------------------------------- racine


def host(cid, start, dur, track, kind="graphics"):
    return (
        f'<div id="host-{cid}" class="clip" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
        f'data-start="{fmt(start)}" data-duration="{fmt(dur)}" data-track-index="{track}" data-track-kind="{kind}" '
        f'data-width="{W}" data-height="{H}"></div>'
    )


def render_root(plan, sfx_tags):
    D = plan["duration"]
    cards = "\n".join(
        f"          {host(c['id'], c['start'], c['end'] - c['start'], 3)}" for c in plan["cards"]
    )
    cam_js = []
    for c in plan.get("camera", []):
        cam_js.append(
            f'      tl.fromTo("#cam", {{ scale: 1 }}, {{ scale: {c["scale"]}, duration: 0.6, ease: "power2.out", immediateRender: false }}, {fmt(c["at"])});'
        )
        cam_js.append(
            f'      tl.fromTo("#cam", {{ scale: {c["scale"]} }}, {{ scale: 1, duration: 0.35, ease: "power2.inOut", immediateRender: false }}, {fmt(c["until"] - 0.35)});'
        )
    v = plan["voice"]
    return f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{esc(plan["title"])}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #efe7d8; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: #efe7d8; }}
      .clip {{ position: absolute; inset: 0; }}
      #cam {{ position: absolute; inset: 0; transform-origin: 540px 860px; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{fmt(D)}" data-width="{W}" data-height="{H}">
      <div id="cam">
          {host("decor", 0, D, 1)}
{cards}
          {host("character", 0, D, 2)}
      </div>
      {host("hud", 0, D, 4)}
      {host("captions", 0, D, 5, "captions")}
      <audio id="voice" src="{v["src"]}" data-start="0" data-duration="{fmt(v["duration"])}" data-track-index="10" data-volume="1"></audio>
{sfx_tags}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(cam_js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def sfx_tags(plan):
    cfg = plan.get("sfx", {})
    cues = list(cfg.get("cues", []))
    w = cfg.get("card_whoosh")
    if w:
        cues += [{"at": c["start"], "file": w["file"], "volume": w["volume"]} for c in plan["cards"] if c["start"] > 0]
    cues.sort(key=lambda c: c["at"])
    out_dir = ROOT / "assets/sfx"
    out_dir.mkdir(parents=True, exist_ok=True)
    tags = []
    for k, c in enumerate(cues):
        src = SFX_LIB / f"{c['file']}.mp3"
        dst = out_dir / src.name
        if not dst.exists():
            shutil.copy(src, dst)
        length = sfx_duration(dst)
        tags.append(
            f'      <audio id="sfx-{k}" src="assets/sfx/{src.name}" data-start="{fmt(c["at"])}" '
            f'data-duration="{fmt(length)}" data-track-index="{11 + k % 2}" data-volume="{c["volume"]}"></audio>'
        )
    return "\n".join(tags), len(cues)


def sfx_duration(path):
    import subprocess

    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()), 3)


def main():
    plan = json.loads((ROOT / "plan.json").read_text())
    comp = ROOT / "compositions"
    comp.mkdir(exist_ok=True)
    for old in comp.glob("*.html"):
        old.unlink()
    for i, card in enumerate(plan["cards"]):
        (comp / f"{card['id']}.html").write_text(render_card(card, i == len(plan["cards"]) - 1))
    (comp / "decor.html").write_text(render_decor())
    (comp / "character.html").write_text(render_character(plan))
    (comp / "hud.html").write_text(render_hud(plan))
    caps, n_caps = render_captions(plan)
    (comp / "captions.html").write_text(caps)
    tags, n_sfx = sfx_tags(plan)
    (ROOT / "index.html").write_text(render_root(plan, tags))
    print(
        f"OK : {len(plan['cards'])} cartes, {len({p for _, p in plan['poses']})} poses, "
        f"{n_caps} blocs de sous-titres, {n_sfx} bruitages, {plan['duration']} s"
    )


if __name__ == "__main__":
    main()
