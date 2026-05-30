"""
server.py — Marginalia local development server
================================================

USAGE:
    cd marginalia
    pip install flask
    python server.py            # dev server at localhost:5000
    python server.py --build    # write static posts.html, problems.html for GitHub Pages

GITHUB PAGES DEPLOYMENT:
    1. Run:  python server.py --build
    2. Commit all files including the generated posts.html and problems.html
    3. git push

    URL forms served identically by this server:
      /              → index.html
      /index.html    → index.html  (logo click)
      /posts         → listing page
      /posts.html    → listing page  (GitHub Pages static URL)
      /posts/<slug>  → individual post
      /posts/<slug>.html → same post
      /notes         → Marginal Notes journal
      /notes.html    → same
      /problems      → problems listing page
      /problems.html → problems listing page
      /static/<file> → static assets (comment-policy.html, etc.)
"""

import html
import os
import re
import sys
from flask import Flask, send_from_directory, abort

app = Flask(__name__, static_folder=None)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR   = os.path.join(BASE_DIR, "posts")
CSS_DIR     = os.path.join(BASE_DIR, "css")
JS_DIR      = os.path.join(BASE_DIR, "js")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
STATIC_DIR  = os.path.join(BASE_DIR, "static")

# Master tag list — order controls the filter row in the listing page.
# Tags with no posts still appear as normal buttons; clicking them shows
# "Essays on this topic are coming soon." No special styling is applied.
# TO ADD A NEW TAG: append a (css-class, display-label) tuple here.
ALL_TAGS = [
    ("tag-analysis",       "Analysis"),
    ("tag-algebra",        "Algebra"),
    ("tag-topology",       "Topology"),
    ("tag-geometry",       "Geometry"),
    ("tag-number-theory",  "Number Theory"),
    ("tag-logic",          "Logic"),
    ("tag-probability",    "Probability"),
]

# Problem source tags — used by build_problems_html() and the Problems listing page.
# TO ADD A NEW SOURCE: append a (css-class, display-label) tuple here AND add the
# corresponding .tag-* colour block to css/layout.css.
PROBLEM_SOURCES = [
    ("tag-isi-cmi",  "ISI / CMI"),
    ("tag-olympiad", "Olympiads"),
    ("tag-putnam",   "Putnam"),
]

# ── HTML comment stripper ──────────────────────────────────────────────────────
# All metadata regexes run against a comment-stripped copy of the post source.
# This prevents documentation comments that reference bare HTML tag names (e.g.
# "edit the <h1> below" in a template comment block) from being matched by the
# metadata regexes, which previously caused garbled card titles rendered as a
# solid white horizontal bar from Unicode box-drawing characters.
_RE_HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)


def _strip_comments(src):
    """Return src with all HTML comments removed."""
    return _RE_HTML_COMMENT.sub('', src)


# ── Post metadata extraction ──────────────────────────────────────────────────

