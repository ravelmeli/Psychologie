"""Génère la composition HyperFrames à partir de plan.json.

    python3 -I build.py

Sorties : index.html (racine) et compositions/*.html — un panneau fixe
(« appli bancaire ») et une sous-composition par séquence (beat), plus décor,
personnage, bandeau et sous-titres. Pour une nouvelle vidéo, ne modifier que
plan.json (et les médias). Icônes : Fluent Emoji 3D (MIT) dans assets/icons/.
"""
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
SFX_LIB = ROOT.parent.parent / ".claude/skills/media-use/audio/assets/sfx"

W, H = 1080, 1920
# Personnage : ~40 % de la hauteur, comme dans les références, aligné sur les pieds
SCALE = 0.50
FEET_X = 190
BASELINE = 1440
# Panneau fixe (zone sûre titre 80 %, à gauche de la colonne d'icônes TikTok)
BOARD = {"left": 392, "top": 330, "w": 580, "h": 980}
HEAD_H = 104
PAD = 36
CONTENT = {
    "left": BOARD["left"] + PAD,
    "top": BOARD["top"] + HEAD_H + 26,
    "w": BOARD["w"] - 2 * PAD,
    "h": BOARD["h"] - HEAD_H - 26 - 30,
}

COLORS = {"red": "#d9453b", "green": "#3f8f4a", "dark": "#3f6b3c", "light": "#8db580", "yellow": "#f2b84b"}

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
            tl.fromTo(s, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2.2)" }, t);
          const stamp = (s, t, r) =>
            tl.fromTo(s, { opacity: 0, scale: 1.8, rotation: r }, { opacity: 1, scale: 1, rotation: r, duration: 0.26, ease: "power3.in" }, t);
          const fr = (v, d) => {
            const p = Math.abs(v).toFixed(d).split(".");
            p[0] = p[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, " ");
            return (v < 0 ? "-" : "") + p.join(",");
          };
          const count = (sel, from, to, t, dur, d, suffix) => {
            const el = document.querySelector(sel);
            const o = { v: from };
            tl.fromTo(o, { v: from }, { v: to, duration: dur, ease: "power2.out", immediateRender: false,
              onUpdate: () => { el.textContent = fr(o.v, d) + suffix; } }, t);
          };"""


def esc(s):
    return html.escape(s, quote=False)


def fmt(t):
    return f"{max(t, 0):.3f}".rstrip("0").rstrip(".") or "0"


def fr(v, d):
    whole, _, dec = f"{abs(v):.{d}f}".partition(".")
    whole = re.sub(r"\B(?=(\d{3})+(?!\d))", " ", whole)
    return ("-" if v < 0 else "") + whole + ("," + dec if d else "")


def norm(x):
    return {"text": x} if isinstance(x, str) else x


def icon(name, size, extra=""):
    if not (ROOT / "assets/icons" / f"{name}.png").exists():
        raise FileNotFoundError(f"icône manquante : assets/icons/{name}.png")
    return f'<img class="ic"{extra} src="assets/icons/{name}.png" alt="" style="width:{size}px;height:{size}px" />'


def sub(cid, css, markup, js):
    return SUB.replace("%CSS%", css).replace("%HTML%", markup).replace("%JS%", js).replace("%ID%", cid)


# ---------------------------------------------------------------- séquences

BEAT_CSS = """        #%ID% .beat {
          position: absolute; left: %L%px; top: %T%px; width: %W%px; height: %H%px;
          display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 30px;
          text-align: center;
        }
        #%ID% .hid { opacity: 0; }
        #%ID% .ic { display: block; filter: drop-shadow(0 14px 18px rgba(40, 30, 10, 0.22)); }
        #%ID% .icons { display: flex; align-items: center; justify-content: center; gap: 22px; }
        #%ID% .sep { font-weight: 900; font-size: 64px; color: #a86f0c; }
        #%ID% .title { font-weight: 900; font-size: 66px; line-height: 1.04; letter-spacing: -0.02em; }
        #%ID% .sub { display: flex; align-items: center; gap: 14px; font-weight: 700; font-size: 38px; line-height: 1.2; color: #3a362e; }
        #%ID% .badge {
          position: absolute; right: -6px; top: 0; display: flex; flex-direction: column; align-items: center; gap: 6px;
          font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 30px; color: #c0352c;
        }
        #%ID% .stamp {
          font-weight: 900; font-size: 40px; letter-spacing: 0.02em; padding: 16px 24px;
          border: 7px solid #d9453b; color: #c0352c; border-radius: 16px; background: #ffffff;
        }
        #%ID% .stamp.yellow { border-color: #c98a12; color: #16140f; background: #f2b84b; }
        #%ID% .meter { width: 100%; }
        #%ID% .meter-top {
          display: flex; justify-content: space-between; font-family: "JetBrains Mono", monospace;
          font-weight: 700; font-size: 24px; letter-spacing: 0.1em; margin-bottom: 14px;
        }
        #%ID% .bar { height: 44px; border-radius: 22px; background: #f1ece2; overflow: hidden; }
        #%ID% .fill { width: 100%; height: 100%; border-radius: 22px; transform-origin: left center; }
        #%ID% .plate {
          width: 210px; height: 210px; border-radius: 40px; background: #f2b84b; box-shadow: 0 12px 0 #c98a12;
          display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 120px;
        }
        #%ID% .of { font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 24px; letter-spacing: 0.14em; color: #3f6b3c; }
        #%ID% .big { font-weight: 900; font-size: 140px; line-height: 1; letter-spacing: -0.03em; white-space: nowrap; }
        #%ID% .label { font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 24px; letter-spacing: 0.1em; text-transform: uppercase; color: #3f6b3c; }
        #%ID% .rows { width: 100%; display: flex; flex-direction: column; gap: 34px; }
        #%ID% .row { display: flex; align-items: center; gap: 26px; text-align: left; font-weight: 800; font-size: 40px; line-height: 1.15; }
        #%ID% .row.tile { font-weight: 900; font-size: 42px; white-space: nowrap; }
        #%ID% .iconwrap { position: relative; flex: none; }
        #%ID% .num {
          position: absolute; left: -10px; top: -10px; width: 52px; height: 52px; border-radius: 26px;
          background: #16140f; color: #ffffff; display: flex; align-items: center; justify-content: center;
          font-weight: 900; font-size: 28px;
        }
        #%ID% .chart { position: relative; width: 100%; height: 620px; display: flex; align-items: flex-end; justify-content: center; gap: 70px; }
        #%ID% .col { display: flex; flex-direction: column; align-items: center; gap: 16px; }
        #%ID% .barv { width: 150px; height: 460px; border-radius: 22px 22px 8px 8px; transform-origin: center bottom; }
        #%ID% .cl { font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 24px; letter-spacing: 0.08em; }
        #%ID% .x2 {
          position: absolute; right: 0; top: 0; width: 160px; height: 160px; border-radius: 80px; background: #f2b84b;
          box-shadow: 0 10px 0 #c98a12; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 68px;
        }
        #%ID% .receipt { width: 100%; display: flex; flex-direction: column; gap: 16px; }
        #%ID% .line {
          display: flex; align-items: center; gap: 18px; font-family: "JetBrains Mono", monospace; font-weight: 700;
          font-size: 30px; padding-bottom: 14px; border-bottom: 3px dashed #e6dfd1; text-align: left;
        }
        #%ID% .line .l { flex: 1; }
        #%ID% .total { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-top: 18px; }
        #%ID% .totalv { font-weight: 900; font-size: 92px; color: #c0352c; white-space: nowrap; }
        #%ID% .reaction { position: absolute; right: -10px; bottom: 120px; }
        #%ID% .buy {
          align-self: stretch; font-weight: 900; font-size: 54px; letter-spacing: 0.04em; padding: 30px 0;
          border-radius: 26px; background: #f2b84b; box-shadow: 0 12px 0 #c98a12;
        }
        #%ID% .cta {
          display: flex; align-items: center; gap: 16px; padding: 18px 28px; border-radius: 44px;
          background: #16140f; color: #ffffff; font-weight: 900; font-size: 30px; white-space: nowrap;
        }"""


class Beat:
    def __init__(self, beat, end, last):
        self.b, self.start, self.end, self.last = beat, beat["start"], end, last
        self.parts, self.js, self.n = [], [JS_HELPERS], 0

    def nid(self):
        self.n += 1
        return f"{self.b['id']}-e{self.n}"

    def L(self, t):
        return fmt(t - self.start)

    def later(self, t):
        return t is not None and t > self.start + 0.05

    def appear(self, eid, at):
        if self.later(at):
            self.js.append(f'          pop("#{eid}", {self.L(at)});')
            return " hid"
        return ""

    def text(self, cls, spec, extra=""):
        spec = norm(spec)
        i = self.nid()
        ico = icon(spec["icon"], 52) if "icon" in spec else ""
        return f'<div class="{cls}{self.appear(i, spec.get("at"))}" id="{i}"{extra}>{ico}{esc(spec["text"])}</div>'

    def icons_row(self, items):
        size = {1: 230, 2: 190, 3: 150}[sum(1 for x in items if "icon" in x)]
        out = []
        for it in items:
            i = self.nid()
            cls = self.appear(i, it.get("at"))
            if "sep" in it:
                out.append(f'<span class="sep{cls}" id="{i}">{esc(it["sep"])}</span>')
            else:
                out.append(f'<span class="{cls.strip()}" id="{i}">{icon(it["icon"], size)}</span>')
        return f'<div class="icons">{"".join(out)}</div>'

    def meter(self, m):
        i = self.nid()
        c_to, c_from = COLORS[m["color"]], COLORS[m.get("color_from", m["color"])]
        self.js.append(
            f'          tl.fromTo("#{i}", {{ scaleX: {m["from"]}, backgroundColor: "{c_from}" }}, '
            f'{{ scaleX: {m["to"]}, backgroundColor: "{c_to}", duration: 0.9, ease: "power2.out" }}, {self.L(m["at"])});'
        )
        return (
            f'<div class="meter"><div class="meter-top"><span>{esc(m["label"])}</span><span>{int(m["to"] * 100)} %</span></div>'
            f'<div class="bar"><div class="fill" id="{i}"></div></div></div>'
        )

    def stamp(self, s):
        i = self.nid()
        yellow = s.get("color") == "yellow"
        self.js.append(f'          stamp("#{i}", {self.L(s["at"])}, {-4 if yellow else -5});')
        return f'<div class="stamp{" yellow" if yellow else ""} hid" id="{i}">{esc(s["text"])}</div>'

    def render(self):
        b, P = self.b, self.parts
        t = b["type"]
        if t == "hero":
            P.append(self.icons_row(b["icons"]))
            if "meter" in b:
                P.append(self.meter(b["meter"]))
            if "title" in b:
                P.append(self.text("title", b["title"]))
            if "sub" in b:
                P.append(self.text("sub", b["sub"]))
            if "button" in b:
                bt = b["button"]
                i = self.nid()
                P.append(f'<div class="buy{self.appear(i, bt["at"])}" id="{i}">{esc(bt["text"])}</div>')
                reps = int((bt["pulse_until"] - bt["at"] - 0.4) / 0.35)
                reps -= 1 - reps % 2
                self.js.append(
                    f'          tl.fromTo("#{i}", {{ scale: 1 }}, {{ scale: 1.06, duration: 0.35, ease: "sine.inOut", yoyo: true, '
                    f'repeat: {reps}, immediateRender: false }}, {self.L(bt["at"] + 0.4)});'
                )
            if "stamp" in b:
                P.append(self.stamp(b["stamp"]))
            if "cta" in b:
                c = b["cta"]
                i = self.nid()
                P.append(f'<div class="cta{self.appear(i, c["at"])}" id="{i}">{icon(c["icon"], 56)}{esc(c["text"])}</div>')
                self.js.append(
                    f'          tl.fromTo("#{i}", {{ y: 0 }}, {{ y: -10, duration: 0.45, ease: "sine.inOut", yoyo: true, repeat: 5, '
                    f'immediateRender: false }}, {self.L(c["at"] + 0.4)});'
                )
            if "badge" in b:
                bd = b["badge"]
                i = self.nid()
                txt = f"<span>{esc(bd['text'])}</span>" if "text" in bd else ""
                P.append(f'<div class="badge{self.appear(i, bd["at"])}" id="{i}">{icon(bd["icon"], 130)}{txt}</div>')
        elif t == "chapter":
            P.append(icon(b["icon"], 150))
            P.append(f'<div class="plate">{esc(b["num"])}</div>')
            P.append(f'<div class="of">{esc(b["of"])}</div>')
            P.append(f'<div class="title">{esc(b["title"])}</div>')
            if "sub" in b:
                P.append(self.text("sub", b["sub"]))
            self.js.append(
                f'          tl.fromTo("#{b["id"]}-beat .plate", {{ rotation: -12, scale: 0.4 }}, '
                f'{{ rotation: 0, scale: 1, duration: 0.5, ease: "back.out(2)" }}, 0.05);'
            )
        elif t == "counter":
            i = self.nid()
            P.append(icon(b["icon"], 220))
            P.append(f'<div class="label">{esc(b["label"])}</div>')
            P.append(f'<div class="big" id="{i}">{fr(b["from"], 0)}{esc(b["suffix"])}</div>')
            self.js.append(
                f'          count("#{i}", {b["from"]}, {b["to"]}, {self.L(b["at"])}, {b["dur"]}, 0, {json.dumps(b["suffix"])});'
            )
            if "sub" in b:
                P.append(self.text("sub", b["sub"]))
        elif t in ("tiles", "list"):
            rows = []
            items = b["tiles"] if t == "tiles" else b["items"]
            for k, it in enumerate(items, 1):
                i = self.nid()
                num = f'<span class="num">{k}</span>' if b.get("num") else ""
                size = 130
                rows.append(
                    f'<div class="row{" tile" if t == "tiles" else ""}{self.appear(i, it.get("at"))}" id="{i}">'
                    f'<span class="iconwrap">{icon(it["icon"], size)}{num}</span><span>{esc(it["text"])}</span></div>'
                )
            P.append(f'<div class="rows">{"".join(rows)}</div>')
        elif t == "bars":
            cols = []
            for it in b["items"]:
                i = self.nid()
                color = COLORS[it.get("color", "dark")]
                cols.append(
                    f'<div class="col"><div class="barv" id="{i}" style="background:{color}"></div>'
                    f'<div class="cl">{esc(it["label"])}</div>{icon(it["icon"], 110)}</div>'
                )
                self.js.append(
                    f'          tl.fromTo("#{i}", {{ scaleY: 0 }}, {{ scaleY: {it["to"]}, duration: 0.5, ease: "power2.out" }}, {self.L(it["at"])});'
                )
                if "grow_to" in it:
                    self.js.append(
                        f'          tl.fromTo("#{i}", {{ scaleY: {it["to"]} }}, {{ scaleY: {it["grow_to"]}, duration: 1.0, '
                        f'ease: "power3.out", immediateRender: false }}, {self.L(it["grow_at"])});'
                    )
            i = self.nid()
            cols.append(f'<div class="x2 hid" id="{i}">{esc(b["badge"]["text"])}</div>')
            self.js.append(f'          pop("#{i}", {self.L(b["badge"]["at"])});')
            P.append(f'<div class="chart">{"".join(cols)}</div>')
        elif t == "receipt":
            lines = []
            for k, ln in enumerate(b["lines"]):
                i = self.nid()
                lines.append(
                    f'<div class="line hid" id="{i}">{icon(ln["icon"], 54)}<span class="l">{esc(ln["left"])}</span>'
                    f'<span>{esc(ln["right"])}</span></div>'
                )
                self.js.append(
                    f'          tl.fromTo("#{i}", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.25, ease: "power2.out" }}, '
                    f'{self.L(b["lines_at"] + k * b["step"])});'
                )
            tot = b["total"]
            i, v = self.nid(), self.nid()
            lines.append(
                f'<div class="total hid" id="{i}"><div class="label">{esc(tot["label"])}</div>'
                f'<div class="totalv" id="{v}">0,00 €</div></div>'
            )
            self.js.append(f'          stamp("#{i}", {self.L(tot["at"])}, 0);')
            self.js.append(f'          count("#{v}", 0, {tot["to"]}, {self.L(tot["at"])}, {tot["dur"]}, 2, " €");')
            P.append(f'<div class="receipt">{"".join(lines)}</div>')
            if "reaction" in b:
                r = b["reaction"]
                i = self.nid()
                P.append(f'<div class="reaction hid" id="{i}">{icon(r["icon"], 170)}</div>')
                self.js.append(f'          pop("#{i}", {self.L(r["at"])});')
                self.js.append(
                    f'          tl.fromTo("#{b["id"]}-beat", {{ x: -18 }}, {{ x: 0, duration: 0.5, ease: "elastic.out(1.2, 0.3)", '
                    f'immediateRender: false }}, {self.L(r["at"])});'
                )
        else:
            raise ValueError(f"type de séquence inconnu : {t}")

        sel = f"#{b['id']}-beat"
        if self.start > 0:
            self.js.append(
                f'          tl.fromTo("{sel}", {{ opacity: 0, scale: 0.9, y: 30 }}, '
                f'{{ opacity: 1, scale: 1, y: 0, duration: 0.3, ease: "back.out(1.7)" }}, 0);'
            )
        if not self.last:
            self.js.append(
                f'          tl.fromTo("{sel}", {{ opacity: 1, scale: 1 }}, {{ opacity: 0, scale: 0.92, duration: 0.15, ease: "power2.in", '
                f'immediateRender: false }}, {fmt(self.end - self.start - 0.15)});'
            )
        body = "\n".join(f"          {p}" for p in P)
        markup = f'        <div class="beat" id="{sel[1:]}">\n{body}\n        </div>'
        css = (
            BEAT_CSS.replace("%L%", str(CONTENT["left"])).replace("%T%", str(CONTENT["top"]))
            .replace("%W%", str(CONTENT["w"])).replace("%H%", str(CONTENT["h"]))
        )
        return sub(b["id"], css, markup, "\n".join(self.js))


# ---------------------------------------------------------------- panneau fixe


def render_board(plan):
    bd = plan["board"]
    css = f"""        #board .panel {{
          position: absolute; left: {BOARD["left"]}px; top: {BOARD["top"]}px; width: {BOARD["w"]}px; height: {BOARD["h"]}px;
          background: #ffffff; border-radius: 44px; box-shadow: 0 30px 70px rgba(40, 35, 20, 0.2);
          border: 3px solid #ece6d8; overflow: hidden;
        }}
        #board .head {{
          height: {HEAD_H}px; background: #1f3a2c; display: flex; align-items: center; gap: 16px; padding: 0 28px;
          color: #ffffff;
        }}
        #board .head .ic {{ width: 60px; height: 60px; }}
        #board .acct {{ flex: 1; font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 22px; letter-spacing: 0.12em; }}
        #board .bal {{ display: flex; flex-direction: column; align-items: flex-end; }}
        #board .bal small {{ font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: 16px; letter-spacing: 0.12em; color: #b9d3b3; }}
        #board .amt {{ font-weight: 900; font-size: 34px; white-space: nowrap; }}"""
    first = bd["balance"][0]["value"]
    markup = (
        '        <div class="panel"><div class="head">'
        f'<img class="ic" src="assets/icons/bank.png" alt="" /><span class="acct">{esc(bd["title"])}</span>'
        f'<span class="bal"><small>SOLDE</small><span class="amt" id="board-amt">{fr(first, 2)} €</span></span>'
        "</div></div>"
    )
    js = [JS_HELPERS]
    for prev, cur in zip(bd["balance"], bd["balance"][1:]):
        js.append(f'          count("#board-amt", {prev["value"]}, {cur["value"]}, {fmt(cur["at"])}, 0.9, 2, " €");')
        js.append(
            f'          tl.fromTo("#board-amt", {{ color: "#ff8a80" }}, {{ color: "#ffffff", duration: 1.2, immediateRender: false }}, {fmt(cur["at"])});'
        )
    return sub("board", css, markup, "\n".join(js))


