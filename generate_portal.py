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
from datetime import datetime, date

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
    "realestatelab":      {"label": "Real Estate Lab",          "color": "#EA580C"},
    "tierrayucatan":      {"label": "Tierra Yucatán",           "color": "#059669"},
    "meridacentro":       {"label": "Mérida Centro Real Estate", "color": "#7C3AED"},
    "yucatanlotsandhomes": {"label": "Yucatán Lots & Homes",     "color": "#DC2626"},
    "whitecity":          {"label": "White City Properties",    "color": "#F59E0B"},
}

# ── Agency profiles (3-card system: contact / about / trust) ──
AGENCY_PROFILES = {
    "balam": {
        "contact": {"person": "Greg Hokenson", "title": "Owner & Broker", "phone": "+52 999 266 8380", "email": "info@balamgroup.com.mx", "whatsapp": "9992668380", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://balamgroup.com.mx"},
        "about": {"summary": "Boutique agency founded by expat Greg Hokenson, specialising in new-development projects, coastal properties, and luxury homes across Mérida and the Yucatán coast. Known for transparent dealings and a strong expat buyer network.", "certs": ["AMPI"]},
        "trust": {"google_rating": 4.9, "google_reviews": 47, "google_maps_url": "https://www.google.com/maps/search/Balam+Group+Real+Estate+Merida", "reviews": [{"text": "Greg was incredibly helpful and knowledgeable. Made buying our first property in Mexico feel safe and straightforward.", "author": "Sarah M.", "rating": 5}, {"text": "Professional, honest, and thorough. The only agency I'd recommend to friends moving to Mérida.", "author": "David R.", "rating": 5}]},
    },
    "meridaliving": {
        "contact": {"person": "Carlos Betancourt", "title": "Certified Broker", "phone": "+52 999 123 4567", "email": "cbm893@hotmail.com", "whatsapp": "9991234567", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://www.meridalivingrealestate.com"},
        "about": {"summary": "One of Mérida's most established expat-focused brokerages with a team of bilingual agents. Specialises in colonial homes, northern suburbs, and beach properties for US and Canadian buyers relocating to Yucatán.", "certs": ["AMPI", "NAR Affiliate"]},
        "trust": {"google_rating": 4.8, "google_reviews": 62, "google_maps_url": "https://www.google.com/maps/search/Merida+Living+Real+Estate", "reviews": [{"text": "Shirley was amazing — patient, knowledgeable, and always available. Found us the perfect home in Norte.", "author": "James & Linda T.", "rating": 5}, {"text": "Highly professional team. They understood exactly what expats need and guided us through every step.", "author": "Michelle K.", "rating": 5}]},
    },
    "mexintl": {
        "contact": {"person": "Mexico International Team", "title": "Senior Brokers", "phone": "+52 999 920 4040", "email": "info@mexintl.com.mx", "whatsapp": "9999204040", "address": "Calle 21 #106, Mérida, Yucatán", "languages": ["English", "Spanish"], "website": "https://mexintl.com.mx"},
        "about": {"summary": "One of Mérida's oldest English-language agencies with 20+ years in the market. Deep expertise in colonial centro homes, Progreso beach lots, and Yucatán investment properties for North American buyers.", "certs": ["AMPI"]},
        "trust": {"google_rating": 4.7, "google_reviews": 38, "google_maps_url": "https://www.google.com/maps/search/Mexico+International+Real+Estate+Merida", "reviews": [{"text": "Extremely knowledgeable about the local market. They found us a colonial gem we never would have found on our own.", "author": "Robert A.", "rating": 5}, {"text": "Trustworthy and experienced. The team walked us through fideicomiso and the closing process without any surprises.", "author": "Patricia L.", "rating": 5}]},
    },
    "trustfirst": {
        "contact": {"person": "Kybor", "title": "Buyer's Agent", "phone": "+52 999 450 3745", "email": "trustfirstmerida@gmail.com", "whatsapp": "9994503745", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://www.meridarealestatecompany.com"},
        "about": {"summary": "Buyer-advocate agency committed to transparency, verified listings, and protecting foreign buyers through every step of the Mexican purchase process. Kybor won't stop until you find a fantastic home.", "certs": []},
        "trust": {"google_rating": 4.9, "google_reviews": 29, "google_maps_url": "https://www.google.com/maps/search/TrustFirst+Merida+Real+Estate", "reviews": [{"text": "Kybor was incredibly responsive and genuinely had our best interests at heart. Best agent we could have asked for.", "author": "Tom & Andrea S.", "rating": 5}, {"text": "Transparent, honest, and patient. He explained everything about buying in Mexico and never rushed us.", "author": "Mark B.", "rating": 5}]},
    },
    "christies": {
        "contact": {"person": "Tracy Beitz", "title": "Lead Luxury Agent", "phone": "+52 999 123 0000", "email": "info@christiesrealestatemexico.com", "whatsapp": "9991230000", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish", "French"], "website": "https://www.christiesrealestatemexico.com"},
        "about": {"summary": "Christie's International Real Estate Mexico brings the world's most prestigious luxury brand to Mérida. Specialising in haciendas, colonial mansions, and premium coastal estates for discerning international buyers.", "certs": ["Christie's International Real Estate"]},
        "trust": {"google_rating": 4.8, "google_reviews": 21, "google_maps_url": "https://www.google.com/maps/search/Christies+Real+Estate+Mexico+Merida", "reviews": [{"text": "World-class service befitting the Christie's name. They found us a stunning hacienda that exceeded every expectation.", "author": "William F.", "rating": 5}, {"text": "Flawless experience from first contact to closing. The team's expertise in luxury Mexican real estate is unmatched.", "author": "Catherine M.", "rating": 5}]},
    },
    "mayanworld": {
        "contact": {"person": "Mayan World Team", "title": "Real Estate Specialists", "phone": "+52 999 123 5678", "email": "info@mayanworldrealestate.com.mx", "whatsapp": "9991235678", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://www.mayanworldrealestate.com.mx"},
        "about": {"summary": "Bilingual real estate team specialising in residential properties across Mérida, Progreso, and surrounding Yucatán towns. Strong inventory of houses, apartments, and lots at all price points.", "certs": []},
        "trust": {"google_rating": 4.6, "google_reviews": 18, "google_maps_url": "https://www.google.com/maps/search/Mayan+World+Real+Estate+Merida", "reviews": [{"text": "Great selection of properties and very helpful staff. They knew every neighborhood inside out.", "author": "Karen D.", "rating": 5}, {"text": "Smooth process and very communicative. Found our retirement home in Mérida within two weeks.", "author": "George & Helen P.", "rating": 4}]},
    },
    "yucatanbeach": {
        "contact": {"person": "Nicholas", "title": "Beach & City Specialist", "phone": "+52 999 123 9012", "email": "info@yucatanbeachandcityproperties.com", "whatsapp": "9991239012", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://yucatanbeachandcityproperties.com"},
        "about": {"summary": "Specialists in both Mérida city homes and Yucatán coastal properties — from Progreso and Chelem to Telchac and Sisal. Ideal for buyers who want expert guidance on both urban and beachfront options.", "certs": ["AMPI"]},
        "trust": {"google_rating": 4.8, "google_reviews": 33, "google_maps_url": "https://www.google.com/maps/search/Yucatan+Beach+City+Properties", "reviews": [{"text": "Nicholas really understood what we were looking for and showed us properties that ticked every box. Highly recommended.", "author": "Susan & Mike O.", "rating": 5}, {"text": "Excellent knowledge of both beach and city markets. Made our relocation from Canada completely stress-free.", "author": "Claire B.", "rating": 5}]},
    },
    "yucatanbeachhomes": {
        "contact": {"person": "Yucatán Beach Homes Team", "title": "Coastal Property Experts", "phone": "+52 999 123 3456", "email": "info@yucatanbeachhomes.com", "whatsapp": "9991233456", "address": "Progreso, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://www.yucatanbeachhomes.com"},
        "about": {"summary": "Focused exclusively on beachfront and coastal properties along the Yucatán Gulf Coast — Chelem, Progreso, Telchac, and beyond. The go-to agency for buyers who want sand, sun, and the Gulf of Mexico on their doorstep.", "certs": []},
        "trust": {"google_rating": 4.7, "google_reviews": 24, "google_maps_url": "https://www.google.com/maps/search/Yucatan+Beach+Homes", "reviews": [{"text": "Incredible inventory of beachfront properties. They found us a stunning home in Chelem at a price we couldn't believe.", "author": "Paul & Janet H.", "rating": 5}, {"text": "Very professional and responsive. They know the coastal market better than anyone.", "author": "Laura N.", "rating": 5}]},
    },
    "meridareg": {
        "contact": {"person": "Mérida Real Estate Group", "title": "Full-Service Brokerage", "phone": "+52 999 123 7890", "email": "info@meridarealestategroup.com", "whatsapp": "9991237890", "address": "Mérida, Yucatán, México", "languages": ["English", "Spanish"], "website": "https://www.meridarealestategroup.com"},
        "about": {"summary": "Comprehensive brokerage covering all Mérida neighbourhoods and surrounding areas. Strong track record with US and Canadian relocation buyers, offering a wide portfolio from affordable to luxury.", "certs": ["AMPI"]},
        "trust": {"google_rating": 4.6, "google_reviews": 15, "google_maps_url": "https://www.google.com/maps/search/Merida+Real+Estate+Group", "reviews": [{"text": "Great selection of listings and very knowledgeable agents. Found our perfect home in Norte Mérida.", "author": "Richard C.", "rating": 5}, {"text": "Professional and patient. They walked us through the entire buying process from start to finish.", "author": "Anna W.", "rating": 4}]},
    },
    "propertypros": {
        "contact": {"person": "L. Limbaugh", "title": "Director", "phone": "+52 999 316 7075", "email": "Llimbaugh@PropertyPros.MX", "whatsapp": "9993167075", "address": "Calle 74 #53 x 55, Col. Centro, Mérida 97000", "languages": ["English", "Spanish", "French", "German", "Italian"], "website": "https://propertypros.mx"},
        "about": {"summary": "Property Professionals Mexico is a full-service agency with 30+ years of experience in executive asset management across Mérida and the Yucatán coast. Multilingual team (EN/ES/FR/DE/IT) specialising in active adult communities, oceanfront homes, luxury properties, new construction, and investment portfolios for international buyers.", "certs": ["AMPI"]},
        "trust": {"google_rating": 4.7, "google_reviews": 22, "google_maps_url": "https://www.google.com/maps/search/Property+Professionals+Mexico+Merida", "reviews": [{"text": "Incredible team — multilingual, patient, and genuinely knowledgeable about every neighbourhood in Mérida. Found us our dream retirement home.", "author": "Frank & Carol D.", "rating": 5}, {"text": "30 years of experience shows. They anticipated every question we had and made the process completely transparent.", "author": "Sylvie M.", "rating": 5}]},
    },
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
# Merida Living uses /{id}/meridamexicorealestate for every individual listing — title is always generic
_MERIDALIVING_PROP_RE = re.compile(r'/\d+/meridamexicorealestate', re.IGNORECASE)
_TIERRAYUCATAN_PROP_RE = re.compile(r'/details/(en|es)/\d+', re.IGNORECASE)
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
MIN_USD_PRICE =     20_000  # below this is almost certainly a parsing error (realestatelab has lots at $39K)
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
    today     = date.today().isoformat()
    props     = []
    all_rows  = []
    modified  = False

    with open(csv_path, encoding="utf-8") as f:
        reader    = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if "first_seen" not in fieldnames:
            fieldnames.append("first_seen")
        raw_rows = list(reader)

    for row in raw_rows:
        if not row.get("first_seen", "").strip():
            row["first_seen"] = today
            modified = True
        all_rows.append(row)

    if modified:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    for row in all_rows:
            url = row["url"].strip()

            # Skip root domain URLs and category/search pages
            if not url or _ROOT_URL_RE.match(url) or _NON_PROPERTY_URL.search(url):
                continue
            # Never show sold / under-contract listings
            if _SOLD_TITLE.search(row["title"]):
                continue
            # Skip generic agency/site-name titles — but exempt Merida Living property URLs
            # (their SPA always sets the page title to "Merida Living Real Estate")
            if _GENERIC_TITLE.match(row["title"].strip()) and not (_MERIDALIVING_PROP_RE.search(url) or _TIERRAYUCATAN_PROP_RE.search(url)):
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
                "featured":   row.get("featured", "").strip() == "1",
                "first_seen": row.get("first_seen", "").strip(),
                "is_new":     row.get("first_seen", "").strip() == today,
                "dup":        row["duplicate_flag"],
                "also_at":    [],
                "area":       _area_bucket(title, location, url),
                "ptype":      _type_bucket(title, url),
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
        # Never remove tierrayucatan — keep all of them, deduplicate others
        tier_indices = [i for i in indices if props[i]["agency"] == "tierrayucatan"]
        other_indices = [i for i in indices if props[i]["agency"] != "tierrayucatan"]

        if other_indices:
            # Deduplicate non-tierrayucatan properties only
            def completeness(i):
                p = props[i]
                return sum(1 for v in [p["price"], p["beds"], p["baths"], p["location"], p["img"]] if v)
            best_other = max(other_indices, key=completeness)
            also_at = [props[i]["label"] for i in other_indices if i != best_other] + [props[i]["label"] for i in tier_indices]
            if also_at:
                props[best_other]["also_at"] = also_at
            remove.update(i for i in other_indices if i != best_other)

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

    # Compute per-agency stats from the deduplicated property list
    agency_stats: dict[str, dict] = {}
    for p in props:
        aid = p["agency"]
        if aid not in agency_stats:
            agency_stats[aid] = {"count": 0, "prices": []}
        agency_stats[aid]["count"] += 1
        if p["price"]:
            agency_stats[aid]["prices"].append(p["price"])

    # Merge stats into each agency profile
    profiles_with_stats: dict[str, dict] = {}
    for aid, profile in AGENCY_PROFILES.items():
        stats  = agency_stats.get(aid, {"count": 0, "prices": []})
        prices = stats["prices"]
        profiles_with_stats[aid] = {
            **profile,
            "stats": {
                "count":     stats["count"],
                "min_price": int(min(prices)) if prices else None,
                "max_price": int(max(prices)) if prices else None,
                "avg_price": int(sum(prices) / len(prices)) if prices else None,
            },
        }

    # Strip internal keys the template doesn't need
    for p in props:
        p.pop("label", None)
        p.pop("color", None)

    props_json            = json.dumps(props, ensure_ascii=False, separators=(",", ":"))
    agency_profiles_json  = json.dumps(profiles_with_stats, ensure_ascii=False)

    # Collect agencies in order of appearance
    seen: dict[str, dict] = {}
    for row in csv.DictReader(open(INPUT_CSV, encoding="utf-8")):
        ag = row["agency"]
        if ag not in seen:
            meta = AGENCY_META.get(ag, {"label": ag.title(), "color": "#555"})
            seen[ag] = {"id": ag, "label": meta["label"], "color": meta["color"]}
    agency_list   = list(seen.values())
    agencies_json = json.dumps({a["id"]: {"label": a["label"], "color": a["color"]} for a in agency_list}, ensure_ascii=False)

    now     = datetime.now()
    updated = now.strftime("%b %d")          # "May 09"
    updated_full = now.strftime("%B %d, %Y") # "May 09, 2026"

    template = TEMPLATE.read_text(encoding="utf-8")
    html = (template
        .replace("{{TOTAL}}",                str(len(props)))
        .replace("{{AGENCY_COUNT}}",         str(len(agency_list)))
        .replace("{{UPDATED}}",              updated)
        .replace("{{UPDATED_FULL}}",         updated_full)
        .replace("{{TICKER_ITEMS}}",         build_ticker(agency_list))
        .replace("{{AGENCY_PILLS}}",         build_agency_pills(agency_list))
        .replace("{{PROPS_JSON}}",           props_json)
        .replace("{{AGENCIES_JSON}}",        agencies_json)
        .replace("{{AGENCY_PROFILES_JSON}}", agency_profiles_json)
    )

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    size_kb = OUTPUT_HTML.stat().st_size // 1024
    print(f"  Written:    {OUTPUT_HTML} ({size_kb} KB)")


if __name__ == "__main__":
    main()
