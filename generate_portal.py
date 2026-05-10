"""
Mérida Property Portal — data processor.
Reads properties_all.csv + template.html → writes index.html.

Usage:
  python3 generate_portal.py
"""

import csv
import json
import re
from pathlib import Path
from datetime import datetime

BASE         = Path(__file__).parent
INPUT_CSV    = BASE / "properties_all.csv"
TEMPLATE     = BASE / "template.html"
OUTPUT_HTML  = BASE / "index.html"

MXN_TO_USD   = 17.5

# ── Agency display metadata ────────────────────────────────
AGENCY_META = {
    "mexintl":            {"label": "Mexico International",     "color": "#1A3C5E"},
    "mayanworld":         {"label": "Mayan World Real Estate",  "color": "#B45309"},
    "propertypros":       {"label": "Property Professionals",   "color": "#16A34A"},
    "trustfirst":         {"label": "TrustFirst Mérida",        "color": "#6D28D9"},
    "christies":          {"label": "Christie's Mexico",        "color": "#9F1239"},
    "meridaliving":       {"label": "Merida Living",            "color": "#0369A1"},
    "yucatanbeach":       {"label": "Yucatán Beach & City",     "color": "#0F766E"},
    "yucatanbeachhomes":  {"label": "Yucatán Beach Homes",      "color": "#C2410C"},
    "balam":              {"label": "Balam Group",              "color": "#5B21B6"},
    "meridareg":          {"label": "Mérida Real Estate Group", "color": "#BE123C"},
}