# ---------------------------------------------------------------- décor


def render_decor(plan):
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
          position: absolute; left: 0; right: 0; top: 1190px; height: 240px;
          background:
            repeating-linear-gradient(90deg, transparent 0 176px, rgba(120, 100, 70, 0.12) 176px 180px),
            linear-gradient(180deg, #e9e0cf, #e2d7c3);
          border-top: 6px solid #d9ccb5;
        }
        #decor .base { position: absolute; left: 0; right: 0; top: 1430px; height: 22px; background: #cdbd9f; }
        #decor .floor {
          position: absolute; left: 0; right: 0; top: 1452px; bottom: 0;
          background:
            repeating-linear-gradient(0deg, rgba(110, 75, 40, 0.10) 0 3px, transparent 3px 84px),
            linear-gradient(180deg, #e8d6b8, #efe2ca);
        }
        #decor .plant { position: absolute; left: 24px; top: 1246px; width: 120px; height: 190px; }
        #decor .pot { position: absolute; left: 22px; bottom: 0; width: 76px; height: 70px; background: #c97b4a; border-radius: 6px 6px 18px 18px; }
        #decor .leaf { position: absolute; width: 46px; height: 100px; border-radius: 50%; background: #6f9a62; transform-origin: bottom center; }
        #decor .float { position: absolute; opacity: 0.38; }
        #decor .vignette {
          position: absolute; inset: 0;
          background: radial-gradient(ellipse 85% 75% at 50% 45%, transparent 60%, rgba(60, 45, 25, 0.16) 100%);
        }"""
    leaves = "".join(
        f'<div class="leaf" style="left:{x}px;top:{y}px;transform:rotate({r}deg)"></div>'
        for x, y, r in [(10, 30, -35), (38, 0, -8), (64, 22, 24), (36, 40, 6)]
    )
    # Icônes flottantes : positions fixes (déterministes), dans les espaces libres
    spots = [(14, 460, 80), (250, 480, 64), (120, 610, 72), (300, 650, 56), (995, 540, 62), (990, 920, 70), (60, 1620, 66), (960, 1650, 74)]
    floats, js = [], []
    for k, (name, (x, y, s)) in enumerate(zip(plan.get("ambient", []), spots)):
        floats.append(
            f'<img class="float" id="decor-f{k}" src="assets/icons/{name}.png" alt="" '
            f'style="left:{x}px;top:{y}px;width:{s}px;height:{s}px" />'
        )
        D = plan["duration"]
        js.append(
            f'          tl.fromTo("#decor-f{k}", {{ y: 0 }}, {{ y: -{120 + 25 * (k % 3)}, duration: {D}, ease: "none" }}, 0);'
        )
        js.append(
            f'          tl.fromTo("#decor-f{k}", {{ rotation: {-8 if k % 2 else 8} }}, {{ rotation: {8 if k % 2 else -8}, duration: {2.4 + 0.3 * (k % 4)}, '
            f'ease: "sine.inOut", yoyo: true, repeat: {int(D / (2.4 + 0.3 * (k % 4))) - 1} }}, 0);'
        )
    markup = (
        '        <div class="wall"></div>\n'
        '        <div class="light"></div>\n'
        '        <div class="panel"></div>\n'
        f'        <div class="plant">{leaves}<div class="pot"></div></div>\n'
        '        <div class="base"></div>\n'
        '        <div class="floor"></div>\n'
        f'        {"".join(floats)}\n'
        '        <div class="vignette"></div>'
    )
    return sub("decor", css, markup, "\n".join(js))


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
          position: absolute; left: {FEET_X - 170}px; top: {BASELINE - 24}px; width: 340px; height: 48px;
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
    js = [f"          const POSES = {json.dumps(poses)};"]
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
          position: absolute; left: 108px; top: 196px; width: 864px; height: 92px; border-radius: 22px;
          background: #1f3a2c; box-shadow: 0 14px 40px rgba(20, 30, 20, 0.25);
          display: flex; align-items: center; gap: 18px; padding: 0 16px; overflow: hidden;
        }
        #hud .bar::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 7px; background: #f2b84b; }
        #hud .tag {
          background: #f2b84b; color: #16140f; font-family: "JetBrains Mono", monospace; font-weight: 700;
          font-size: 22px; letter-spacing: 0.08em; padding: 12px 16px; border-radius: 12px; white-space: nowrap;
        }
        #hud .name { font-weight: 900; font-size: 28px; white-space: nowrap; flex: 1; color: #ffffff; }
        #hud .secs { position: relative; width: 250px; height: 56px; }
        #hud .sec {
          position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
          background: #ffffff; border-radius: 28px; font-family: "JetBrains Mono", monospace; font-weight: 700;
          font-size: 20px; letter-spacing: 0.04em; white-space: nowrap; color: #16140f; opacity: 0;
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
            js.append('          tl.set("#hud-sec-0", { opacity: 1 }, 0);')
        else:
            js.append(
                f'          tl.fromTo("#hud-sec-{i}", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power2.out" }}, {fmt(t)});'
            )
        if i + 1 < len(secs):
            js.append(
                f'          tl.fromTo("#hud-sec-{i}", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.15, immediateRender: false }}, {fmt(secs[i + 1][0] - 0.15)});'
            )
    return sub("hud", css, markup, "\n".join(js))


# ---------------------------------------------------------------- sous-titres (style des références)


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
    chunks = caption_chunks(plan)
    css = f"""        #captions .cap {{
          position: absolute; left: 108px; right: 108px; top: {BASELINE + 40}px; height: 150px;
          display: flex; align-items: center; justify-content: center; text-align: center;
          font-weight: 800; font-size: 52px; line-height: 1.15; opacity: 0;
        }}
        #captions .w {{ color: #8a8377; }}"""
    rows, data = [], []
    for i, c in enumerate(chunks):
        spans = " ".join(f'<span class="w" id="cap-{i}-{j}">{esc(w["w"])}</span>' for j, w in enumerate(c["words"]))
        rows.append(f'        <div class="cap" id="cap-{i}"><p>{spans}</p></div>')
        data.append([c["start"], c["end"], [w["s"] for w in c["words"]]])
    js = f"""          const CAPS = {json.dumps(data)};
          CAPS.forEach(([start, end, words], i) => {{
            tl.set("#cap-" + i, {{ opacity: 1 }}, start);
            if (i < CAPS.length - 1) tl.set("#cap-" + i, {{ opacity: 0 }}, end);
            words.forEach((t, j) => tl.set("#cap-" + i + "-" + j, {{ color: "#16140f" }}, t));
          }});"""
    return sub("captions", css, "\n".join(rows), js), len(chunks)


