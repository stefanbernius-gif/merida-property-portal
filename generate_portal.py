"""
Mérida Property Portal — self-contained generator for GitHub Actions.
Reads properties_all.csv from the same directory, outputs index.html.
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
INPUT_CSV = BASE / "properties_all.csv"
OUTPUT_HTML = BASE / "index.html"

MXN_TO_USD = 17.5

AGENCY_META = {
    "mexintl":           {"label": "Mexico International",    "color": "#1A3C5E"},
    "mayanworld":        {"label": "Mayan World Real Estate", "color": "#B45309"},
    "propertypros":      {"label": "Property Professionals",  "color": "#16A34A"},
    "trustfirst":        {"label": "TrustFirst Mérida",       "color": "#6D28D9"},
    "christies":         {"label": "Christie's Mexico",       "color": "#9F1239"},
    "meridaliving":      {"label": "Merida Living",           "color": "#0369A1"},
    "yucatanbeach":      {"label": "Yucatán Beach & City",    "color": "#0F766E"},
    "yucatanbeachhomes": {"label": "Yucatán Beach Homes",     "color": "#C2410C"},
    "balam":             {"label": "Balam Group",             "color": "#5B21B6"},
    "meridareg":         {"label": "Mérida Real Estate Group","color": "#BE123C"},
}


def load_and_process(csv_path):
    props = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            price_usd = None
            if row["price"]:
                try:
                    raw = float(row["price"])
                    if row["currency"] == "MXN":
                        raw /= MXN_TO_USD
                    price_usd = int(round(raw / 1000) * 1000)
                    if price_usd < 5000:
                        price_usd = None
                except (ValueError, ZeroDivisionError):
                    pass

            agency = row["agency"]
            meta = AGENCY_META.get(agency, {"label": agency.title(), "color": "#555"})
            props.append({
                "agency":   agency,
                "label":    meta["label"],
                "color":    meta["color"],
                "title":    row["title"].strip(),
                "price":    price_usd,
                "beds":     int(row["bedrooms"]) if row["bedrooms"] else None,
                "baths":    int(row["bathrooms"]) if row["bathrooms"] else None,
                "location": row["location"].strip() if row["location"] else "",
                "url":      row["url"].strip(),
                "img":      row.get("image_url", "").strip(),
                "dup":      row["duplicate_flag"],
                "also_at":  [],
            })
    return props


def deduplicate(props):
    groups = {}
    for i, p in enumerate(props):
        m = re.search(r"group (\d+)", p["dup"])
        if m:
            groups.setdefault(int(m.group(1)), []).append(i)

    remove = set()
    for indices in groups.values():
        if len(indices) < 2:
            continue
        def completeness(i):
            p = props[i]
            return sum(1 for v in [p["price"], p["beds"], p["baths"], p["location"], p["img"]] if v)
        best = max(indices, key=completeness)
        props[best]["also_at"] = [props[i]["label"] for i in indices if i != best]
        remove.update(i for i in indices if i != best)

    return [p for i, p in enumerate(props) if i not in remove]


def price_bucket(price):
    if not price:       return "unknown"
    if price < 200000:  return "under200"
    if price < 500000:  return "200to500"
    if price < 1000000: return "500to1m"
    return "over1m"


def build_html(props_json, total, updated, agency_list, agency_meta_js):
    agency_pills = "\n".join(
        f'        <button class="pill pill-gold" data-f="agency" data-v="{a["id"]}">&#11088; {a["label"]} <span class="gold-badge">Gold Sponsor</span></button>'
        if a["id"] == "balam" else
        f'        <button class="pill" data-f="agency" data-v="{a["id"]}">{a["label"]}</button>'
        for a in agency_list
    )

    # Build ticker items (duplicated for seamless loop)
    ticker_items = ""
    for a in agency_list * 2:
        if a["id"] == "balam":
            ticker_items += f'<span class="ticker-item ticker-gold"><span class="ticker-star">&#11088;</span>{a["label"]}<span class="ticker-badge">Gold Sponsor</span></span>'
        else:
            ticker_items += f'<span class="ticker-item">{a["label"]}</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mérida Properties — Find Your Home in Yucatán</title>
<meta name="description" content="Search {total}+ listings from Mérida's top real estate agencies. All prices in USD. Built for US and Canadian buyers.">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --navy:#1A3C5E; --terra:#C84B2F; --green:#15803D;
  --text:#111827; --muted:#6B7280; --border:#E5E7EB;
  --bg:#F8F7F5; --card:#fff;
  --shadow:0 1px 6px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.04);
  --r:12px; --font:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif
}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.5}}
a{{color:inherit;text-decoration:none}}
button{{cursor:pointer;font-family:var(--font)}}
.hero{{background:linear-gradient(140deg,#0F2942 0%,#1A3C5E 50%,#1E5F8C 100%);color:#fff;padding:52px 20px 44px;text-align:center;position:relative;overflow:hidden}}
.hero::after{{content:'';position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse 80% 60% at 50% 110%,rgba(243,193,58,.15),transparent)}}
.hero-tag{{display:inline-block;background:rgba(243,193,58,.2);border:1px solid rgba(243,193,58,.4);color:#F3C13A;border-radius:20px;padding:4px 16px;font-size:12px;letter-spacing:.8px;text-transform:uppercase;font-weight:600;margin-bottom:18px}}
.hero h1{{font-size:clamp(24px,5vw,44px);font-weight:800;line-height:1.15;margin-bottom:14px;max-width:640px;margin-left:auto;margin-right:auto;position:relative;z-index:1}}
.hero h1 em{{color:#F3C13A;font-style:normal}}
.hero p{{font-size:clamp(15px,2.5vw,18px);opacity:.8;max-width:520px;margin:0 auto 32px;position:relative;z-index:1}}
.hero-stats{{display:flex;justify-content:center;gap:clamp(20px,4vw,48px);flex-wrap:wrap;position:relative;z-index:1}}
.stat-num{{font-size:clamp(22px,4vw,32px);font-weight:700;color:#F3C13A;line-height:1}}
.stat-lbl{{font-size:11px;opacity:.65;text-transform:uppercase;letter-spacing:.6px;margin-top:4px}}
.ticker-wrap{{background:#0F2942;overflow:hidden;white-space:nowrap;padding:8px 0;border-bottom:2px solid #F3C13A}}
.ticker-track{{display:inline-flex;gap:0;animation:ticker-scroll 35s linear infinite}}
.ticker-track:hover{{animation-play-state:paused}}
@keyframes ticker-scroll{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.ticker-item{{display:inline-flex;align-items:center;gap:6px;padding:0 28px;font-size:12px;font-weight:600;color:rgba(255,255,255,.65);letter-spacing:.4px;text-transform:uppercase;border-right:1px solid rgba(255,255,255,.1)}}
.ticker-gold{{color:#F3C13A!important;font-weight:800}}
.ticker-star{{font-size:13px}}
.ticker-badge{{background:#F3C13A;color:#0F2942;font-size:9px;font-weight:800;padding:2px 7px;border-radius:8px;letter-spacing:.6px;text-transform:uppercase;margin-left:4px}}
.pill-gold{{border-color:#F3C13A!important;color:#92610A!important;background:linear-gradient(135deg,#FFFBEB,#FEF3C7)!important;font-weight:700!important}}
.pill-gold.active{{background:linear-gradient(135deg,#F3C13A,#D97706)!important;border-color:#D97706!important;color:#fff!important}}
.gold-badge{{background:#F3C13A;color:#0F2942;font-size:9px;font-weight:800;padding:1px 6px;border-radius:6px;letter-spacing:.5px;text-transform:uppercase;margin-left:4px;vertical-align:middle}}
.filter-wrap{{position:sticky;top:0;z-index:200;background:#fff;border-bottom:1px solid var(--border);box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.filter-inner{{max-width:1140px;margin:0 auto;padding:8px 16px;display:flex;flex-direction:column;gap:6px}}
.filter-row{{display:flex;gap:6px;align-items:center;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;padding-bottom:1px}}
.filter-row::-webkit-scrollbar{{display:none}}
.filter-row-agency{{border-bottom:1px solid var(--border);padding-bottom:7px}}
.filter-lbl{{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;flex-shrink:0;padding-right:2px}}
.filter-sep{{width:1px;height:22px;background:var(--border);flex-shrink:0;margin:0 4px}}
.pill{{padding:5px 13px;border-radius:20px;font-size:12.5px;font-weight:500;border:1.5px solid var(--border);background:#fff;color:var(--text);transition:all .15s;white-space:nowrap;flex-shrink:0}}
.pill:hover{{border-color:var(--navy);color:var(--navy)}}
.pill.active{{background:var(--navy);border-color:var(--navy);color:#fff}}
.count-badge{{margin-left:auto;flex-shrink:0;font-size:12px;font-weight:600;color:var(--muted);white-space:nowrap;padding:0 4px}}
.main{{max-width:1140px;margin:0 auto;padding:24px 16px 80px}}
.results-bar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:8px}}
.results-bar h2{{font-size:14px;color:var(--muted);font-weight:400}}
.results-bar strong{{color:var(--text);font-weight:600}}
.sort-sel{{padding:7px 12px;border-radius:8px;border:1.5px solid var(--border);font-size:13px;background:#fff;color:var(--text);cursor:pointer;font-family:var(--font)}}
.grid{{display:grid;grid-template-columns:1fr;gap:20px}}
@media(min-width:580px){{.grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(min-width:900px){{.grid{{grid-template-columns:repeat(3,1fr)}}}}
.card{{background:var(--card);border-radius:var(--r);box-shadow:var(--shadow);overflow:hidden;display:flex;flex-direction:column;transition:transform .2s,box-shadow .2s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.12)}}
.card-img{{height:172px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;font-size:44px;background:#ddd}}
.card-img img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;transition:transform .3s}}
.card:hover .card-img img{{transform:scale(1.04)}}
.card-img .loc-label{{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,.62));color:#fff;font-size:12px;font-weight:500;padding:8px 12px}}
.multi-badge{{position:absolute;top:10px;right:10px;background:#F3C13A;color:#1A3C5E;padding:3px 9px;border-radius:10px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}}
.agency-bar{{height:3px;width:100%}}
.card-body{{padding:16px;flex:1;display:flex;flex-direction:column;gap:10px}}
.card-price{{font-size:21px;font-weight:800;color:var(--green);line-height:1}}
.card-price small{{font-size:12px;font-weight:400;color:var(--muted);margin-left:3px}}
.card-title{{font-size:14px;font-weight:600;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.card-attrs{{display:flex;gap:10px;flex-wrap:wrap}}
.attr{{display:flex;align-items:center;gap:4px;font-size:12px;color:var(--muted)}}
.agency-chip{{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;padding:3px 10px;border-radius:10px;width:fit-content;text-transform:uppercase;letter-spacing:.3px}}
.also-at{{font-size:11px;color:var(--muted);margin-top:-4px}}
.card-actions{{padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:8px}}
.btn-view{{flex:1;padding:10px 0;background:var(--navy);color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;transition:background .15s}}
.btn-view:hover{{background:#2563EB}}
.btn-view:disabled{{opacity:.4;cursor:default}}
.btn-ask{{padding:10px 14px;background:var(--terra);color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;transition:background .15s;white-space:nowrap}}
.btn-ask:hover{{background:#A33B22}}
.empty{{grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--muted)}}
.empty h3{{font-size:20px;color:var(--text);margin-bottom:8px}}
.sticky-cta{{position:fixed;bottom:20px;right:20px;z-index:150;background:var(--terra);color:#fff;border:none;border-radius:40px;padding:14px 22px;font-size:14px;font-weight:700;box-shadow:0 4px 20px rgba(200,75,47,.45);display:flex;align-items:center;gap:8px;transition:transform .15s,box-shadow .15s}}
.sticky-cta:hover{{transform:translateY(-2px);box-shadow:0 6px 28px rgba(200,75,47,.55)}}
.overlay{{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:500;display:none;align-items:flex-end;justify-content:center;padding:0}}
.overlay.open{{display:flex}}
@media(min-width:560px){{.overlay{{align-items:center;padding:20px}}.modal{{border-radius:var(--r);max-width:480px}}}}
.modal{{background:#fff;width:100%;border-radius:var(--r) var(--r) 0 0;padding:28px 24px 32px;max-height:90vh;overflow-y:auto;position:relative}}
.modal-handle{{width:40px;height:4px;background:var(--border);border-radius:2px;margin:0 auto 20px}}
.modal h2{{font-size:20px;font-weight:800;color:var(--navy);margin-bottom:6px}}
.modal .sub{{font-size:13px;color:var(--muted);margin-bottom:22px}}
.form-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.field{{margin-bottom:14px}}
.field label{{display:block;font-size:12px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px}}
.field input,.field select,.field textarea{{width:100%;padding:11px 14px;border:1.5px solid var(--border);border-radius:8px;font-size:14px;font-family:var(--font);background:#fff;color:var(--text);transition:border-color .15s}}
.field input:focus,.field select:focus,.field textarea:focus{{outline:none;border-color:var(--navy)}}
.field textarea{{height:72px;resize:none}}
.btn-submit{{width:100%;padding:14px;background:var(--terra);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:700;margin-top:4px;transition:background .15s}}
.btn-submit:hover{{background:#A33B22}}
.btn-close-x{{position:absolute;top:14px;right:16px;background:none;border:none;font-size:20px;color:var(--muted);padding:4px;line-height:1}}
.success{{display:none;text-align:center;padding:12px 0 4px}}
.success h3{{font-size:20px;color:var(--green);margin-bottom:8px}}
.success p{{color:var(--muted);font-size:14px}}
.footer{{background:#0F2942;color:rgba(255,255,255,.55);text-align:center;padding:28px 20px;font-size:12px;line-height:1.8}}
.footer a{{color:rgba(255,255,255,.75)}}
.hidden{{display:none!important}}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-tag">&#127968; Mérida Property Search</div>
  <h1>Find Your Perfect Home in<br><em>Mérida, Mexico</em></h1>
  <p>{total}+ curated listings from Mérida's top agencies — all prices in USD, built for US &amp; Canadian buyers.</p>
  <div class="hero-stats">
    <div><div class="stat-num" id="js-total">{total}</div><div class="stat-lbl">Total Listings</div></div>
    <div><div class="stat-num">{len(agency_list)}</div><div class="stat-lbl">Top Agencies</div></div>
    <div><div class="stat-num">USD</div><div class="stat-lbl">All Prices</div></div>
    <div><div class="stat-num">{updated.split(",")[0]}</div><div class="stat-lbl">Last Updated</div></div>
  </div>
</div>

<div class="ticker-wrap">
  <div class="ticker-track">{ticker_items}</div>
</div>

<div class="filter-wrap">
  <div class="filter-inner">
    <div class="filter-row filter-row-agency">
      <span class="filter-lbl">Agency</span>
      <button class="pill active" data-f="agency" data-v="all">All</button>
{agency_pills}
    </div>
    <div class="filter-row">
      <span class="filter-lbl">Price</span>
      <button class="pill active" data-f="price" data-v="all">All</button>
      <button class="pill" data-f="price" data-v="under200">Under $200K</button>
      <button class="pill" data-f="price" data-v="200to500">$200K–$500K</button>
      <button class="pill" data-f="price" data-v="500to1m">$500K–$1M</button>
      <button class="pill" data-f="price" data-v="over1m">$1M+</button>
      <div class="filter-sep"></div>
      <span class="filter-lbl">Beds</span>
      <button class="pill active" data-f="beds" data-v="0">Any</button>
      <button class="pill" data-f="beds" data-v="2">2+</button>
      <button class="pill" data-f="beds" data-v="3">3+</button>
      <button class="pill" data-f="beds" data-v="4">4+</button>
      <span class="count-badge" id="js-count">— shown</span>
    </div>
  </div>
</div>

<main class="main">
  <div class="results-bar">
    <h2><strong id="js-vis">0</strong> properties</h2>
    <select class="sort-sel" id="js-sort">
      <option value="price-asc">Price: Low → High</option>
      <option value="price-desc">Price: High → Low</option>
      <option value="beds-desc">Most Bedrooms First</option>
    </select>
  </div>
  <div class="grid" id="js-grid"></div>
</main>

<button class="sticky-cta" onclick="openModal()">&#128172; Get Matched Free</button>

<div class="overlay" id="js-overlay" onclick="overlayClick(event)">
  <div class="modal" id="js-modal">
    <div class="modal-handle"></div>
    <button class="btn-close-x" onclick="closeModal()">&#10005;</button>
    <h2>Find Your Property in Mérida</h2>
    <p class="sub">Tell us what you need — we'll connect you with the right agency. No spam, ever.</p>
    <form id="js-form" onsubmit="submitLead(event)">
      <div class="form-row">
        <div class="field"><label>First Name</label><input type="text" name="first" required placeholder="Jane"></div>
        <div class="field"><label>Last Name</label><input type="text" name="last" required placeholder="Smith"></div>
      </div>
      <div class="field"><label>Email *</label><input type="email" name="email" required placeholder="jane@example.com"></div>
      <div class="field"><label>Phone (optional)</label><input type="tel" name="phone" placeholder="+1 555 000 0000"></div>
      <div class="form-row">
        <div class="field">
          <label>Budget (USD)</label>
          <select name="budget">
            <option value="">Any budget</option>
            <option>Under $200,000</option>
            <option>$200,000 – $500,000</option>
            <option>$500,000 – $1,000,000</option>
            <option>$1,000,000+</option>
          </select>
        </div>
        <div class="field">
          <label>Bedrooms</label>
          <select name="beds">
            <option value="">Any</option>
            <option>1+</option><option>2+</option><option>3+</option><option>4+</option>
          </select>
        </div>
      </div>
      <div class="field">
        <label>Notes (optional)</label>
        <textarea name="notes" placeholder="Pool, near Centro, moving in 2026, or anything else..."></textarea>
      </div>
      <button type="submit" class="btn-submit">Connect Me With an Agent &#8594;</button>
    </form>
    <div class="success" id="js-success">
      <h3>&#10003; Request Received!</h3>
      <p>We'll match you with the right agency within 24 hours.<br>Check your inbox for next steps.</p>
    </div>
  </div>
</div>

<footer class="footer">
  <p>Data sourced from Mexico International, Mayan World Real Estate, Property Professionals Mexico, TrustFirst Mérida, Christie's Mexico, Merida Living, Yucatán Beach &amp; City, Yucatán Beach Homes.</p>
  <p>Prices converted to USD at ~17.5 MXN/USD &middot; Last updated {updated}</p>
</footer>

<script>
const PROPS = {props_json};
const AGENCIES = {agency_meta_js};

let F = {{agency:"all", price:"all", beds:0}};
let sortKey = "price-asc";
let pending = "";

function fmtPrice(n){{
  if(!n) return '<span style="color:#9CA3AF;font-size:15px">Price on Request</span>';
  return "$" + n.toLocaleString("en-US") + '<small> USD</small>';
}}

function cardHTML(p){{
  const ag = AGENCIES[p.agency] || {{label:p.agency, color:"#555"}};
  const beds  = p.beds  ? `<span class="attr">&#127968; ${{p.beds}} bd</span>` : "";
  const baths = p.baths ? `<span class="attr">&#128703; ${{p.baths}} ba</span>` : "";
  const loc   = p.location ? `<span class="attr">&#128205; ${{p.location}}</span>` : "";
  const multi = p.also_at && p.also_at.length ? `<div class="multi-badge">Multi-Listed</div>` : "";
  const alsoAt = p.also_at && p.also_at.length ? `<div class="also-at">Also on: ${{p.also_at.join(", ")}}</div>` : "";
  const viewBtn = p.url
    ? `<button class="btn-view" onclick="window.open('${{p.url.replace(/'/g,"\\'")}}','_blank')">View Listing &#8594;</button>`
    : `<button class="btn-view" disabled>No Link</button>`;
  const lightBg = ag.color + "22";
  const imgTag = p.img
    ? `<img src="${{p.img}}" alt="${{p.title}}" loading="lazy" onerror="this.style.display='none'">`
    : `<span style="opacity:.2;font-size:48px">&#127968;</span>`;
  return `<div class="card">
  <div class="card-img" style="background:linear-gradient(135deg,${{ag.color}},${{ag.color}}99)">
    ${{imgTag}}${{multi}}
    <div class="loc-label">${{p.location || "Mérida, Yucatán"}}</div>
  </div>
  <div class="agency-bar" style="background:${{ag.color}}"></div>
  <div class="card-body">
    <div class="card-price">${{fmtPrice(p.price)}}</div>
    <div class="card-title">${{p.title}}</div>
    <div class="card-attrs">${{beds}}${{baths}}${{loc}}</div>
    <div class="agency-chip" style="background:${{lightBg}};color:${{ag.color}}">${{ag.label}}</div>
    ${{alsoAt}}
  </div>
  <div class="card-actions">${{viewBtn}}<button class="btn-ask" onclick="openModal('${{encodeURIComponent(p.title)}}')">Ask Agent</button></div>
</div>`;
}}

function render(){{
  let list = PROPS.filter(p => {{
    if(F.agency !== "all" && p.agency !== F.agency) return false;
    if(F.price  !== "all" && p.bucket !== F.price)  return false;
    if(F.beds > 0 && (!p.beds || p.beds < F.beds))  return false;
    return true;
  }});
  list.sort((a,b) => {{
    if(sortKey === "price-asc")  return (a.price||9999999) - (b.price||9999999);
    if(sortKey === "price-desc") return (b.price||0) - (a.price||0);
    if(sortKey === "beds-desc")  return (b.beds||0) - (a.beds||0);
    return 0;
  }});
  const grid = document.getElementById("js-grid");
  grid.innerHTML = list.length
    ? list.map(cardHTML).join("")
    : '<div class="empty"><h3>No properties match</h3><p>Try adjusting the filters above.</p></div>';
  document.getElementById("js-vis").textContent   = list.length;
  document.getElementById("js-count").textContent = list.length + " shown";
  document.getElementById("js-total").textContent = list.length;
}}

document.querySelectorAll(".pill[data-f]").forEach(btn => {{
  btn.addEventListener("click", () => {{
    const f = btn.dataset.f, v = btn.dataset.v;
    document.querySelectorAll(`.pill[data-f="${{f}}"]`).forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    if(f === "agency") F.agency = v;
    else if(f === "price") F.price = v;
    else if(f === "beds") F.beds = parseInt(v);
    render();
  }});
}});

document.getElementById("js-sort").addEventListener("change", e => {{ sortKey = e.target.value; render(); }});

function openModal(title){{
  pending = title ? decodeURIComponent(title) : "";
  document.getElementById("js-overlay").classList.add("open");
  document.body.style.overflow = "hidden";
}}
function closeModal(){{
  document.getElementById("js-overlay").classList.remove("open");
  document.body.style.overflow = "";
  document.getElementById("js-form").classList.remove("hidden");
  document.getElementById("js-success").style.display = "none";
}}
function overlayClick(e){{
  if(e.target === document.getElementById("js-overlay")) closeModal();
}}
function submitLead(e){{
  e.preventDefault();
  const d = Object.fromEntries(new FormData(e.target));
  const lines = Object.entries(d).map(([k,v]) => k+": "+v).join("%0A");
  const prop  = pending ? "%0AProperty: " + pending : "";
  window.open("mailto:stefan.bernius@pm.me?subject=M%C3%A9rida+Property+Inquiry&body="+lines+prop);
  e.target.classList.add("hidden");
  document.getElementById("js-success").style.display = "block";
}}

render();
</script>
</body>
</html>"""


def main():
    print("=== Mérida Portal Generator ===")
    props = load_and_process(INPUT_CSV)
    print(f"  Loaded: {len(props)}")
    props = deduplicate(props)
    print(f"  After dedup: {len(props)}")

    for p in props:
        p["bucket"] = price_bucket(p["price"])

    props_json = json.dumps(props, ensure_ascii=False, separators=(",", ":"))
    updated = datetime.now().strftime("%B %d, %Y")

    agencies_seen = {}
    for p in props:
        if p["agency"] not in agencies_seen:
            agencies_seen[p["agency"]] = {"id": p["agency"], "label": p["label"], "color": p["color"]}
    agency_list = list(agencies_seen.values())
    agency_meta_js = json.dumps(
        {a["id"]: {"label": a["label"], "color": a["color"]} for a in agency_list},
        ensure_ascii=False
    )

    html = build_html(props_json, len(props), updated, agency_list, agency_meta_js)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  Written: {OUTPUT_HTML} ({OUTPUT_HTML.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
