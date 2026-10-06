#!/usr/bin/env python3
"""Builds assets/fetch.svg: retro dim-brown CRT terminal with live GitHub data.
No dependencies. Set GITHUB_TOKEN to avoid API rate limits (the Action does)."""
import os, re, sys, json, time, datetime as dt, urllib.request

USER = "pedroamarop"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "fetch.svg")
STATIC = "--static" in sys.argv          # preview mode: everything visible, no filters
MOCK = os.environ.get("MOCK_EVENTS")      # layout testing only

def get(url, api=False, data=None, tries=6):
    h = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    tok = os.environ.get("GITHUB_TOKEN")
    if api and tok: h["Authorization"] = f"Bearer {tok}"
    if data: h["Content-Type"] = "application/json"
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=40) as r:
                return r.read().decode()
        except Exception:
            if i == tries-1: raise
            time.sleep(3 + i*4)

def days_from_html():
    html = get(f"https://github.com/users/{USER}/contributions")
    tips = {m.group(1): m.group(2) for m in re.finditer(r'for="(contribution-day-component-\d+-\d+)"[^>]*>\s*([^<]*)', html)}
    out_ = []
    for m in re.finditer(r'<td[^>]*data-date="([\d-]+)"[^>]*id="(contribution-day-component-\d+-\d+)"[^>]*data-level="(\d)"', html):
        n = re.match(r"(\d+) contribution", tips.get(m.group(2), ""))
        out_.append((dt.date.fromisoformat(m.group(1)), int(m.group(3)), int(n.group(1)) if n else 0))
    return out_