# ── Agent roster (keyed by agency id) ─────────────────────
AGENTS = {
    "meridaliving": [
        {"name": "Carlos Betancourt", "title": "Certified Broker", "photo": "", "languages": ["English", "Spanish"], "years_exp": 10, "certs": ["AMPI", "NAR Affiliate"], "bio": "Native Meridian with 10+ years helping expats and nationals find their perfect home. NAR international affiliate with deep local knowledge.", "email": "cbm893@hotmail.com"},
        {"name": "Shirley Hisgen",    "title": "Real Estate Agent", "photo": "", "languages": ["English"], "years_exp": 15, "certs": [], "bio": "15+ years in real estate across Minnesota, Arizona, New Mexico, and now Mérida. Specializes in relocating buyers from the US and Canada.", "email": "shirley.meridaliving@gmail.com"},
        {"name": "Josey Vogels",      "title": "Licensed Realtor",  "photo": "", "languages": ["English"], "years_exp": 10, "certs": ["Ontario Realtor™"], "bio": "Licensed Ontario Realtor with 10+ years Canadian RE experience. Living in Mérida since 2013 — specializes in expat buyers navigating the Mexican market.", "email": "justaskjosey@me.com"},
        {"name": "Arturo Magana",     "title": "Real Estate Agent", "photo": "", "languages": ["English", "Spanish"], "years_exp": 10, "certs": [], "bio": "10 years in Mérida with deep community roots. Known for exceptional follow-through and building lasting client relationships.", "email": "arturomeridaliving@gmail.com"},
        {"name": "Lucía Pantoja",     "title": "Senior Agent",      "photo": "", "languages": ["English", "Spanish"], "years_exp": 12, "certs": [], "bio": "Highly experienced agent providing top-tier customer service for both buyers and sellers in the Mérida market.", "email": "meridaliving@hotmail.com"},
        {"name": "Annie Murillo",     "title": "Real Estate Agent", "photo": "", "languages": ["English", "Spanish"], "years_exp": 5,  "certs": [], "bio": "Native Meridian passionate about connecting people with their perfect home. Adventurous spirit with a talent for finding exactly what clients need.", "email": "animurillom@hotmail.com"},
        {"name": "Cristina Sosa",     "title": "Real Estate Agent", "photo": "", "languages": ["English", "Spanish"], "years_exp": 4,  "certs": [], "bio": "Passionate agent who believes finding a home is one of life's most important decisions. Dedicated to making every client feel confident throughout the process.", "email": "cristysosar94@hotmail.com"},
    ],
    "balam": [
        {"name": "Greg Hokenson", "title": "Owner & Broker", "photo": "", "languages": ["English", "Spanish"], "years_exp": 17, "certs": ["AMPI"], "bio": "Founder of Balam Group with 17+ years in Mérida luxury and expat real estate. Deep expertise in high-end colonial homes, beach properties, and investment portfolios.", "email": "", "website": "https://balamgroup.com.mx"},
    ],
    "mexintl": [
        {"name": "Mexico International Team", "title": "Mérida's Established Expat Agency", "photo": "", "languages": ["English", "Spanish"], "years_exp": 20, "certs": ["AMPI"], "bio": "One of Mérida's oldest English-language agencies, specializing in colonial homes, beach lots in Progreso, and Yucatán property for American and Canadian buyers.", "email": "", "website": "https://mexintl.com.mx"},
    ],
    "christies": [
        {"name": "Tracy Beitz",    "title": "Luxury Real Estate Agent", "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Tracy-Beitz-copy-scaled.jpg",       "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Luxury property specialist at Christie's International Real Estate Mexico — haciendas, colonial mansions, and premium coastal homes.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/tracy-beitz/"},
        {"name": "Jorge Delgado",  "title": "Senior Luxury Agent",      "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Jorge-Delgado-525.jpg",               "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Bilingual luxury real estate specialist with deep expertise in high-end Yucatán and Mérida properties for international buyers.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/jorge-delgado/"},
        {"name": "Jerry Agüero",   "title": "Real Estate Agent",        "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Jerry-Headshot-525x328-1.jpg",          "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Specializes in luxury residential properties across Mérida and the Yucatán Peninsula for discerning buyers.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/jerry-aguero/"},
        {"name": "Jason Waller",   "title": "Real Estate Agent",        "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Jason-Waller-525.jpg",                  "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Expert in luxury home acquisitions and investments across Yucatán, with a focus on North American buyers relocating to Mérida.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/jason-waller/"},
        {"name": "Elizabeth Gregg","title": "Luxury Agent",             "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Eli-Gregg.jpg",                         "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Connects international buyers with exceptional luxury properties in Mérida and across the Yucatán Peninsula.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/elizabeth-gregg/"},
        {"name": "Kim O'Connell",  "title": "Real Estate Agent",        "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Kim-OConnell-525.jpg",                   "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Trusted advisor for buyers and sellers in Mérida's luxury real estate market, with a reputation for seamless transactions.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/kim-oconnell/"},
        {"name": "Tony Rabachuk",  "title": "Real Estate Agent",        "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/06/Tony-Portraits-525.jpg",                 "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Specializes in luxury residential acquisitions across Yucatán, helping expats and investors navigate the premium market.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/tony-rabachuk/"},
        {"name": "Maxime Bertron", "title": "Real Estate Agent",        "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/HeadShots-final-7-copy.jpg",             "languages": ["English", "Spanish", "French"], "years_exp": None, "certs": ["Christie's International"], "bio": "Trilingual luxury agent serving French, English, and Spanish-speaking buyers across Mexico's premium real estate markets.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/maxime-bertron/"},
        {"name": "Reese Uggeri",   "title": "Real Estate Agent",        "photo": "https://www.christiesrealestatemexico.com/wp-content/uploads/2025/01/Reese-Uggeri-Square-3-525.jpg",         "languages": ["English", "Spanish"], "years_exp": None, "certs": ["Christie's International"], "bio": "Dedicated to helping buyers find their ideal luxury home in Mérida and the Yucatán Peninsula.", "email": "", "website": "https://www.christiesrealestatemexico.com/agents/reese-uggeri/"},
    ],
    "mayanworld":       [{"name": "Mayan World Team",              "title": "Mérida Real Estate Specialists",       "photo": "", "languages": ["English", "Spanish"], "years_exp": 10, "certs": [],       "bio": "Bilingual real estate team specializing in residential properties across Mérida, Progreso, and surrounding Yucatán towns.", "email": "", "website": "https://www.mayanworldrealestate.com"}],
    "propertypros":     [{"name": "Property Professionals Team",   "title": "Mérida Property Experts",              "photo": "", "languages": ["English", "Spanish"], "years_exp": 12, "certs": [],       "bio": "Full-service bilingual brokerage covering residential, commercial, and vacation properties in Mérida and the Yucatán coast.", "email": "", "website": "https://www.propertypros.mx"}],
    "yucatanbeach":     [{"name": "Yucatán Beach & City Team",     "title": "Beach & Urban Property Specialists",   "photo": "", "languages": ["English", "Spanish"], "years_exp": 10, "certs": ["AMPI"], "bio": "Specialists in both Mérida city homes and Yucatán coastal properties — from Progreso and Chelem to Telchac and Sisal.", "email": "", "website": "https://www.yucatanbeachandcity.com"}],
    "yucatanbeachhomes":[{"name": "Yucatán Beach Homes Team",      "title": "Coastal Property Experts",             "photo": "", "languages": ["English", "Spanish"], "years_exp": 8,  "certs": [],       "bio": "Focused exclusively on beachfront and coastal properties along the Yucatán Gulf Coast — Chelem, Progreso, Telchac, and beyond.", "email": "", "website": "https://www.yucatanbeachhomes.com"}],
    "trustfirst":       [{"name": "TrustFirst Mérida Team",        "title": "Buyer-Focused Real Estate",            "photo": "", "languages": ["English", "Spanish"], "years_exp": 8,  "certs": [],       "bio": "Buyer-advocate agency committed to transparency, verified listings, and protecting foreign buyers through every step of the Mexican purchase process.", "email": "", "website": "https://trustfirstmerida.com"}],
    "meridareg":        [{"name": "Mérida Real Estate Group",      "title": "Full-Service Mérida Brokerage",        "photo": "", "languages": ["English", "Spanish"], "years_exp": 10, "certs": ["AMPI"], "bio": "Comprehensive brokerage covering all Mérida neighborhoods and surrounding areas. Strong track record with US and Canadian relocation buyers.", "email": "", "website": "https://www.meridarealestategroup.com"}],
}