# ---------------------------------------------------------------- racine


def host(cid, start, dur, track, kind="graphics"):
    return (
        f'<div id="host-{cid}" class="clip" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
        f'data-start="{fmt(start)}" data-duration="{fmt(dur)}" data-track-index="{track}" data-track-kind="{kind}" '
        f'data-width="{W}" data-height="{H}"></div>'
    )


def sfx_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()), 3)


def sfx_tags(plan):
    cfg = plan.get("sfx", {})
    cues = list(cfg.get("cues", []))
    for b in plan["beats"]:
        if b["start"] <= 0:
            continue
        kind = cfg.get("chapter") if b["type"] == "chapter" else cfg.get("beat")
        if kind:
            cues.append({"at": b["start"], "file": kind["file"], "volume": kind["volume"]})
    cues.sort(key=lambda c: c["at"])
    out_dir = ROOT / "assets/sfx"
    out_dir.mkdir(parents=True, exist_ok=True)
    tags = []
    for k, c in enumerate(cues):
        src = SFX_LIB / f"{c['file']}.mp3"
        dst = out_dir / src.name
        if not dst.exists():
            shutil.copy(src, dst)
        tags.append(
            f'      <audio id="sfx-{k}" src="assets/sfx/{src.name}" data-start="{fmt(c["at"])}" '
            f'data-duration="{fmt(sfx_duration(dst))}" data-track-index="{11 + k % 2}" data-volume="{c["volume"]}"></audio>'
        )
    return "\n".join(tags), len(cues)