def days_from_graphql():
    q = 'query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount contributionLevel}}}}}}'
    r = json.loads(get("https://api.github.com/graphql", api=True, data=json.dumps({"query": q, "variables": {"u": USER}}).encode()))
    lv = {"NONE":0,"FIRST_QUARTER":1,"SECOND_QUARTER":2,"THIRD_QUARTER":3,"FOURTH_QUARTER":4}
    wk = r["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(dt.date.fromisoformat(d["date"]), lv[d["contributionLevel"]], d["contributionCount"]) for w in wk for d in w["contributionDays"]]

# ---------- live data ----------
days = []
for src in (days_from_html, days_from_graphql):
    try:
        days = src()
        if days: break
    except Exception as e:
        print(f"{src.__name__} failed: {e}", file=sys.stderr)
if not days:
    print("no contribution data available, keeping the existing image", file=sys.stderr)
    sys.exit(0)
days.sort()
total = sum(c for _,_,c in days)
longest = cur = 0
for _,_,c in days:
    cur = cur + 1 if c else 0; longest = max(longest, cur)
streak = 0
for _,_,c in reversed(days):
    if c: streak += 1
    elif streak == 0 and _ == days[-1][0]: continue
    else: break
active = [x for x in days if x[2] > 0]
last_active = active[-1] if active else None

push = None
try:
    if MOCK: raise RuntimeError
    ev = json.loads(get(f"https://api.github.com/users/{USER}/events/public", api=True))
    for e in ev:
        if e["type"] == "PushEvent" and not e["repo"]["name"].endswith("/" + USER):
            cm = (e["payload"].get("commits") or [{}])[-1].get("message", "").split("\n")[0]
            push = (e["repo"]["name"].split("/")[-1], e["created_at"], cm); break
except Exception:
    pass
repos = []
try:
    if MOCK: raise RuntimeError
    rl = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", api=True))
    repos = [(r["name"], r["stargazers_count"], r.get("description") or "", r.get("archived", False))
             for r in rl if not r.get("fork")]
except Exception:
    pass
if MOCK: repos = [("minimal-waybar-themes",215,"Minimal Waybar Themes for omarchy.org",False),("anomshell",97,"Quickshell configuration for Omarchy OS",True),
    ("omarchy-rainynight-theme",41,"Rainy night theme for Omarchy",False),("dotfiles",37,"My Dotfiles",False),("omarchy-aureth-theme",26,"Aureth theme for Omarchy",False)]
repos.sort(key=lambda r: -r[1]); repos = repos[:5]
if MOCK: push = ("omarchy-rainynight-theme", "2026-10-02T04:10:00Z", "fix waybar module spacing")

# ---------- layout ----------
CW, FS, LH, W, X0, Y0 = 8.4, 14, 22, 860, 40, 66
BG, AMB, MID, DIM, KEY, HI = "#18181a", "#6a6a6c", "#5a5a5c", "#3f3f41", "#5a5a5c", "#9a9a9c"
HEAT = ["#222224", "#38383a", "#4e4e50", "#6a6a6c", "#9a9a9c"]
GRAPH = os.environ.get("GRAPH", "heatmap")   # "chart" (weekly bars) or "heatmap"
FONT = "'JetBrains Mono','Fira Code','DejaVu Sans Mono',Consolas,Menlo,monospace"
esc = lambda s: s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
out, clips = [], []
def show(t): return "" if STATIC else f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
def grp(t, inner): return f'<g opacity="{1 if STATIC else 0}">{show(t)}{inner}</g>'
PROMPT = "pedro@dev:~$ "; PW = len(PROMPT)*CW

def typed(row, t, cmd, speed=0.06):
    y = Y0 + row*LH; n = max(len(cmd), 1); cx = X0 + PW; cid = f"c{row}"
    if STATIC: rect = f'<rect x="{cx}" y="{y-FS}" width="{n*CW+2}" height="{LH}"/>'
    else:
        vals = ";".join(f"{i*CW:.1f}" for i in range(n+1))
        rect = f'<rect x="{cx}" y="{y-FS}" width="0" height="{LH}"><animate attributeName="width" values="{vals}" calcMode="discrete" begin="{t+0.2:.2f}s" dur="{n*speed:.2f}s" fill="freeze"/></rect>'
    clips.append(f'<clipPath id="{cid}">{rect}</clipPath>')
    out.append(grp(t, f'<text x="{X0}" y="{y}" fill="{MID}">{PROMPT}</text><text x="{cx}" y="{y}" fill="{HI}" clip-path="url(#{cid})">{esc(cmd)}</text>'))
    return t + 0.2 + len(cmd)*speed

def kv(row, t, k, v, vc=AMB):
    y = Y0 + row*LH
    out.append(grp(t, f'<text x="{X0}" y="{y}" fill="{KEY}">{k}</text><text x="{X0+10*CW}" y="{y}" fill="{vc}">{esc(v)}</text>'))

def plain(row, t, s, c=AMB, x=X0):
    out.append(grp(t, f'<text x="{x}" y="{Y0+row*LH}" fill="{c}" xml:space="preserve">{esc(s)}</text>'))

now = dt.datetime.now(dt.timezone.utc)
row, t = 0, 0.2
plain(row, t, f"Last login: {now:%a %b %-d %H:%M} UTC on tty1", DIM); row += 2
t = typed(row, 0.6, "fetch"); row += 1; t += 0.3
plain(row, t, "pedro@dev", HI); row += 1
plain(row, t, "─"*40, DIM); row += 1; t += 0.1
for k, v in [("os","macOS"),("shell","zsh"),("editor","Claude Code"),
             ("doing","IA aplicada · AWS Bedrock/AgentCore · back-end serverless"),
             ("github","github.com/pedroamarop")]:
    kv(row, t, k, v, HI if k == "github" else AMB); row += 1; t += 0.1
row += 1

# contribution graph
plain(row, t, f"contrib   {total} in the last year   streak {streak}d   best {longest}d", AMB); row += 1; t += 0.1
P, S = 14, 11
gx, gy = X0 + 34, Y0 + row*LH + 4
first = days[0][0]
off = (first.weekday()+1) % 7                       # Sunday-first
ncols = (off + len(days) + 6)//7
months, lastm, lastc = [], None, -9
anim_cell = lambda b: "" if STATIC else f'<animate attributeName="opacity" from="0" to="1" begin="{b:.2f}s" dur="0.01s" fill="freeze"/>'
hide = "" if STATIC else ' opacity="0"'
def month_labels(ytxt):
    global lastm, lastc
    for i,(d,l,c) in enumerate(days):
        col, r = (off+i)//7, (off+i)%7
        if r == 0 and d.month != lastm and col - lastc >= 3:
            lastc = col; lastm = d.month
            months.append(f'<text x="{gx+col*P}" y="{ytxt}" fill="{DIM}" style="font-size:11px">{d:%b}</text>')
if GRAPH == "heatmap":
    cells = []
    for i,(d,l,c) in enumerate(days):
        col, r = (off+i)//7, (off+i)%7
        cells.append(f'<rect x="{gx+col*P}" y="{gy+r*P}" width="{S}" height="{S}" fill="{HEAT[l]}"{hide}>{anim_cell(t+col*0.03)}</rect>')
    month_labels(gy-6)
    labels = "".join(f'<text x="{X0}" y="{gy+r*P+S-1}" fill="{DIM}" style="font-size:11px">{n}</text>' for r,n in ((1,"Mon"),(3,"Wed"),(5,"Fri")))
    out.append(f'<g>{"".join(months)}{labels}{"".join(cells)}</g>')
    row += 1 + 7*P//LH + 1; t += ncols*0.03 + 0.2
    ly = Y0 + row*LH - 8
    leg = f'<text x="{gx}" y="{ly}" fill="{DIM}" style="font-size:11px">less</text>' + "".join(
          f'<rect x="{gx+32+i*(S+3)}" y="{ly-S+1}" width="{S}" height="{S}" fill="{c}"/>' for i,c in enumerate(HEAT)) + \
          f'<text x="{gx+32+5*(S+3)+4}" y="{ly}" fill="{DIM}" style="font-size:11px">more</text>'
    out.append(grp(t, leg)); row += 1; t += 0.2
else:
    # weekly activity chart: one column per week, stacked cells like a btop graph
    weeks = [0]*ncols
    for i,(d,l,c) in enumerate(days): weeks[(off+i)//7] += c
    mx = max(weeks) or 1
    ROWS, CH, CP = 8, 6, 8                           # 8 cells tall, 6px cells on an 8px pitch
    base = gy + ROWS*CP
    bars = []
    for col, n in enumerate(weeks):
        h = 0 if n == 0 else max(1, round(n/mx*ROWS))
        for k in range(ROWS):
            lit = k < h
            if not lit and k > 0: continue            # only the baseline cell shows for empty weeks
            colr = (HI if col == ncols-1 else (HEAT[3] if k >= h-2 and h else HEAT[2])) if lit else HEAT[0]
            if lit and col == ncols-1: colr = HI
            bars.append(f'<rect x="{gx+col*P}" y="{base-(k+1)*CP+1}" width="{S}" height="{CH}" fill="{colr}"{hide}>{anim_cell(t+col*0.03)}</rect>')
    month_labels(base + 14)
    ylab = f'<text x="{X0}" y="{gy+9}" fill="{DIM}" style="font-size:11px">{mx}</text><text x="{X0}" y="{base-1}" fill="{DIM}" style="font-size:11px">0</text>'
    out.append(f'<g>{ylab}{"".join(bars)}{"".join(months)}</g>')
    row += 1 + (ROWS*CP + 34)//LH + 1; t += ncols*0.03 + 0.2
    out.append(grp(t, f'<text x="{gx}" y="{base+32}" fill="{DIM}" style="font-size:11px">commits per week · peak {mx}</text>')); row += 1; t += 0.2

# live lines
if last_active:
    d,_,c = last_active
    kv(row, t, "active", f"{d:%Y-%m-%d}  ({c} contribution{'s' if c!=1 else ''})"); row += 1; t += 0.12
if push:
    repo, ts, msg = push
    when = dt.datetime.fromisoformat(ts.replace("Z","+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    kv(row, t, "last repo", repo, HI); row += 1; t += 0.12
    kv(row, t, "last push", when); row += 1; t += 0.12
    if msg: kv(row, t, "commit", f"“{msg[:58]}”", MID); row += 1; t += 0.12
else:
    kv(row, t, "last repo", "waiting for first sync", MID); row += 1; t += 0.12
row += 1

# interests
plain(row, t, "interesses", AMB); row += 1; t += 0.1
for it in ["aws", "ia", "python", "full-stack", "devops", "machine learning"]:
    plain(row, t, "› " + it, HI); row += 1; t += 0.1
row += 1

# final prompt
t = typed(row, t, "", 0.1)
cy = Y0 + row*LH; cx = X0 + PW
cur = f'<rect x="{cx}" y="{cy-FS+1}" width="{CW}" height="{FS+2}" fill="{HI}"'
cur += '/>' if STATIC else f' opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s"/><animate attributeName="opacity" values="1;0" calcMode="discrete" dur="1.1s" begin="{t:.2f}s" repeatCount="indefinite"/></rect>'
out.append(cur)
H = Y0 + (row+1)*LH + 18

glow = "" if STATIC else 'filter="url(#glow)"'
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="pedro@dev terminal" shape-rendering="crispEdges">
<defs>
<filter id="glow" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="0.9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" y="2" fill="#000" opacity="0.28"/></pattern>
<radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset="60%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.65"/></radialGradient>
<clipPath id="screen"><rect x="14" y="14" width="{W-28}" height="{H-28}"/></clipPath>
{"".join(clips)}
</defs>
<style>text{{font-family:{FONT};font-size:{FS}px;white-space:pre}}</style>
<rect width="{W}" height="{H}" fill="#202022" stroke="#2c2c2e" stroke-width="2"/>
<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="{BG}"/>
<g clip-path="url(#screen)">
<g {glow}>{"".join(out)}</g>
<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="url(#scan)"/>
<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="url(#vig)"/>
</g>
<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="none" stroke="#000" stroke-opacity="0.6" stroke-width="2"/>
</svg>'''
dest = "/tmp/fetch_static.svg" if STATIC else OUT
open(dest, "w").write(svg); print("wrote", dest)

if not STATIC:
    rd = os.path.join(os.path.dirname(__file__), "..", "README.md")
    open(rd, "w").write(f'<div align="center">\n\n<img src="assets/fetch.svg?v={int(now.timestamp())}" alt="pedro@dev terminal" width="860" />\n\n</div>\n')
