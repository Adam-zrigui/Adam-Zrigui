#!/usr/bin/env python3
"""
Builds dark_mode.svg and light_mode.svg (a neofetch-style profile card).

  python build.py              # uses GITHUB_TOKEN if set, else public REST API
  python build.py --invert     # flip the ASCII brightness (try if your face looks "negative")

Edit the CONFIG section below to change what the card says.
"""
import datetime
import json
import os
import sys
import urllib.request
from html import escape

# ───────────────────────────── CONFIG ─────────────────────────────
USERNAME = "Adam-zrigui"
TITLE = "adam@zrigui"
BIRTHDAY = None  # e.g. datetime.date(2003, 5, 17). Leave None to hide the Uptime line.

# ("key", "value")  |  ("section", "Title")  |  None = blank line
INFO = [
    ("OS", "Linux"),
    ("Role", "Fullstack Engineer"),
    ("Location", "Gabes, Tunisia"),
    ("Editor", "Neovim"),
    None,
    ("Languages.Programming", "TypeScript, JavaScript, Lua"),
    ("Languages.Computer", "HTML, CSS, JSON, Prisma"),
    ("Languages.Real", "Arabic, French, English"),  # <- edit me
    None,
    ("Stack.Frontend", "Next.js, React, Tailwind"),
    ("Stack.Backend", "Node.js, Prisma, PostgreSQL, Redis"),
    ("Stack.Cloud", "AWS, Docker, Firebase, Vercel"),
    None,
    ("section", "Projects"),
    ("CoreVita", "DICOM medical imaging platform"),
    ("SmartBudget", "Financial SaaS with AI advisor"),
    ("Vita Ring", "Medication adherence (WIP)"),
    None,
    ("section", "Contact"),
    ("Email", "zriguiadam@gmail.com"),
    ("LinkedIn", "adam-zrigui-2b6a65240"),
    ("Live", "corevita.vercel.app"),
    None,
    ("section", "GitHub Stats"),
    # filled in automatically: Repos / Stars / Followers / Commits
]

ART_FILE = "ascii-art.txt"
WIDTH_CHARS = 62  # characters per info row (all rows are padded to this)

THEMES = {
    "dark_mode.svg": dict(bg="#0d1117", art="#c9d1d9", key="#ffa657", val="#a5d6ff", dots="#6e7681"),
    "light_mode.svg": dict(bg="#f6f8fa", art="#24292f", key="#953800", val="#0a3069", dots="#8c959f"),
}
# ──────────────────────────────────────────────────────────────────