# ── URL patterns that indicate a category/search page, not a listing ──
_NON_PROPERTY_URL = re.compile(
    r'/property-category/|/listing-category/'
    r'|/search/?(?:$|[?#])'
    r'|/search[-_]by[-_]map/'
    r'|/properties/?(?:$|[?#])'
    r'|/listings/?(?:$|[?#])'
    r'|/state/[^/]+/?(?:$|[?#])'
    r'|/city/[^/]+/?(?:$|[?#])'
    r'|/area/[^/]+/?(?:$|[?#])'
    r'|/action/[^/]+/?(?:$|[?#])'
    r'|/listings/tagged/'
    r'|/a/[^/]+/?(?:$|[?#])'
    r'|list\.html',
    re.IGNORECASE,
)
_ROOT_URL_RE = re.compile(r'^https?://[^/]+/?$')
_SOLD_TITLE    = re.compile(r'\bSOLD\b|\bUNDER\s+CONTRACT\b|\bPENDING\b|\bOFF\s+MARKET\b', re.IGNORECASE)
# Titles that are clearly agency/site names rather than individual property listings
_GENERIC_TITLE = re.compile(
    r'^(merida\s+(living\s+)?real\s+estate'
    r'|merida\s+real\s+estate\s+group'
    r'|real\s+estate\s+group'
    r'|advanced\s+search'
    r'|search\s+by\s+map'
    r'|.*listings?\s+for\s+sale$'
    r'|yucatan\s+real\s+estate'
    r'|centro\s+real\s+estate'
    r'|merida\s+real\s+estate\s+for\s+sale)',
    re.IGNORECASE,
)
MIN_USD_PRICE =     75_000  # below this is almost certainly a parsing error
MAX_USD_PRICE = 15_000_000  # above this is almost certainly MXN stored as USD

