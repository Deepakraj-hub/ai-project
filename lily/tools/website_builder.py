"""Generate modern interactive single-page sites from a user goal."""

from __future__ import annotations

import re
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "lily-site"


def extract_title(goal: str) -> str:
    cleaned = re.sub(r"^(build|create|make|design|develop)\s+(an?\s+)?(interactive\s+)?(website|web app|site)\s+(about|on|for)\s+", "", goal, flags=re.I)
    cleaned = re.sub(r"^(build|create|make)\s+", "", cleaned, flags=re.I)
    cleaned = cleaned.strip(" .")
    if not cleaned:
        return "Lily Studio"
    return cleaned.title()[:80]


def build_interactive_website_html(goal: str) -> str:
    title = extract_title(goal)
    slug = slugify(title)
    accent_a = "#22d3ee"
    accent_b = "#a855f7"
    lower_goal = goal.lower()
    if any(w in lower_goal for w in ["tree", "forest", "planet", "space", "cosmos"]):
        accent_a = "#34d399"
        accent_b = "#6366f1"
    cards = _cards_for_goal(lower_goal)
    facts = _facts_for_goal(lower_goal)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #060610;
      --ink: #f8fafc;
      --muted: #94a3b8;
      --a: {accent_a};
      --b: {accent_b};
      --card: rgba(255,255,255,.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, Segoe UI, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 20%, color-mix(in srgb, var(--a) 35%, transparent), transparent 28rem),
        radial-gradient(circle at 85% 10%, color-mix(in srgb, var(--b) 30%, transparent), transparent 24rem),
        linear-gradient(160deg, #05050c, #0b1020 55%, #120818);
      min-height: 100vh;
    }}
    main {{ width: min(1100px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0 72px; }}
    .hero {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 40px; align-items: center; min-height: 70vh; }}
    h1 {{ font-size: clamp(2.8rem, 8vw, 5.5rem); line-height: .95; margin: 0 0 16px; }}
    .lead {{ color: var(--muted); font-size: 1.15rem; line-height: 1.7; max-width: 560px; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 24px; }}
    button {{
      border: 0; border-radius: 999px; padding: 12px 20px; font-weight: 700; cursor: pointer;
      background: linear-gradient(135deg, var(--a), var(--b)); color: #041016;
      transition: transform .2s ease, filter .2s ease;
    }}
    button.secondary {{ background: transparent; color: var(--ink); border: 1px solid rgba(255,255,255,.18); }}
    button:hover {{ transform: translateY(-2px); filter: brightness(1.08); }}
    .orb {{
      aspect-ratio: 1; border-radius: 50%; position: relative;
      background: radial-gradient(circle at 30% 30%, #fff, var(--a) 22%, var(--b) 58%, transparent 70%);
      box-shadow: 0 30px 120px color-mix(in srgb, var(--b) 45%, transparent);
      animation: float 4.5s ease-in-out infinite;
    }}
    .orb::after {{
      content: ""; position: absolute; inset: 18%; border-radius: 50%;
      border: 2px dashed rgba(255,255,255,.25); animation: spin 12s linear infinite;
    }}
    .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 36px; }}
    .card {{
      background: var(--card); border: 1px solid rgba(255,255,255,.12);
      border-radius: 16px; padding: 18px; backdrop-filter: blur(12px);
      transition: transform .2s ease, border-color .2s ease;
    }}
    .card:hover {{ transform: translateY(-4px); border-color: color-mix(in srgb, var(--a) 50%, white); }}
    .card h2 {{ margin: 0 0 8px; font-size: 1rem; color: color-mix(in srgb, var(--a) 70%, white); }}
    .card p {{ margin: 0; color: #cbd5e1; line-height: 1.55; }}
    .panel {{
      margin-top: 28px; padding: 18px; border-radius: 16px;
      background: rgba(0,0,0,.25); border: 1px solid rgba(255,255,255,.08);
    }}
    .tag {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: rgba(255,255,255,.08); margin: 4px 6px 0 0; font-size: .85rem; }}
    @keyframes float {{ 50% {{ transform: translateY(-16px); }} }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    @media (max-width: 860px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .cards {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>{title}</h1>
        <p class="lead">Built by Lily — a modern interactive experience inspired by your request.</p>
        <div class="actions">
          <button id="pulseBtn">Animate Scene</button>
          <button class="secondary" id="shuffleBtn">Shuffle Palette</button>
        </div>
        <div class="panel" id="factPanel">
          <strong>Interactive panel</strong>
          <p id="factText" style="margin:8px 0 0;color:#cbd5e1;">Tap the buttons to explore the scene.</p>
        </div>
      </div>
      <div class="orb" id="orb" aria-label="Interactive visual"></div>
    </section>
    <section class="cards">
      <article class="card"><h2>{cards[0][0]}</h2><p>{cards[0][1]}</p></article>
      <article class="card"><h2>{cards[1][0]}</h2><p>{cards[1][1]}</p></article>
      <article class="card"><h2>{cards[2][0]}</h2><p>{cards[2][1]}</p></article>
    </section>
    <div style="margin-top:24px">
      <span class="tag">modern ui</span><span class="tag">interactive</span><span class="tag">{slug}</span>
    </div>
  </main>
  <script>
    const facts = [
      "{facts[0]}",
      "{facts[1]}",
      "{facts[2]}",
      "Lily assembled this page automatically from your task."
    ];
    const palettes = [
      ["#34d399", "#6366f1"],
      ["#22d3ee", "#a855f7"],
      ["#fbbf24", "#ef4444"],
      ["#fb7185", "#38bdf8"]
    ];
    document.querySelector("#pulseBtn").addEventListener("click", () => {{
      document.querySelector("#orb").animate([
        {{ transform: "scale(1)" }},
        {{ transform: "scale(1.08)" }},
        {{ transform: "scale(1)" }}
      ], {{ duration: 700 }});
      document.querySelector("#factText").textContent = facts[Math.floor(Math.random() * facts.length)];
    }});
    document.querySelector("#shuffleBtn").addEventListener("click", () => {{
      const [a, b] = palettes[Math.floor(Math.random() * palettes.length)];
      document.documentElement.style.setProperty("--a", a);
      document.documentElement.style.setProperty("--b", b);
    }});
  </script>
</body>
</html>
"""


def website_output_path(goal: str, workspace_root: Path) -> Path:
    title = extract_title(goal)
    return workspace_root / slugify(title) / "index.html"


def _cards_for_goal(lower_goal: str) -> list[tuple[str, str]]:
    if "tree" in lower_goal and "planet" in lower_goal:
        return [
            ("Canopy Worlds", "Forest layers become living skylines, breathing oxygen into the planetary story."),
            ("Orbital Gardens", "Planet cards glow like ecosystems in motion, connecting roots, weather, and starlight."),
            ("Living Balance", "Hover states and animated color shifts turn climate, space, and nature into an explorable scene."),
        ]
    if "tree" in lower_goal or "forest" in lower_goal:
        return [
            ("Roots", "A grounded section for soil, networks, growth, and hidden forest intelligence."),
            ("Canopy", "Soft motion and green light evoke leaves, wind, biodiversity, and shade."),
            ("Seasons", "Interactive accents can shift the mood from spring growth to autumn warmth."),
        ]
    if "planet" in lower_goal or "space" in lower_goal or "cosmos" in lower_goal:
        return [
            ("Inner Worlds", "Terrestrial planets get crisp, luminous cards with layered atmosphere effects."),
            ("Gas Giants", "Large gradients and orbital motion give the composition a cosmic center of gravity."),
            ("Deep Space", "Responsive glass panels keep the interface readable while the background feels vast."),
        ]
    return [
        ("Explore", "Smooth motion, glass panels, and responsive layout for any screen."),
        ("Discover", "Dynamic accents and hover states make the page feel alive."),
        ("Create", "Lily can extend this into a full multi-page site on request."),
    ]


def _facts_for_goal(lower_goal: str) -> list[str]:
    if "tree" in lower_goal and "planet" in lower_goal:
        return [
            "Trees stabilize ecosystems while planets remind us how rare living worlds can be.",
            "Forests move water, carbon, shade, and habitat through the planetary system.",
            "A good interface can make earth science and astronomy feel connected.",
        ]
    if "tree" in lower_goal or "forest" in lower_goal:
        return [
            "Trees communicate through chemistry, roots, fungi, and environmental signals.",
            "Forest canopies create microclimates for birds, insects, and young plants.",
            "Healthy trees cool cities, filter air, and soften stormwater.",
        ]
    if "planet" in lower_goal or "space" in lower_goal or "cosmos" in lower_goal:
        return [
            "Every planet has a distinct rhythm of gravity, atmosphere, and motion.",
            "Saturn's rings are mostly ice, rock, and dust reflecting sunlight.",
            "Exoplanets help us imagine how diverse worlds beyond our solar system may be.",
        ]
    return [
        "Interactive design helps people explore complex topics playfully.",
        "Motion, contrast, and spacing can guide attention without extra explanation.",
        "A single-page site can still feel polished when the layout has a clear story.",
    ]