def get_posts():
    """
    Scans posts/ and returns a list of metadata dicts, newest first.
    Files prefixed with underscore (templates, drafts) are skipped.

    tag_class: the specific tag class only, e.g. 'tag-algebra'
               (the base 'tag' class is stripped to avoid duplicate class names
               when the card HTML adds it back as <span class="tag {tag_class}">)
    """
    posts = []
    if not os.path.isdir(POSTS_DIR):
        return posts

    for fname in sorted(os.listdir(POSTS_DIR), reverse=True):
        if not fname.endswith(".html") or fname.startswith("_"):
            continue

        fpath = os.path.join(POSTS_DIR, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            continue

        # Strip HTML comments before ALL metadata parsing.
        src = _strip_comments(raw)

        # Title — strip inner HTML tags from first <h1>
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", src, re.S | re.I)
        title = (
            re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
            if title_m
            else fname.replace("-", " ").replace(".html", "").title()
        )

        # Tag — first <span class="tag tag-X">Label</span>
        # We extract only the specific tag variant (e.g. "tag-algebra"),
        # not the base "tag" class, to prevent double-class in the card HTML.
        tag_m = re.search(
            r'<span\s+class="(?:tag\s+)?(tag-[^"]+)"[^>]*>(.*?)</span>',
            src, re.S | re.I
        )
        # If not found with specific variant, fall back to any tag span
        if not tag_m:
            tag_m = re.search(
                r'<span\s+class="(tag[^"]*)"[^>]*>(.*?)</span>',
                src, re.S | re.I
            )

        raw_class  = tag_m.group(1).strip() if tag_m else ""
        # Strip leading "tag " so we get just "tag-algebra", not "tag tag-algebra"
        tag_class  = re.sub(r"^tag\s+", "", raw_class).strip() if raw_class else "tag-analysis"
        tag_label  = re.sub(r"<[^>]+>", "", tag_m.group(2)).strip() if tag_m else ""

        # Date — first <span> inside the element with class="post-meta"
        meta_m = re.search(
            r'class="post-meta"[^>]*>.*?<span>(.*?)</span>', src, re.S | re.I
        )
        date_str = meta_m.group(1).strip() if meta_m else ""

        # Convert "Month DD, YYYY" → RFC-822 format required by RSS 2.0 spec.
        rfc822_date = date_str
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%B %d, %Y")
            rfc822_date = dt.strftime("%a, %d %b %Y 00:00:00 +0000")
        except (ValueError, ImportError):
            pass  # keep raw date_str as fallback

        # Read time — estimated from post-body word count at 200 wpm
        body_m = re.search(r'class="post-body"[^>]*>(.*?)</div>', src, re.S | re.I)
        read_time = ""
        if body_m:
            words   = re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", "", body_m.group(1)))
            minutes = max(1, round(len(words) / 200))
            read_time = f"{minutes} min read"

        # Excerpt — first <p> in .post-body, stripped, max 175 chars
        exc_m = re.search(r'class="post-body"[^>]*>.*?<p>(.*?)</p>', src, re.S | re.I)
        excerpt = ""
        if exc_m:
            excerpt = re.sub(r"<[^>]+>", "", exc_m.group(1)).strip()
            if len(excerpt) > 175:
                excerpt = excerpt[:175].rsplit(" ", 1)[0] + "…"

        posts.append({
            "slug":       fname.replace(".html", ""),
            "title":      title,
            "tag_class":  tag_class,
            "tag_label":  tag_label,
            "date":       date_str,       # "May 12, 2026"  — used in card UI
            "rfc822_date": rfc822_date,   # "Tue, 12 May 2026 00:00:00 +0000" — used in RSS
            "read_time":  read_time,
            "excerpt":    excerpt,
        })

    return posts


# ── Listing page HTML builder ─────────────────────────────────────────────────

def build_listing_html(posts):
    """
    Returns the full HTML for the essays listing page.
    Used by Flask routes and --build static export.

    Tag filter buttons:
      - Tags WITH posts: standard buttons
      - Tags WITHOUT posts: identical buttons; clicking them shows
        "Essays on this topic are coming soon." via #empty-filter-msg.

    TO ADD A TAG: add it to ALL_TAGS at the top of this file.
    TO STYLE THE PAGE: edit the <style> block below.
    """
    used_tags = set()
    for p in posts:
        for cls in p["tag_class"].split():
            if cls.startswith("tag-") and cls != "tag":
                used_tags.add(cls)

    # Build post cards
    cards_html = ""
    if posts:
        for p in posts:
            rt = (
                f'<span class="pc-dot">·</span><span>{p["read_time"]}</span>'
                if p["read_time"] else ""
            )
            # HTML-escape all post-author-controlled fields to prevent XSS.
            e_title     = html.escape(p['title'])
            e_excerpt   = html.escape(p['excerpt'])
            e_tag_label = html.escape(p['tag_label'])
            e_date      = html.escape(p['date'])
            e_tag_class = html.escape(p['tag_class'])
            e_slug      = html.escape(p['slug'])
            cards_html += f"""
        <div class="post-card" data-tag="{e_tag_class}"
             onclick="location.href='posts/{e_slug}.html'">
          <span class="tag {e_tag_class}">{e_tag_label}</span>
          <div class="pc-title">{e_title}</div>
          <div class="pc-excerpt">{e_excerpt}</div>
          <div class="pc-meta"><span>{e_date}</span>{rt}</div>
        </div>"""
    else:
        cards_html = '<p class="empty-msg">.</p>'

    # All filter buttons look identical regardless of whether the tag has posts.
    filter_btns = '      <button class="filter-btn active" data-filter="all">All</button>\n'
    for tag_key, tag_label in ALL_TAGS:
        filter_btns += (
            f'      <button class="filter-btn" data-filter="{tag_key}">'
            f'{tag_label}</button>\n'
        )

    count  = len(posts)
    plural = "s" if count != 1 else ""

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>All Essays — Marginalia</title>
  <meta name="description" content="All essays on Marginalia — a mathematics blog by Promit Dutta covering analysis, algebra, topology, number theory, and logic."/>
  <link rel="canonical" href="https://promit-dutta.github.io/marginalia/posts.html"/>
  <script>
    (function(){{
      var s=localStorage.getItem('mg-theme');
      var d=window.matchMedia('(prefers-color-scheme:dark)').matches;
      document.documentElement.setAttribute('data-theme',s||(d?'dark':'light'));
    }})();
  </script>
  <link rel="icon" href="favicon.svg" type="image/svg+xml"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=EB+Garamond:ital,wght@0,400;1,400&family=DM+Sans:wght@300;400&display=swap"/>
  <link rel="stylesheet" href="css/base.css"/>
  <link rel="stylesheet" href="css/layout.css"/>
  <style>
    body {{
      background: var(--bg); color: var(--text);
      min-height: 100vh; display: flex; flex-direction: column;
      transition: background var(--t-slow), color var(--t-slow);
    }}
    .listing-wrap {{
      max-width: 760px; margin: 0 auto;
      padding: 2.5rem 2rem 5rem; flex: 1;
    }}
    .listing-header {{
      margin-bottom: 2rem; padding-bottom: 1.2rem;
      border-bottom: 0.5px solid var(--border);
    }}
    .listing-title {{
      font-family: var(--font-display); font-size: 32px; font-weight: 300;
      color: var(--text); letter-spacing: 0.02em;
    }}
    .listing-count {{
      font-family: var(--font-serif); font-style: italic;
      font-size: 14px; color: var(--text-3); margin-top: 4px;
    }}
    .filter-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 2rem; }}
    .filter-btn {{
      font-family: var(--font-sans); font-size: 11px; letter-spacing: 0.09em;
      text-transform: uppercase; padding: 6px 16px;
      border: 1px solid var(--border-2); background: transparent;
      color: var(--text-3); border-radius: 3px; cursor: pointer;
      position: relative; outline: none;
      transition: background var(--t-base), color var(--t-base),
                  border-color var(--t-base), box-shadow var(--t-base);
    }}
    .filter-btn::after {{
      content: ''; position: absolute; inset: -4px;
      border: 0.5px solid transparent; border-radius: 5px;
      transition: border-color var(--t-base); pointer-events: none;
    }}
    .filter-btn:hover {{
      color: var(--text); border-color: var(--border-3); background: var(--bg-2);
    }}
    .filter-btn:hover::after {{ border-color: var(--border); }}
    .filter-btn.active {{
      background: var(--text); color: var(--bg); border-color: var(--text);
      box-shadow: 0 0 0 3px var(--bg-2), 0 0 10px 1px rgba(80,120,55,0.15);
    }}
    .filter-btn.active::after {{ border-color: var(--border-2); }}
    [data-theme="dark"] .filter-btn.active {{
      box-shadow: 0 0 0 3px var(--bg-2), 0 0 14px 2px rgba(120,180,90,0.22);
    }}
    .filter-btn:focus-visible {{ outline: 2px solid var(--text-2); outline-offset: 3px; }}
    .cards-grid {{
      display: grid; grid-template-columns: repeat(auto-fill, minmax(300px,1fr)); gap: 16px;
    }}
    .post-card {{
      background: var(--card-bg); border: 0.5px solid var(--border);
      border-radius: 8px; padding: 1.4rem 1.5rem; cursor: pointer;
      transition: background var(--t-base), border-color var(--t-base), transform var(--t-fast);
    }}
    .post-card:hover {{
      background: var(--card-hover); border-color: var(--border-3); transform: translateY(-2px);
    }}
    .post-card.hidden {{ display: none; }}
    .pc-title {{ font-family: var(--font-serif); font-size: 18px; font-weight: 400;
                color: var(--text); line-height: 1.4; margin: 8px 0 6px; }}
    .pc-excerpt {{ font-family: var(--font-sans); font-size: 13px; color: var(--text-3);
                  line-height: 1.65; margin-bottom: 12px; }}
    .pc-meta {{ font-family: var(--font-sans); font-size: 11px; color: var(--text-4);
               display: flex; gap: 8px; align-items: center; }}
    .pc-dot {{ opacity: 0.4; }}
    .empty-msg {{ font-family: var(--font-serif); font-style: italic; font-size: 18px;
                 color: var(--text-3); text-align: center; padding: 3rem 0; }}
    #empty-filter-msg {{
      display: none; font-family: var(--font-serif); font-style: italic;
      font-size: 17px; color: var(--text-3); text-align: center; padding: 3rem 0;
    }}
    .listing-footer {{
      border-top: 0.5px solid var(--border); padding: 1.2rem 2.5rem;
      display: flex; justify-content: space-between; align-items: center;
      font-family: var(--font-sans); font-size: 12px; color: var(--text-4);
    }}
    .listing-footer a {{ color: var(--text-3); transition: color var(--t-base); }}
    .listing-footer a:hover {{ color: var(--text); }}
    @media (max-width: 640px) {{
      .listing-wrap   {{ padding: 2rem 1.2rem 4rem; }}
      .cards-grid     {{ grid-template-columns: 1fr; }}
      .listing-title  {{ font-size: 26px; }}
      .listing-footer {{ flex-direction: column; gap: 0.5rem; text-align: center; }}
    }}
  </style>