# ── Area keyword buckets ───────────────────────────────────
_AREA_KW = {
    "beach":       ["progreso", "chelem", "telchac", "chicxulub", "chuburna puerto", "celestun", "sisal", "yucalpeten", "beachfront", "oceanfront", "coastal", "costa bonita", "marina", "san benito", "uaymitun", "playa", "seafront"],
    "norte":       ["north merida", "north mérida", "norte", "altabrisa", "temozon", "temozón", "cabo norte", "cholul", "conkal", "dzitya", "arborea", "santa maria chi", "gran provincia", "caucel", "ciudad caucel", "las americas", "montejo", "san ramon", "francisco de montejo", "la ceiba", "yucatan country club", "santa fe", "pensiones"],
    "centro":      ["centro", "colonial", "downtown", "mejorada", "garcia gineres", "san sebastian", "ermita", "historico", "historic", "itzimna", "paseo de montejo", "santa ana", "santiago", "benito juarez", "barrio", "sam canche", "la plancha", "san cristobal", "jesús"],
    "surrounding": ["hacienda", "ranch", "rancho", "valladolid", "izamal", "motul", "ticul", "oxkutzcab", "muna", "ucu", "hunucma", "uman", "kikteil", "xcanatun", "hocaba", "sotuta", "tixkokob", "xmatkuil", "tekanto", "acanceh", "cenote", "golf course", "pueblo", "baca", "tepakan", "chicxulub pueblo", "countryside", "rural"],
    "rental":      ["for rent", "income potential", "airbnb", "boutique hotel", "investment property", "income property", "student suite", "rental income", "renta", "en renta"],
}

_TYPE_KW = {
    "land":       ["land", "lot", "lote", "terreno", "solar", "homesite", "acreage", "residential lot", "beachfront lot", "land parcel", "plot", "buildable", "lotification"],
    "condo":      ["condo", "condominium", "penthouse", "pent house", "apartment", "suite", "studio", "flat", "departamento", "depa", "ph "],
    "commercial": ["hotel", "boutique hotel", "commercial", "business", "office", "warehouse", "bodega", "retail", "restaurant", "hostel", "hostal"],
}


def _area_bucket(title: str, location: str, url: str) -> str:
    haystack = f"{title} {location} {url}".lower()
    for area, keywords in _AREA_KW.items():
        if any(kw in haystack for kw in keywords):
            return area
    return "merida"


def _type_bucket(title: str, url: str) -> str:
    haystack = f"{title} {url}".lower()
    for ptype, keywords in _TYPE_KW.items():
        if any(kw in haystack for kw in keywords):
            return ptype
    return "house"


def _price_bucket(price: int | None) -> str:
    if not price:        return "unknown"
    if price < 200_000:  return "under200"
    if price < 500_000:  return "200to500"
    if price < 1_000_000:return "500to1m"
    return "over1m"


def load_properties(csv_path: Path) -> list[dict]:
    props = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row["url"].strip()

            # Skip root domain URLs and category/search pages
            if not url or _ROOT_URL_RE.match(url) or _NON_PROPERTY_URL.search(url):
                continue
            # Never show sold / under-contract listings
            if _SOLD_TITLE.search(row["title"]):
                continue
            # Skip generic agency/site-name titles (not individual listings)
            if _GENERIC_TITLE.match(row["title"].strip()):
                continue

            price_usd = None
            raw_price = row["price"].strip()
            if raw_price:
                try:
                    val = float(raw_price)
                    if row["currency"] == "MXN":
                        val /= MXN_TO_USD
                    val = int(round(val / 1000) * 1000)
                    if MIN_USD_PRICE <= val <= MAX_USD_PRICE:
                        price_usd = val
                except (ValueError, ZeroDivisionError):
                    pass

            agency   = row["agency"]
            meta     = AGENCY_META.get(agency, {"label": agency.title(), "color": "#555"})
            title    = row["title"].strip()
            location = row["location"].strip() if row["location"] else ""

            props.append({
                "agency":   agency,
                "label":    meta["label"],
                "color":    meta["color"],
                "title":    title,
                "price":    price_usd,
                "bucket":   _price_bucket(price_usd),
                "beds":     int(row["bedrooms"])  if row["bedrooms"]  else None,
                "baths":    int(row["bathrooms"]) if row["bathrooms"] else None,
                "location": location,
                "url":      url,
                "img":      row.get("image_url", "").strip(),
                "dup":      row["duplicate_flag"],
                "also_at":  [],
                "area":     _area_bucket(title, location, url),
                "ptype":    _type_bucket(title, url),
            })
    return props


