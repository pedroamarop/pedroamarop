#!/usr/bin/env node
// Renders the "hyperspace-jump" piece (ASCII Magic, MIT) in its halftone "dots" look as an
// SVG fragment of looping frames. The piece and its painter run unchanged; a recording
// canvas captures every dot and glyph they draw so the SVG matches the site's player.
// usage: node hyperspace.mjs <width> <height> [inset] [fps] [--static] [--contain]
import { pathToFileURL, fileURLToPath } from "node:url";
import path from "node:path";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "vendor", "ascii-magic-art");
const [Wa, Ha, insetA = "14", fpsA = "10"] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const STATIC = process.argv.includes("--static"), CONTAIN = process.argv.includes("--contain");
const W = +Wa, H = +Ha, IN = +insetA, FPS = +fpsA;
const imp = (p) => import(pathToFileURL(path.join(root, p)).href);
const { default: create, meta } = await imp("pieces/hyperspace-jump.js");
const { paint, CELL_W, cellAspect } = await imp("runtime/canvas.js");

globalThis.Path2D = class { constructor() { this.d = []; } moveTo() {} arc(x, y, r) { this.d.push(x, y, r); } };
const rec = { fills: [], texts: [] };
const ctx = {
  fillStyle: "", font: "", textBaseline: "",
  fill(p) { rec.fills.push([this.fillStyle, p.d]); },
  fillText(ch, x, y) { rec.texts.push([this.fillStyle, ch, x, y]); },
};

// fill the screen edge to edge (renderTo's fit "cover"), or show the whole piece ("contain")
const SW = W - 2 * IN, SH = H - 2 * IN, aspect = cellAspect(meta);
const cw = Math[CONTAIN ? "min" : "max"](SW / meta.cols, SH / (meta.rows * aspect)), ch = cw * aspect;
const ox = IN + (SW - meta.cols * cw) / 2, oy = IN + (SH - meta.rows * ch) / 2;
const inside = (x, y, r = 0) => x + r > IN && x - r < W - IN && y + r > IN && y - r < H - IN;
const n1 = (v) => Math.round(v * 10) / 10;
// the painter's dot grid (paintTone): square spacing of min(cw, ch) / density
const DENSITY = 1.31, step = Math.min(cw, ch) / DENSITY;
const gxN = Math.max(1, Math.round(meta.cols * cw / step)), gyN = Math.max(1, Math.round(meta.rows * ch / step));
const sx = meta.cols * cw / gxN, sy = meta.rows * ch / gyN;

const BG = "#04050c";                               // the piece's darkest space tone, also the banner's screen
const draw = create();
const PERIOD = 10;                                   // the piece's own cycle length (P in its source)
const N = STATIC ? 1 : Math.round(PERIOD * FPS);
const frames = [];
for (let i = 0; i < N; i++) {
  rec.fills = []; rec.texts = [];
  const t = STATIC ? 5.5 : i / FPS;
  paint(ctx, draw(t), meta.palette, { x: ox, y: oy, cw, ch, mode: "circle", noStamp: true });
  let s = "";
  for (const [fill, d] of rec.fills) {
    // dots sit on the painter's square grid: store them as integer grid steps, and draw each
    // horizontal run of neighbours as one dotted line (dash 0, gap 1, round caps)
    const pts = [];
    let r = 0;
    for (let k = 0; k < d.length; k += 3) {
      r = d[k + 2];
      if (!inside(d[k], d[k + 1], r)) continue;
      pts.push([Math.round((d[k + 1] - oy) / sy - 0.5), Math.round((d[k] - ox) / sx - 0.5)]);
    }
    if (!pts.length) continue;
    pts.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    let p = "", cx = 0, cy = 0;
    for (let k = 0; k < pts.length;) {
      const [j, i] = pts[k]; let n = 1;
      while (k + n < pts.length && pts[k + n][0] === j && pts[k + n][1] === i + n) n++;
      p += p ? `m${i - cx} ${j - cy}h${n - 1}` : `M${i} ${j}h${n - 1}`; cx = i + n - 1; cy = j; k += n;
    }
    s += `<path d="${p}" stroke="${fill}" stroke-width="${(2 * r / sx).toFixed(3)}"/>`;
  }
  s = s ? `<g transform="translate(${n1(ox + sx / 2)} ${n1(oy + sy / 2)}) scale(${sx.toFixed(4)} ${sy.toFixed(4)})">${s}</g>` : "";
  // glyphs (streaks, the ship's core) grouped per colour and row, one x per glyph
  const rows = new Map();
  for (const [fill, c, x, y] of rec.texts) {
    if (fill === BG || !inside(x + cw / 2, y)) continue;   // same colour as the screen: invisible
    const k = fill + "|" + n1(y); let g = rows.get(k); if (!g) rows.set(k, (g = { fill, y: n1(y), xs: [], cs: "" }));
    g.xs.push(Math.round(x)); g.cs += c;
  }
  for (const g of rows.values()) s += `<text x="${g.xs.join(" ")}" y="${g.y}" fill="${g.fill}">${g.cs}</text>`;
  frames.push(s);
}

const font = `font-family:Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace;font-size:${n1(cw / CELL_W)}px`;
let css = `.hj text{${font};dominant-baseline:central;white-space:pre}`;
if (!STATIC) css += `.hj>g{visibility:hidden;animation:hj ${PERIOD}s steps(1,end) infinite}` +
  `@keyframes hj{0%{visibility:visible}${n1(100 / N * 1.0001)}%,100%{visibility:hidden}}`;
const body = frames.map((f, i) => `<g${STATIC ? "" : ` style="animation-delay:${(i / FPS - PERIOD).toFixed(2)}s"`}>${f}</g>`).join("");
process.stdout.write(`<style>${css}</style><g class="hj" fill="none" stroke-linecap="round" stroke-dasharray="0 1" shape-rendering="geometricPrecision">${body}</g>`);