</head>
<body>

  <nav id="main-nav">
    <a href="index.html" class="nav-logo">Marginalia</a>
    <input type="checkbox" id="nav-toggle"/>
    <label for="nav-toggle" class="nav-hamburger" aria-label="Menu">
      <span></span><span></span><span></span>
    </label>
    <ul class="nav-links">

      <li class="nav-has-dropdown">
        <button class="nav-dropdown-btn" aria-haspopup="true" aria-expanded="false">
          Essays
          <svg class="nav-chevron" width="9" height="5" viewBox="0 0 9 5" fill="none" aria-hidden="true">
            <path d="M1 1l3.5 3L8 1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div class="nav-dropdown-panel">
          <a href="posts.html" class="ndp-all">All essays</a>
          <span class="ndp-label">By topic</span>
          <a href="posts.html?tag=analysis">Analysis</a>
          <a href="posts.html?tag=algebra">Algebra</a>
          <a href="posts.html?tag=topology">Topology</a>
          <a href="posts.html?tag=geometry">Geometry</a>
          <a href="posts.html?tag=number-theory">Number Theory</a>
          <a href="posts.html?tag=logic">Logic</a>
          <a href="posts.html?tag=probability">Probability</a>
        </div>
      </li>

      <li class="nav-has-dropdown">
        <button class="nav-dropdown-btn" aria-haspopup="true" aria-expanded="false">
          Problems
          <svg class="nav-chevron" width="9" height="5" viewBox="0 0 9 5" fill="none" aria-hidden="true">
            <path d="M1 1l3.5 3L8 1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div class="nav-dropdown-panel">
          <a href="problems.html" class="ndp-all">All problems</a>
          <span class="ndp-label">By source</span>
          <a href="problems.html?source=isi-cmi">ISI / CMI</a>
          <a href="problems.html?source=olympiad">Olympiads</a>
          <a href="problems.html?source=putnam">Putnam</a>
        </div>
      </li>

      <li><a href="notes.html">Marginal Notes</a></li>
      <li><a href="index.html#about">About</a></li>

    </ul>
    <button id="theme-toggle" aria-label="Toggle dark mode">
      <svg id="icon-moon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
      <svg id="icon-sun" width="14" height="14" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round" style="display:none">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
    </button>
  </nav>

  <div class="listing-wrap">
    <div class="listing-header">
      <h1 class="listing-title">All essays</h1>
      <p class="listing-count">{count} piece{plural} so far</p>
    </div>

    <div class="filter-row" id="filters">
{filter_btns}
    </div>

    <div class="cards-grid" id="cards">
      {cards_html}
    </div>

    <p id="empty-filter-msg">Essays on this topic are coming soon.</p>
  </div>

  <footer class="listing-footer">
    <span style="font-family:var(--font-serif);font-style:italic;">
      "Mathematics is the art of giving the same name to different things." — Poincaré
    </span>
    <div style="display:flex;gap:1rem;">
      <a href="index.html">Home</a>
    </div>
  </footer>

  <script>
    (function(){{
      function syncIcon(t){{
        var m=document.getElementById('icon-moon'),s=document.getElementById('icon-sun');
        if(!m||!s)return;
        m.style.display=t==='dark'?'none':'block';
        s.style.display=t==='dark'?'block':'none';
      }}
      syncIcon(document.documentElement.getAttribute('data-theme'));
      document.getElementById('theme-toggle').addEventListener('click',function(){{
        var c=document.documentElement.getAttribute('data-theme');
        var n=c==='dark'?'light':'dark';
        document.documentElement.setAttribute('data-theme',n);
        localStorage.setItem('mg-theme',n);
        syncIcon(n);
      }});

      var filterBtns=document.querySelectorAll('.filter-btn');
      var cards=document.querySelectorAll('.post-card');
      var emptyMsg=document.getElementById('empty-filter-msg');

      function applyFilter(f){{
        var matched=0;
        cards.forEach(function(c){{
          var hide=f!=='all'&&!c.dataset.tag.includes(f);
          c.classList.toggle('hidden',hide);
          if(!hide)matched++;
        }});
        filterBtns.forEach(function(b){{
          b.classList.toggle('active',b.dataset.filter===f);
        }});
        if(emptyMsg){{
          emptyMsg.style.display=(matched===0&&f!=='all')?'block':'none';
        }}
      }}

      filterBtns.forEach(function(b){{
        b.addEventListener('click',function(){{applyFilter(b.dataset.filter);}});
      }});

      var urlTag=new URLSearchParams(window.location.search).get('tag');
      if(urlTag)applyFilter('tag-'+urlTag);
    }})();
  </script>

  <script src="js/nav-dropdown.js"></script>