def deduplicate(props: list[dict]) -> list[dict]:
    groups: dict[int, list[int]] = {}
    for i, p in enumerate(props):
        m = re.search(r"group (\d+)", p["dup"])
        if m:
            groups.setdefault(int(m.group(1)), []).append(i)

    remove: set[int] = set()
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


def build_agency_pills(agency_list: list[dict]) -> str:
    parts = []
    for a in agency_list:
        if a["id"] == "balam":
            parts.append(
                f'<button class="pill pill-gold" data-f="agency" data-v="{a["id"]}">'
                f'&#11088; {a["label"]} <span class="gold-badge">Gold Sponsor</span></button>'
            )
        else:
            parts.append(f'<button class="pill" data-f="agency" data-v="{a["id"]}">{a["label"]}</button>')
    return "\n      ".join(parts)


def build_ticker(agency_list: list[dict]) -> str:
    items = []
    for a in agency_list * 2:
        if a["id"] == "balam":
            items.append(
                f'<span class="ticker-item ticker-gold">'
                f'<span>&#11088;</span>{a["label"]}'
                f'<span class="ticker-badge">Gold Sponsor</span></span>'
            )
        else:
            items.append(f'<span class="ticker-item">{a["label"]}</span>')
    return "".join(items)


def main():
    print("=== Mérida Portal Generator ===")

    props = load_properties(INPUT_CSV)
    print(f"  Loaded:     {len(props)}")

    props = deduplicate(props)
    print(f"  After dedup:{len(props)}")

    # Strip internal keys the template doesn't need
    for p in props:
        p.pop("label", None)
        p.pop("color", None)

    props_json = json.dumps(props, ensure_ascii=False, separators=(",", ":"))

    # Collect agencies in order of appearance
    seen: dict[str, dict] = {}
    for row in csv.DictReader(open(INPUT_CSV, encoding="utf-8")):
        ag = row["agency"]
        if ag not in seen:
            meta = AGENCY_META.get(ag, {"label": ag.title(), "color": "#555"})
            seen[ag] = {"id": ag, "label": meta["label"], "color": meta["color"]}
    agency_list   = list(seen.values())
    agencies_json = json.dumps({a["id"]: {"label": a["label"], "color": a["color"]} for a in agency_list}, ensure_ascii=False)
    agents_json   = json.dumps(AGENTS, ensure_ascii=False)

    now     = datetime.now()
    updated = now.strftime("%b %d")          # "May 09"
    updated_full = now.strftime("%B %d, %Y") # "May 09, 2026"

    template = TEMPLATE.read_text(encoding="utf-8")
    html = (template
        .replace("{{TOTAL}}",         str(len(props)))
        .replace("{{AGENCY_COUNT}}",  str(len(agency_list)))
        .replace("{{UPDATED}}",       updated)
        .replace("{{UPDATED_FULL}}",  updated_full)
        .replace("{{TICKER_ITEMS}}",  build_ticker(agency_list))
        .replace("{{AGENCY_PILLS}}",  build_agency_pills(agency_list))
        .replace("{{PROPS_JSON}}",    props_json)
        .replace("{{AGENCIES_JSON}}", agencies_json)
        .replace("{{AGENTS_JSON}}",   agents_json)
    )

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    size_kb = OUTPUT_HTML.stat().st_size // 1024
    print(f"  Written:    {OUTPUT_HTML} ({size_kb} KB)")


if __name__ == "__main__":
    main()