def render_root(plan, beat_spans, sfx):
    D = plan["duration"]
    beats = "\n".join(f"        {host(bid, s, e - s, 3)}" for bid, s, e in beat_spans)
    js = []
    for c in plan.get("camera", []):
        js.append(
            f'      tl.fromTo("#cam", {{ scale: 1 }}, {{ scale: {c["scale"]}, duration: 0.6, ease: "power2.out", immediateRender: false }}, {fmt(c["at"])});'
        )
        js.append(
            f'      tl.fromTo("#cam", {{ scale: {c["scale"]} }}, {{ scale: 1, duration: 0.35, ease: "power2.inOut", immediateRender: false }}, {fmt(c["until"] - 0.35)});'
        )
    for s in plan.get("spotlight", []):
        js.append(f'      tl.fromTo("#spot", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, immediateRender: false }}, {fmt(s["at"])});')
        js.append(f'      tl.fromTo("#spot", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.3, immediateRender: false }}, {fmt(s["until"])});')
    v, m = plan["voice"], plan.get("music")
    music = ""
    if m and (ROOT / m["src"]).exists():
        music = (
            f'      <audio id="music" src="{m["src"]}" data-start="0" data-duration="{fmt(D)}" '
            f'data-track-index="13" data-volume="{m["volume"]}"></audio>'
        )
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
      #cam {{ position: absolute; inset: 0; transform-origin: 640px 820px; }}
      #spot {{
        position: absolute; left: {BOARD["left"]}px; top: {BOARD["top"]}px; width: {BOARD["w"]}px; height: {BOARD["h"]}px;
        border-radius: 44px; box-shadow: 0 0 0 3000px rgba(18, 14, 8, 0.5); opacity: 0; pointer-events: none;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{fmt(D)}" data-width="{W}" data-height="{H}">
      <div id="cam">
        {host("decor", 0, D, 1)}
        {host("board", 0, D, 2)}
{beats}
        {host("character", 0, D, 4)}
        <div id="spot"></div>
      </div>
      {host("hud", 0, D, 5)}
      {host("captions", 0, D, 6, "captions")}
      <audio id="voice" src="{v["src"]}" data-start="0" data-duration="{fmt(v["duration"])}" data-track-index="10" data-volume="1"></audio>
{music}
{sfx}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def main():
    plan = json.loads((ROOT / "plan.json").read_text())
    comp = ROOT / "compositions"
    comp.mkdir(exist_ok=True)
    for old in comp.glob("*.html"):
        old.unlink()
    beats, spans = plan["beats"], []
    for k, b in enumerate(beats):
        end = beats[k + 1]["start"] if k + 1 < len(beats) else plan["duration"]
        (comp / f"{b['id']}.html").write_text(Beat(b, end, k == len(beats) - 1).render())
        spans.append((b["id"], b["start"], end))
    (comp / "board.html").write_text(render_board(plan))
    (comp / "decor.html").write_text(render_decor(plan))
    (comp / "character.html").write_text(render_character(plan))
    (comp / "hud.html").write_text(render_hud(plan))
    caps, n_caps = render_captions(plan)
    (comp / "captions.html").write_text(caps)
    tags, n_sfx = sfx_tags(plan)
    (ROOT / "index.html").write_text(render_root(plan, spans, tags))
    has_music = (ROOT / plan.get("music", {}).get("src", "-")).exists()
    print(
        f"OK : {len(beats)} séquences, {len({p for _, p in plan['poses']})} poses, {n_caps} blocs de sous-titres, "
        f"{n_sfx} bruitages, musique {'oui' if has_music else 'absente'}, {plan['duration']} s"
    )


if __name__ == "__main__":
    main()