</body>
</html>"""


# ── Problems listing page HTML builder ───────────────────────────────────────

def build_problems_html(posts):
    """
    Returns the full HTML for the problems listing page.
    Only shows posts whose tag_class is a problem source tag.
    Filters via ?source= URL parameter instead of ?tag=.

    TO ADD A SOURCE TAG: add it to PROBLEM_SOURCES at the top of this file,
    add the .tag-* colour block to css/layout.css, and tag the relevant posts.
    """
    PROBLEM_TAG_SET = {"tag-isi-cmi", "tag-olympiad", "tag-putnam"}
    problem_posts = [p for p in posts if p["tag_class"] in PROBLEM_TAG_SET]

    # Build post cards
    cards_html = ""
    if problem_posts:
        for p in problem_posts:
            rt = (
                f'<span class="pc-dot">·</span><span>{p["read_time"]}</span>'
                if p["read_time"] else ""
            )
            e_title     = html.escape(p['title'])
            e_excerpt   = html.escape(p['excerpt'])
            e_tag_label = html.escape(p['tag_label'])
            e_date      = html.escape(p['date'])
            e_tag_class = html.escape(p['tag_class'])
            e_slug      = html.escape(p['slug'])
            cards_html += f"""
        <div class="post-card" data-tag="{e_tag_class}"
             onclick="location.href='posts/{e_slug}.html'">
          <span class="tag {e_tag_class}">{e_tag_label}</span>
          <div class="pc-title">{e_title}</div>
          <div class="pc-excerpt">{e_excerpt}</div>
          <div class="pc-meta"><span>{e_date}</span>{rt}</div>
        </div>"""
    else:
        cards_html = '<p class="empty-msg">No problems posted yet.</p>'

    filter_btns = '      <button class="filter-btn active" data-filter="all">All</button>\n'
    for tag_key, tag_label in PROBLEM_SOURCES:
        filter_btns += (
            f'      <button class="filter-btn" data-filter="{tag_key}">'
            f'{tag_label}</button>\n'
        )

    count  = len(problem_posts)
    plural = "s" if count != 1 else ""

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>All Problems — Marginalia</title>
  <meta name="description" content="Competition problems and solutions on Marginalia — ISI/CMI, Olympiads, and Putnam, by Promit Dutta."/>
  <link rel="canonical" href="https://promit-dutta.github.io/marginalia/problems.html"/>
  <script>
    (function(){{
      var s=localStorage.getItem('mg-theme');
      var d=window.matchMedia('(prefers-color-scheme:dark)').matches;
      document.documentElement.setAttribute('data-theme',s||(d?'dark':'light'));
    }})();
  </script>
  <link rel="icon" href="favicon.svg" type="image/svg+xml"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=EB+Garamond:ital,wght@0,400;1,400&family=DM+Sans:wght@300;400&display=swap"/>
  <link rel="stylesheet" href="css/base.css"/>
  <link rel="stylesheet" href="css/layout.css"/>
  <style>
    html {{ overflow-y: scroll; }}
    body {{
      background: var(--bg); color: var(--text);
      min-height: 100vh; display: flex; flex-direction: column;
      transition: background var(--t-slow), color var(--t-slow);
    }}
    .listing-wrap {{
      max-width: 760px; margin: 0 auto;
      padding: 2.5rem 2rem 5rem; flex: 1;
    }}
    .listing-header {{
      margin-bottom: 2rem; padding-bottom: 1.2rem;
      border-bottom: 0.5px solid var(--border);
    }}
    .listing-title {{
      font-family: var(--font-display); font-size: 32px; font-weight: 300;
      color: var(--text); letter-spacing: 0.02em;
    }}
    .listing-count {{
      font-family: var(--font-serif); font-style: italic;
      font-size: 14px; color: var(--text-3); margin-top: 4px;
    }}
    .filter-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 2rem; }}
    .filter-btn {{
      font-family: var(--font-sans); font-size: 11px; letter-spacing: 0.09em;
      text-transform: uppercase; padding: 6px 16px;
      border: 1px solid var(--border-2); background: transparent;
      color: var(--text-3); border-radius: 3px; cursor: pointer;
      position: relative; outline: none;
      transition: background var(--t-base), color var(--t-base),
                  border-color var(--t-base), box-shadow var(--t-base);
    }}
    .filter-btn::after {{
      content: ''; position: absolute; inset: -4px;
      border: 0.5px solid transparent; border-radius: 5px;
      transition: border-color var(--t-base); pointer-events: none;
    }}
    .filter-btn:hover {{
      color: var(--text); border-color: var(--border-3); background: var(--bg-2);
    }}
    .filter-btn:hover::after {{ border-color: var(--border); }}
    .filter-btn.active {{
      background: var(--text); color: var(--bg); border-color: var(--text);
      box-shadow: 0 0 0 3px var(--bg-2), 0 0 10px 1px rgba(80,120,55,0.15);
    }}
    .filter-btn.active::after {{ border-color: var(--border-2); }}
    [data-theme="dark"] .filter-btn.active {{
      box-shadow: 0 0 0 3px var(--bg-2), 0 0 14px 2px rgba(120,180,90,0.22);
    }}
    .filter-btn:focus-visible {{ outline: 2px solid var(--text-2); outline-offset: 3px; }}
    .cards-grid {{
      display: grid; grid-template-columns: repeat(auto-fill, minmax(300px,1fr)); gap: 16px;
    }}
    .post-card {{
      background: var(--card-bg); border: 0.5px solid var(--border);
      border-radius: 8px; padding: 1.4rem 1.5rem; cursor: pointer;
      transition: background var(--t-base), border-color var(--t-base), transform var(--t-fast);
    }}
    .post-card:hover {{
      background: var(--card-hover); border-color: var(--border-3); transform: translateY(-2px);
    }}
    .post-card.hidden {{ display: none; }}
    .pc-title {{ font-family: var(--font-serif); font-size: 18px; font-weight: 400;
                color: var(--text); line-height: 1.4; margin: 8px 0 6px; }}
    .pc-excerpt {{ font-family: var(--font-sans); font-size: 13px; color: var(--text-3);
                  line-height: 1.65; margin-bottom: 12px; }}
    .pc-meta {{ font-family: var(--font-sans); font-size: 11px; color: var(--text-4);
               display: flex; gap: 8px; align-items: center; }}
    .pc-dot {{ opacity: 0.4; }}
    .empty-msg {{ font-family: var(--font-serif); font-style: italic; font-size: 18px;
                 color: var(--text-3); text-align: center; padding: 3rem 0; }}
    #empty-filter-msg {{
      display: none; font-family: var(--font-serif); font-style: italic;
      font-size: 17px; color: var(--text-3); text-align: center; padding: 3rem 0;
    }}
    .listing-footer {{
      border-top: 0.5px solid var(--border); padding: 1.2rem 2.5rem;
      display: flex; justify-content: space-between; align-items: center;
      font-family: var(--font-sans); font-size: 12px; color: var(--text-4);
    }}
    .listing-footer a {{ color: var(--text-3); transition: color var(--t-base); }}
    .listing-footer a:hover {{ color: var(--text); }}
    @media (max-width: 640px) {{
      .listing-wrap   {{ padding: 2rem 1.2rem 4rem; }}
      .cards-grid     {{ grid-template-columns: 1fr; }}
      .listing-title  {{ font-size: 26px; }}
      .listing-footer {{ flex-direction: column; gap: 0.5rem; text-align: center; }}
    }}
  </style>
</head>
<body>

  <nav id="main-nav">
    <a href="index.html" class="nav-logo">Marginalia</a>
    <input type="checkbox" id="nav-toggle"/>
    <label for="nav-toggle" class="nav-hamburger" aria-label="Menu">
      <span></span><span></span><span></span>
    </label>
    <ul class="nav-links">

      <li class="nav-has-dropdown">
        <button class="nav-dropdown-btn" aria-haspopup="true" aria-expanded="false">
          Essays
          <svg class="nav-chevron" width="9" height="5" viewBox="0 0 9 5" fill="none" aria-hidden="true">
            <path d="M1 1l3.5 3L8 1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div class="nav-dropdown-panel">
          <a href="posts.html" class="ndp-all">All essays</a>
          <span class="ndp-label">By topic</span>
          <a href="posts.html?tag=analysis">Analysis</a>
          <a href="posts.html?tag=algebra">Algebra</a>
          <a href="posts.html?tag=topology">Topology</a>
          <a href="posts.html?tag=geometry">Geometry</a>
          <a href="posts.html?tag=number-theory">Number Theory</a>
          <a href="posts.html?tag=logic">Logic</a>
          <a href="posts.html?tag=probability">Probability</a>
        </div>
      </li>

      <li class="nav-has-dropdown">
        <button class="nav-dropdown-btn" aria-haspopup="true" aria-expanded="false">
          Problems
          <svg class="nav-chevron" width="9" height="5" viewBox="0 0 9 5" fill="none" aria-hidden="true">
            <path d="M1 1l3.5 3L8 1" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <div class="nav-dropdown-panel">
          <a href="problems.html" class="ndp-all">All problems</a>
          <span class="ndp-label">By source</span>
          <a href="problems.html?source=isi-cmi">ISI / CMI</a>
          <a href="problems.html?source=olympiad">Olympiads</a>
          <a href="problems.html?source=putnam">Putnam</a>
        </div>
      </li>

      <li><a href="notes.html">Marginal Notes</a></li>
      <li><a href="index.html#about">About</a></li>

    </ul>
    <button id="theme-toggle" aria-label="Toggle dark mode">
      <svg id="icon-moon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
      <svg id="icon-sun" width="14" height="14" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round" style="display:none">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
    </button>
  </nav>

  <div class="listing-wrap">
    <div class="listing-header">
      <h1 class="listing-title">All problems</h1>
      <p class="listing-count">{count} problem{plural} so far</p>
    </div>

    <div class="filter-row" id="filters">
{filter_btns}
    </div>

    <div class="cards-grid" id="cards">
      {cards_html}
    </div>

    <p id="empty-filter-msg">Problems from this source are coming soon.</p>
  </div>

  <footer class="listing-footer">
    <span style="font-family:var(--font-serif);font-style:italic;">
      "Mathematics is the art of giving the same name to different things." — Poincaré
    </span>
    <div style="display:flex;gap:1rem;">
      <a href="index.html">Home</a>
    </div>
  </footer>

  <script>
    (function(){{
      function syncIcon(t){{
        var m=document.getElementById('icon-moon'),s=document.getElementById('icon-sun');
        if(!m||!s)return;
        m.style.display=t==='dark'?'none':'block';
        s.style.display=t==='dark'?'block':'none';
      }}
      syncIcon(document.documentElement.getAttribute('data-theme'));
      document.getElementById('theme-toggle').addEventListener('click',function(){{
        var c=document.documentElement.getAttribute('data-theme');
        var n=c==='dark'?'light':'dark';
        document.documentElement.setAttribute('data-theme',n);
        localStorage.setItem('mg-theme',n);
        syncIcon(n);
      }});

      var filterBtns=document.querySelectorAll('.filter-btn');
      var cards=document.querySelectorAll('.post-card');
      var emptyMsg=document.getElementById('empty-filter-msg');

      function applyFilter(f){{
        var matched=0;
        cards.forEach(function(c){{
          var hide=f!=='all'&&!c.dataset.tag.includes(f);
          c.classList.toggle('hidden',hide);
          if(!hide)matched++;
        }});
        filterBtns.forEach(function(b){{
          b.classList.toggle('active',b.dataset.filter===f);
        }});
        if(emptyMsg){{
          emptyMsg.style.display=(matched===0&&f!=='all')?'block':'none';
        }}
      }}

      filterBtns.forEach(function(b){{
        b.addEventListener('click',function(){{applyFilter(b.dataset.filter);}});
      }});

      var urlSource=new URLSearchParams(window.location.search).get('source');
      if(urlSource)applyFilter('tag-'+urlSource);
    }})();
  </script>

  <script src="js/nav-dropdown.js"></script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
@app.route("/index.html")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/posts/")
@app.route("/posts")
@app.route("/posts.html")
def posts_listing():
    listing_path = os.path.join(POSTS_DIR, "index.html")
    if os.path.isfile(listing_path):
        return send_from_directory(POSTS_DIR, "index.html")
    return build_listing_html(get_posts())


@app.route("/posts/<slug>")
@app.route("/posts/<slug>.html")
def post(slug):
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", slug.replace(".html", ""))
    fpath = os.path.join(POSTS_DIR, f"{safe}.html")
    if not os.path.isfile(fpath):
        abort(404)
    return send_from_directory(POSTS_DIR, f"{safe}.html")


@app.route("/problems/")
@app.route("/problems")
@app.route("/problems.html")
def problems_listing():
    return build_problems_html(get_posts())


@app.route("/css/<path:filename>")
def css(filename):
    return send_from_directory(CSS_DIR, filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(JS_DIR, filename)


@app.route("/notes")
@app.route("/notes.html")
def notes():
    return send_from_directory(BASE_DIR, "notes.html")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route("/favicon.svg")
def favicon():
    return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.route("/robots.txt")
def robots():
    return send_from_directory(BASE_DIR, "robots.txt", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(BASE_DIR, "sitemap.xml", mimetype="application/xml")


@app.route("/feed.xml")
def rss_feed():
    posts  = get_posts()
    domain = "https://YOUR_DOMAIN"   # ← replace with your real domain
    items  = ""
    for p in posts:
        items += f"""
    <item>
      <title><![CDATA[{p['title']}]]></title>
      <link>{domain}/posts/{p['slug']}.html</link>
      <description><![CDATA[{p['excerpt']}]]></description>
      <pubDate>{p['rfc822_date']}</pubDate>
      <guid isPermaLink="true">{domain}/posts/{p['slug']}.html</guid>
    </item>"""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Marginalia</title>
    <link>{domain}/</link>
    <description>A personal mathematics blog — analysis, algebra, topology, number theory, and logic.</description>
    <language>en</language>
    <atom:link href="{domain}/feed.xml" rel="self" type="application/rss+xml"/>
    {items}
  </channel>
</rss>"""
    from flask import Response
    return Response(xml, mimetype="application/rss+xml")