def api(url, token=None, data=None):
    headers = {"User-Agent": "profile-card", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def gql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    out = api("https://api.github.com/graphql", token, body)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def fetch_stats(token):
    """Returns dict: repos, stars, followers, commits (commits may be 'n/a')."""
    try:
        if token:
            q = """query($l:String!,$after:String){user(login:$l){createdAt followers{totalCount}
              repositories(ownerAffiliations:OWNER,first:100,after:$after){totalCount
              pageInfo{hasNextPage endCursor} nodes{stargazerCount}}}}"""
            repos = stars = 0
            after = None
            while True:
                u = gql(q, {"l": USERNAME, "after": after}, token)["user"]
                repos = u["repositories"]["totalCount"]
                stars += sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
                pi = u["repositories"]["pageInfo"]
                if not pi["hasNextPage"]:
                    break
                after = pi["endCursor"]
            followers = u["followers"]["totalCount"]
            start = int(u["createdAt"][:4])
            commits = 0
            cq = """query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){
              contributionsCollection(from:$f,to:$t){totalCommitContributions}}}"""
            for y in range(start, datetime.date.today().year + 1):
                d = gql(cq, {"l": USERNAME, "f": f"{y}-01-01T00:00:00Z", "t": f"{y}-12-31T23:59:59Z"}, token)
                commits += d["user"]["contributionsCollection"]["totalCommitContributions"]
            return dict(repos=repos, stars=stars, followers=followers, commits=commits)
        # No token: public REST API (no commit count)
        u = api(f"https://api.github.com/users/{USERNAME}")
        stars, page = 0, 1
        while True:
            rs = api(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}")
            stars += sum(r["stargazers_count"] for r in rs)
            if len(rs) < 100:
                break
            page += 1
        return dict(repos=u["public_repos"], stars=stars, followers=u["followers"], commits="n/a")
    except Exception as e:  # keep the card buildable even if the API is down
        print("stats fetch failed:", e, file=sys.stderr)
        return dict(repos=60, stars="n/a", followers=2, commits="n/a")  # last-known fallback


def uptime(born):
    t = datetime.date.today()
    y, m, d = t.year - born.year, t.month - born.month, t.day - born.day
    if d < 0:
        m -= 1
        prev_month_end = t.replace(day=1) - datetime.timedelta(days=1)
        d += prev_month_end.day
    if m < 0:
        y -= 1
        m += 12
    return f"{y} years, {m} months, {d} days"


def load_art(invert):
    lines = open(ART_FILE, encoding="utf-8").read().rstrip("\n").split("\n")
    lines = [l.rstrip() for l in lines]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    margin = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
    lines = [l[margin:] for l in lines]
    if invert:
        ramp = ".:-=+*#%@"
        flip = {c: ramp[-1 - i] for i, c in enumerate(ramp)}
        lines = ["".join(flip.get(c, c) for c in l) for l in lines]
    return lines


def info_rows(stats):
    rows = []
    if BIRTHDAY:
        rows.append(("Uptime", uptime(BIRTHDAY)))
    rows = INFO[:1] + rows + INFO[1:]
    rows += [
        ("Repos", str(stats["repos"])),
        ("Stars", str(stats["stars"])),
        ("Followers", str(stats["followers"])),
        ("Commits", str(stats["commits"])),
    ]
    return rows


def build(art, rows, theme):
    ART_FS, INFO_FS = 9, 14
    art_cw, info_cw = ART_FS * 0.615, INFO_FS * 0.615
    art_lh, info_lh = ART_FS * 1.15, INFO_FS * 1.5
    pad, gap = 24, 40

    art_w = max(len(l) for l in art) * art_cw
    art_h = len(art) * art_lh
    info_x = pad + art_w + gap
    n_info = len(rows) + 1
    info_h = n_info * info_lh
    W = info_x + WIDTH_CHARS * info_cw + pad
    H = max(art_h, info_h) + pad * 2

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
           '<style>text{font-family:ui-monospace,SFMono-Regular,Consolas,"DejaVu Sans Mono","Courier New",monospace;white-space:pre}'
           f'.a{{fill:{theme["art"]};font-size:{ART_FS}px}}.k{{fill:{theme["key"]};font-size:{INFO_FS}px;font-weight:bold}}'
           f'.v{{fill:{theme["val"]};font-size:{INFO_FS}px}}.d{{fill:{theme["dots"]};font-size:{INFO_FS}px}}</style>',
           f'<rect width="100%" height="100%" rx="12" fill="{theme["bg"]}"/>']

    # ASCII art (vertically centred)
    y0 = (H - art_h) / 2 + ART_FS
    out.append('<text class="a" xml:space="preserve">')
    for i, l in enumerate(art):
        out.append(f'<tspan x="{pad}" y="{y0 + i * art_lh:.1f}">{escape(l)}</tspan>')
    out.append("</text>")

    # Info panel
    y = (H - info_h) / 2 + info_lh
    def line(inner):
        nonlocal y
        out.append(f'<text x="{info_x:.1f}" y="{y:.1f}" xml:space="preserve">{inner}</text>')
        y += info_lh

    head = f"{TITLE} "
    line(f'<tspan class="k">{escape(TITLE)}</tspan><tspan class="d"> {"-" * (WIDTH_CHARS - len(head))}</tspan>')
    for r in rows:
        if r is None:
            y += info_lh
        elif r[0] == "section":
            t = f"- {r[1]} "
            line(f'<tspan class="k">{escape(t)}</tspan><tspan class="d">{"-" * (WIDTH_CHARS - len(t))}</tspan>')
        else:
            k, v = r[0] + ":", r[1]
            n = WIDTH_CHARS - len(k) - len(v) - 2
            assert n >= 1, f"row too long: {r}"
            line(f'<tspan class="k">{escape(k)}</tspan><tspan class="d"> {"." * n} </tspan><tspan class="v">{escape(v)}</tspan>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    stats = fetch_stats(token)
    print("stats:", stats)
    art = load_art("--invert" in sys.argv)
    rows = info_rows(stats)
    for fname, theme in THEMES.items():
        open(fname, "w", encoding="utf-8").write(build(art, rows, theme))
        print("wrote", fname)