# ── 404 ───────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return """<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>404 — Marginalia</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300&family=EB+Garamond:ital@1&display=swap"/>
  <style>
    body{margin:0;min-height:100vh;background:#f0f2ec;display:flex;flex-direction:column;
         align-items:center;justify-content:center;text-align:center;gap:1rem;}
    .n{font-family:'Cormorant Garamond',serif;font-size:96px;font-weight:300;color:#a0b088;line-height:1;}
    .m{font-family:'EB Garamond',serif;font-style:italic;font-size:18px;color:#7a8e68;}
    a{font-size:12px;color:#4a5c38;letter-spacing:.08em;text-decoration:none;
      border-bottom:.5px solid rgba(74,92,56,.4);padding-bottom:1px;}
  </style>
</head>
<body>
  <div class="n">404</div>
  <div class="m">This page seems to have wandered off.</div>
  <a href="/">← Return home</a>
</body></html>""", 404


# ── Static export for GitHub Pages ───────────────────────────────────────────

def build_static():
    """
    Writes posts.html, problems.html, and feed.xml to the project root for GitHub Pages.
    Run before every push that adds or removes a post:
        python server.py --build
    """
    posts  = get_posts()
    domain = "https://promit-dutta.github.io/marginalia"   # your GitHub Pages domain

    html_out = os.path.join(BASE_DIR, "posts.html")
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(build_listing_html(posts))
    print(f"\n  posts.html    — {len(posts)} post(s)")

    problems_out = os.path.join(BASE_DIR, "problems.html")
    with open(problems_out, "w", encoding="utf-8") as f:
        f.write(build_problems_html(posts))
    problem_count = len([p for p in posts if p["tag_class"] in {"tag-isi-cmi", "tag-olympiad", "tag-putnam"}])
    print(f"  problems.html — {problem_count} problem(s)")

    items = ""
    for p in posts:
        items += f"""
    <item>
      <title><![CDATA[{p['title']}]]></title>
      <link>{domain}/posts/{p['slug']}.html</link>
      <description><![CDATA[{p['excerpt']}]]></description>
      <pubDate>{p['rfc822_date']}</pubDate>
      <guid isPermaLink="true">{domain}/posts/{p['slug']}.html</guid>
    </item>"""
    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Marginalia</title>
    <link>{domain}/</link>
    <description>A personal mathematics blog — analysis, algebra, topology, number theory, and logic.</description>
    <language>en</language>
    <atom:link href="{domain}/feed.xml" rel="self" type="application/rss+xml"/>
    {items}
  </channel>
</rss>"""
    feed_out = os.path.join(BASE_DIR, "feed.xml")
    with open(feed_out, "w", encoding="utf-8") as f:
        f.write(feed_xml)
    print(f"  feed.xml      — {len(posts)} item(s)")
    print(f"\n  Domain is set to promit-dutta.github.io/marginalia — run --build to regenerate.")
    print("  Commit posts.html, problems.html, feed.xml and push for GitHub Pages.\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--build" in sys.argv:
        build_static()
    else:
        print("\n  ┌─────────────────────────────────────┐")
        print("  │   Marginalia  →  localhost:5000      │")
        print("  │   GitHub Pages build:                │")
        print("  │     python server.py --build         │")
        print("  │   Ctrl+C to stop                     │")
        print("  └─────────────────────────────────────┘\n")
        app.run(debug=True, port=5000)