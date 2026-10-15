#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Featured-tour page generator (ETT-11).

Reads a tour's exported record (data/featured/<slug>.json) and renders the
shared template (featured/_template.html) into one static HTML page per
supported language:

    en (default) -> featured/<slug>.html
    de/fr/it/es/ja -> <lang>/featured/<slug>.html

Run from the repo root:  python scripts/build_featured.py
Always reads/writes UTF-8 (Windows defaults to cp1252 and would mangle
accented names like "Trögler").
"""
import json, re, os, time, glob

SITE  = "https://steepmap.eu"
LANGS = ["en", "de", "fr", "it", "es", "ja"]
PLACE = {}        # slug -> {"place", "region"} from the manifest
TOURS_ALL = []    # every featured tour, in manifest order
ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRADE_COLOR = {"Easy": "#22c55e", "Medium": "#3b82f6", "Hard": "#ef4444", "Very Hard": "#111827"}
GRADE_KEY   = {0: "easy", 10: "medium", 20: "hard", 30: "veryHard"}  # (kept for reference)

# ── UI label catalog ────────────────────────────────────────────────────────
# en is the base; other languages fall back to en for any missing key.
T = {
 "en": {"all_tours":"Featured tours","search":"Search","no_results":"No tours found","get_app":"Get the app","modal_title":"Get STEEP map",
   "map_loading":"Loading 3D map…","stats":"Tour stats","grade":"Grade","steepness":"Max steepness",
   "exposure":"Exposure","aspect":"Aspect","distance":"Distance","elev_gain":"Elevation gain",
   "low_point":"Lowest point","high_point":"Highest point","cta_title":"Take this tour with you",
   "cta_body":"Open this exact tour in Steep to navigate it offline, with slope-angle and aspect overlays, 3D terrain and the GPS track.",
   "open_tour":"Open this tour in Steep","show_map":"Show map","prev":"Previous","next":"Next","photos":"photos","explore_map":"Explore map",
   "privacy":"Privacy","terms":"Terms","m_web_t":"Web app","m_web_s":"Open it in your browser",
   "m_and_s":"Get it on Google Play","m_soon":"Coming soon",
   "grade_label":{"Easy":"Easy","Medium":"Medium","Hard":"Hard","Very Hard":"Very Hard"},
   "meta_title":"{title} ski tour in {place} | Steep",
   "meta_desc":"{title} in {place}: {km} km, {gain} m ascent, up to {steep}° ({grade}). {lead}"},
 "de": {"all_tours":"Ausgewählte Touren","search":"Suchen","no_results":"Keine Touren gefunden","get_app":"App holen","modal_title":"STEEP map holen",
   "map_loading":"3D-Karte wird geladen…","stats":"Tourdaten","grade":"Schwierigkeit","steepness":"Max. Steilheit",
   "exposure":"Exposition","aspect":"Ausrichtung","distance":"Distanz","elev_gain":"Höhenmeter",
   "low_point":"Tiefster Punkt","high_point":"Höchster Punkt","cta_title":"Nimm diese Tour mit",
   "cta_body":"Öffne genau diese Tour in Steep, um sie offline zu navigieren – mit Hangneigungs- und Expositions-Overlays, 3D-Gelände und dem GPS-Track.",
   "open_tour":"Tour in Steep öffnen","show_map":"Karte zeigen","prev":"Zurück","next":"Weiter","photos":"Fotos","explore_map":"Karte erkunden",
   "privacy":"Datenschutz","terms":"AGB","m_web_t":"Web-App","m_web_s":"Im Browser öffnen",
   "m_and_s":"Bei Google Play","m_soon":"Demnächst",
   "grade_label":{"Easy":"Leicht","Medium":"Mittel","Hard":"Schwer","Very Hard":"Sehr schwer"},
   "meta_title":"{title} Skitour in {place} | Steep",
   "meta_desc":"{title} in {place}: {km} km, {gain} Hm, bis zu {steep}° ({grade}). {lead}"},
 "fr": {"all_tours":"Sorties en vedette","search":"Rechercher","no_results":"Aucune sortie trouvée","get_app":"Obtenir l'app","modal_title":"Obtenir STEEP map",
   "map_loading":"Chargement de la carte 3D…","stats":"Infos de la sortie","grade":"Difficulté","steepness":"Pente max.",
   "exposure":"Exposition","aspect":"Orientation","distance":"Distance","elev_gain":"Dénivelé positif",
   "low_point":"Point le plus bas","high_point":"Point le plus haut","cta_title":"Emportez cette sortie",
   "cta_body":"Ouvrez cette sortie exacte dans Steep pour la suivre hors ligne, avec les calques de pente et d'exposition, le relief 3D et la trace GPS.",
   "open_tour":"Ouvrir dans Steep","show_map":"Voir la carte","prev":"Précédent","next":"Suivant","photos":"photos","explore_map":"Explorer la carte",
   "privacy":"Confidentialité","terms":"Conditions","m_web_t":"Application web","m_web_s":"Ouvrir dans le navigateur",
   "m_and_s":"Disponible sur Google Play","m_soon":"Bientôt disponible",
   "grade_label":{"Easy":"Facile","Medium":"Moyen","Hard":"Difficile","Very Hard":"Très difficile"},
   "meta_title":"{title} sortie à ski à {place} | Steep",
   "meta_desc":"{title} à {place} : {km} km, {gain} m de dénivelé, jusqu'à {steep}° ({grade}). {lead}"},
 "it": {"all_tours":"Tour in evidenza","search":"Cerca","no_results":"Nessun tour trovato","get_app":"Scarica l'app","modal_title":"Scarica STEEP map",
   "map_loading":"Caricamento mappa 3D…","stats":"Dati del tour","grade":"Difficoltà","steepness":"Pendenza max",
   "exposure":"Esposizione","aspect":"Orientamento","distance":"Distanza","elev_gain":"Dislivello positivo",
   "low_point":"Punto più basso","high_point":"Punto più alto","cta_title":"Porta con te questo tour",
   "cta_body":"Apri esattamente questo tour in Steep per seguirlo offline, con i livelli di pendenza ed esposizione, il terreno 3D e la traccia GPS.",
   "open_tour":"Apri in Steep","show_map":"Mostra mappa","prev":"Precedente","next":"Successiva","photos":"foto","explore_map":"Esplora la mappa",
   "privacy":"Privacy","terms":"Termini","m_web_t":"App web","m_web_s":"Aprila nel browser",
   "m_and_s":"Scaricala su Google Play","m_soon":"Prossimamente",
   "grade_label":{"Easy":"Facile","Medium":"Medio","Hard":"Difficile","Very Hard":"Molto difficile"},
   "meta_title":"{title} tour sci in {place} | Steep",
   "meta_desc":"{title} a {place}: {km} km, {gain} m di dislivello, fino a {steep}° ({grade}). {lead}"},
 "es": {"all_tours":"Rutas destacadas","search":"Buscar","no_results":"No se encontraron rutas","get_app":"Obtener la app","modal_title":"Obtener STEEP map",
   "map_loading":"Cargando mapa 3D…","stats":"Datos de la ruta","grade":"Dificultad","steepness":"Pendiente máx.",
   "exposure":"Exposición","aspect":"Orientación","distance":"Distancia","elev_gain":"Desnivel positivo",
   "low_point":"Punto más bajo","high_point":"Punto más alto","cta_title":"Llévate esta ruta",
   "cta_body":"Abre esta misma ruta en Steep para seguirla sin conexión, con las capas de pendiente y orientación, el terreno 3D y el track GPS.",
   "open_tour":"Abrir en Steep","show_map":"Ver mapa","prev":"Anterior","next":"Siguiente","photos":"fotos","explore_map":"Explorar el mapa",
   "privacy":"Privacidad","terms":"Términos","m_web_t":"App web","m_web_s":"Ábrela en tu navegador",
   "m_and_s":"Disponible en Google Play","m_soon":"Próximamente",
   "grade_label":{"Easy":"Fácil","Medium":"Media","Hard":"Difícil","Very Hard":"Muy difícil"},
   "meta_title":"{title} ruta de esquí en {place} | Steep",
   "meta_desc":"{title} en {place}: {km} km, {gain} m de desnivel, hasta {steep}° ({grade}). {lead}"},
 "ja": {"all_tours":"注目のツアー","search":"検索","no_results":"ツアーが見つかりません","get_app":"アプリを入手","modal_title":"STEEP map を入手",
   "map_loading":"3Dマップを読み込み中…","stats":"ツアー情報","grade":"グレード","steepness":"最大斜度",
   "exposure":"露出度","aspect":"斜面方位","distance":"距離","elev_gain":"獲得標高",
   "low_point":"最低地点","high_point":"最高地点","cta_title":"このツアーを持ち歩こう",
   "cta_body":"このツアーをそのまま Steep で開けば、斜度・方位オーバーレイ、3D地形、GPSトラックとともにオフラインでナビゲーションできます。",
   "open_tour":"Steep で開く","show_map":"マップを表示","prev":"前へ","next":"次へ","photos":"枚の写真","explore_map":"マップを見る",
   "privacy":"プライバシー","terms":"利用規約","m_web_t":"ウェブアプリ","m_web_s":"ブラウザで開く",
   "m_and_s":"Google Play で入手","m_soon":"近日公開",
   "grade_label":{"Easy":"初級","Medium":"中級","Hard":"上級","Very Hard":"最上級"},
   "meta_title":"{title}（{place}）のスキーツアー | Steep",
   "meta_desc":"{place}の{title}：{km} km、獲得標高 {gain} m、最大 {steep}°（{grade}）。{lead}"},
}

def t(lang, key):
    return T.get(lang, {}).get(key, T["en"][key])

PHOTO_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
  'stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/>'
  '<circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>')

LANG_NAMES = {"en": "English", "de": "Deutsch", "fr": "Français", "it": "Italiano", "es": "Español", "ja": "日本語"}

# Extra UI strings (headings for search engines and the "more tours" block)
EXTRA = {
    "en": {"about": "About this tour", "more_tours": "More featured tours"},
    "de": {"about": "Über diese Tour", "more_tours": "Weitere ausgewählte Touren"},
    "fr": {"about": "À propos de cette sortie", "more_tours": "Plus de sorties en vedette"},
    "it": {"about": "Informazioni sul tour", "more_tours": "Altri tour in evidenza"},
    "es": {"about": "Sobre esta ruta", "more_tours": "Más rutas destacadas"},
    "ja": {"about": "このツアーについて", "more_tours": "他の注目のツアー"},
}

# Region and country names in each language (the manifest stores them in English)
REGION_T = {
    "Tyrol":     {"de": "Tirol", "fr": "Tyrol", "it": "Tirolo", "es": "Tirol", "ja": "チロル"},
    "Lombardy":  {"de": "Lombardei", "fr": "Lombardie", "it": "Lombardia", "es": "Lombardía", "ja": "ロンバルディア"},
    "Austria":   {"de": "Österreich", "fr": "Autriche", "it": "Austria", "es": "Austria", "ja": "オーストリア"},
    "Italy":     {"de": "Italien", "fr": "Italie", "it": "Italia", "es": "Italia", "ja": "イタリア"},
    "France":    {"de": "Frankreich", "fr": "France", "it": "Francia", "es": "Francia", "ja": "フランス"},
    "Norway":    {"de": "Norwegen", "fr": "Norvège", "it": "Norvegia", "es": "Noruega", "ja": "ノルウェー"},
    "Troms":     {"de": "Troms", "fr": "Troms", "it": "Troms", "es": "Troms", "ja": "トロムス"},
}

def localized_region(tour, lang):
    parts = [p.strip() for p in place_of(tour)["region"].split(",")]
    return ", ".join(REGION_T.get(p, {}).get(lang, p) for p in parts)

def page_path(slug, lang):
    return f"featured/{slug}.html" if lang == "en" else f"{lang}/featured/{slug}.html"

def tour_langs(tour):
    """Languages a tour is published in: only those with a real (stored) translation,
    plus its source language. A page in a language with only English text would be a
    near-duplicate for search engines, so those pages are not generated."""
    have = set(tour.get("langs") or LANGS)
    return [lg for lg in LANGS if lg in have]

def place_of(tour):
    p = PLACE.get(tour["slug"])
    if not p:
        raise SystemExit(f"[{tour['slug']}] missing place/region in data/featured/manifest.json")
    return p

def lead_of(text):
    """First sentence of the tour's own description, for the search snippet."""
    text = " ".join((text or "").split())
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    lead = m.group(1) if m else text
    return lead if len(lead) <= 120 else lead[:117].rsplit(" ", 1)[0] + "…"

def clamp(text, limit=160):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"

def tour_texts(tour, lang):
    s = tour["stats"]
    title = tour.get("title_i18n", {}).get(lang) or tour["title"]
    desc_txt = tour["description"].get(lang) or tour["description"].get(tour.get("source_lang") or "en") or ""
    grade_lbl = t(lang, "grade_label").get(s["grade"], s["grade"])
    place = place_of(tour)["place"]
    fields = dict(title=title, place=place, km=s["distance_km"], gain=s["elev_gain_m"],
                  steep=s["max_steep"], grade=grade_lbl, lead=lead_of(desc_txt))
    meta_title = clamp(t(lang, "meta_title").format(**fields), 65)
    meta_desc = clamp(t(lang, "meta_desc").format(**fields).replace(" .", ".").strip(), 160)
    return title, desc_txt, grade_lbl, meta_title, meta_desc

def page_strings(tour, lang):
    """All text for one language: UI labels + tour text. Shipped in every page so
    the language switcher can update the text in place without reloading."""
    title, desc_txt, grade_lbl, meta_title, meta_desc = tour_texts(tour, lang)
    out = {k: v for k, v in T[lang].items() if k not in ("grade_label", "meta_desc", "meta_title")}
    out.update(EXTRA[lang])
    out.update({
        "title": title,
        "region": localized_region(tour, lang),
        "description": "<p>" + desc_txt.replace("\n", "</p><p>") + "</p>" if desc_txt else "",
        "grade_val": grade_lbl,
        "meta_title": meta_title,
        "meta_desc": meta_desc,
    })
    return out

def render(tour, lang, template):
    slug = tour["slug"]
    s = tour["stats"]
    langs = tour_langs(tour)
    title, desc_txt, grade_lbl, meta_title, meta_desc = tour_texts(tour, lang)
    place = place_of(tour)

    # Alternates: host-relative for the in-page switcher (works on localhost and
    # prod); absolute for the SEO hreflang block.
    rel = {lg: "/" + page_path(slug, lg) for lg in langs}
    xdef = rel["en"] if "en" in rel else rel[langs[0]]
    hreflang = "\n".join(f'<link rel="alternate" hreflang="{lg}" href="{SITE}{rel[lg]}" />' for lg in langs) \
        + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{xdef}" />'
    canonical = f"{SITE}{rel[lang]}"

    photos = tour.get("photos", [])
    track_color = GRADE_COLOR.get(s["grade"], "#3b82f6")
    ogimg = f"{SITE}/media/og/{slug}.jpg"   # 1200x630 card from scripts/make_share_images.py
    lat, lng = tour["center"][1], tour["center"][0]
    trip = {
        "@context": "https://schema.org", "@type": "TouristTrip", "name": title,
        "description": meta_desc, "image": photos[:3] or [ogimg],
        "touristType": "Ski touring / backcountry skiing", "url": canonical, "inLanguage": lang,
        "location": {"@type": "Place", "name": localized_region(tour, lang),
                     "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}},
        "provider": {"@type": "Organization", "name": "Steep", "url": SITE + "/"},
    }
    crumbs = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "STEEP map", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
        ],
    }
    jsonld = "\n".join('<script type="application/ld+json">\n' + json.dumps(d, ensure_ascii=False) + "\n</script>"
                       for d in (trip, crumbs))

    toggle = (f'<button id="mediaToggle" type="button" aria-label="{t(lang,"photos")}" '
              f'data-cover="{photos[0]}"><span class="mt-label">'
              f'<span class="mt-icon">{PHOTO_ICON}</span>'
              f'<span class="mt-count">{len(photos)} {t(lang,"photos")}</span></span></button>') if photos else ""
    desc_html = "<p>" + desc_txt.replace("\n", "</p><p>") + "</p>" if desc_txt else ""

    # Options only for the languages this tour is published in
    lang_options = "\n".join(
        f'          <option value="{lg}">{LANG_NAMES[lg]}</option>' for lg in langs)

    # "More featured tours": real links to the other tours, in this language
    others = [tr for tr in TOURS_ALL if tr["slug"] != slug and lang in tour_langs(tr)]
    more = ""
    if others:
        items = "".join(
            f'<li><a href="/{page_path(tr["slug"], lang)}">'
            f'{esc((tr.get("title_i18n", {}).get(lang) or tr["title"]))}</a>'
            f'<span> · {esc(place_of(tr)["place"])}</span></li>' for tr in others)
        more = (f'<nav class="more-tours" aria-label="{esc(EXTRA[lang]["more_tours"])}">'
                f'<h2>{esc(EXTRA[lang]["more_tours"])}</h2><ul>{items}</ul></nav>')

    tok = {
        "{{LANG}}": lang, "{{SLUG}}": slug, "{{CANONICAL_URL}}": canonical,
        "{{HREFLANG_BLOCK}}": hreflang, "{{LANG_ALTERNATES_JSON}}": json.dumps(rel),
        "{{LANG_OPTIONS}}": lang_options, "{{MORE_TOURS}}": more,
        "{{ASSET_VER}}": str(int(time.time())),
        "{{I18N_JSON}}": json.dumps({lg: page_strings(tour, lg) for lg in langs}, ensure_ascii=False).replace("</", "<\\/"),
        "{{META_TITLE}}": meta_title, "{{META_DESCRIPTION}}": meta_desc, "{{OG_IMAGE}}": ogimg,
        "{{JSONLD_BLOCK}}": jsonld,
        "{{TRACK_GEOJSON}}": json.dumps(tour["track"]), "{{MAP_CENTER}}": json.dumps(tour["center"]),
        "{{MAP_ZOOM}}": str(tour["zoom"]), "{{TRACK_COLOR}}": track_color,
        "{{PHOTOS_JSON}}": json.dumps(photos), "{{MEDIA_TOGGLE_BLOCK}}": toggle,
        "{{TOUR_TITLE}}": title, "{{REGION}}": localized_region(tour, lang),
        "{{AUTHOR_NAME}}": tour["author"]["name"], "{{AUTHOR_AVATAR}}": tour["author"]["avatar"],
        "{{CREATED_DATE}}": tour["created_date"], "{{DESCRIPTION_HTML}}": desc_html,
        "{{PHOTO_GALLERY_BLOCK}}": "",
        "{{GRADE}}": grade_lbl, "{{MAX_STEEP}}": str(s["max_steep"]), "{{EXPOSURE}}": s["exposure"],
        "{{ASPECT}}": s["aspect"], "{{DISTANCE_KM}}": str(s["distance_km"]),
        "{{ELEV_GAIN_M}}": str(s["elev_gain_m"]), "{{ALT_MIN_M}}": str(s["alt_min_m"]), "{{ALT_MAX_M}}": str(s["alt_max_m"]),
        "{{TOUR_DEEPLINK}}": f"https://app.steepmap.eu/?tour={tour['id']}",
        "{{T_ALL_TOURS}}": t(lang,"all_tours"), "{{T_GET_APP}}": t(lang,"get_app"), "{{T_MODAL_TITLE}}": t(lang,"modal_title"),
        "{{T_MAP_LOADING}}": t(lang,"map_loading"), "{{T_STATS}}": t(lang,"stats"),
        "{{T_GRADE}}": t(lang,"grade"), "{{T_STEEPNESS}}": t(lang,"steepness"), "{{T_EXPOSURE}}": t(lang,"exposure"),
        "{{T_ASPECT}}": t(lang,"aspect"), "{{T_DISTANCE}}": t(lang,"distance"), "{{T_ELEV_GAIN}}": t(lang,"elev_gain"),
        "{{T_LOW_POINT}}": t(lang,"low_point"), "{{T_HIGH_POINT}}": t(lang,"high_point"),
        "{{T_CTA_TITLE}}": t(lang,"cta_title"), "{{T_CTA_BODY}}": t(lang,"cta_body"), "{{T_OPEN_TOUR}}": t(lang,"open_tour"),
        "{{T_SHOW_MAP}}": t(lang,"show_map"), "{{T_PHOTOS}}": t(lang,"photos"), "{{T_EXPLORE_MAP}}": t(lang,"explore_map"),
        "{{T_PRIVACY}}": t(lang,"privacy"), "{{T_TERMS}}": t(lang,"terms"),
        "{{T_M_WEB_T}}": t(lang,"m_web_t"), "{{T_M_WEB_S}}": t(lang,"m_web_s"),
        "{{T_M_AND_S}}": t(lang,"m_and_s"), "{{T_M_SOON}}": t(lang,"m_soon"),
        "{{T_ABOUT}}": EXTRA[lang]["about"], "{{T_MORE_TOURS}}": EXTRA[lang]["more_tours"],
    }
    html = template
    for k, v in tok.items():
        html = html.replace(k, v)
    left = set(re.findall(r"\{\{[A-Z_]+\}\}", html)) - {"{{TOKENS}}", "{{TOUR_ID}}"}
    if left:
        raise SystemExit(f"[{slug}/{lang}] unreplaced tokens: {left}")
    return html, page_path(slug, lang)

def esc(x):
    return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def write_picker(tours):
    """featured/tours.json: what the "Featured tours" picker shows, per language."""
    labels = {lg: {"title": T[lg]["all_tours"], "search": T[lg]["search"], "no_results": T[lg]["no_results"]}
              for lg in LANGS}
    lists = {}
    for lg in LANGS:
        lists[lg] = [{
            "title": tr.get("title_i18n", {}).get(lg) or tr["title"],
            "url": "/" + page_path(tr["slug"], lg),
            "photo": tr["photos"][0] if tr.get("photos") else "",
        } for tr in tours if lg in tour_langs(tr)]
    out = os.path.join(ROOT, "featured", "tours.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"labels": labels, "tours": lists}, f, ensure_ascii=False, indent=1)
    print(f"  picker: {len(tours)} tours")

def write_home_links(tours):
    """Crawlable links to every English tour page, in the home page footer."""
    path = os.path.join(ROOT, "index.html")
    html = open(path, encoding="utf-8").read()
    links = " · ".join(
        f'<a href="/{page_path(tr["slug"], "en")}">{esc(tr["title"])}</a>' for tr in tours if "en" in tour_langs(tr))
    block = ('<!-- featured-links:start -->\n'
             f'    <nav class="footer-featured" aria-label="Featured tours"><span>Featured tours:</span> {links}</nav>\n'
             '    <!-- featured-links:end -->')
    new, n = re.subn(r"<!-- featured-links:start -->.*?<!-- featured-links:end -->", block, html, flags=re.S)
    assert n == 1, "home page footer markers missing"
    open(path, "w", encoding="utf-8").write(new)
    print("  home page: featured links updated")

def load_tours():
    manifest = json.load(open(os.path.join(ROOT, "data", "featured", "manifest.json"), encoding="utf-8"))
    global PLACE, TOURS_ALL
    PLACE = {e["slug"]: {"place": e["place"], "region": e["region"]} for e in manifest["tours"]}
    TOURS_ALL = [json.load(open(os.path.join(ROOT, "data", "featured", f"{e['slug']}.json"), encoding="utf-8"))
                 for e in manifest["tours"]]
    return TOURS_ALL

def update_sitemap(tours):
    path = os.path.join(ROOT, "sitemap.xml")
    xml = open(path, encoding="utf-8").read()
    xml = re.sub(r"\s*<url>\s*<loc>[^<]*/featured/[^<]*</loc>.*?</url>", "", xml, flags=re.S)
    if "xmlns:xhtml" not in xml:
        xml = xml.replace('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
                          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
                          '        xmlns:xhtml="http://www.w3.org/1999/xhtml">')
    blocks, count = [], 0
    for tr in tours:
        langs = tour_langs(tr)
        lastmod = (tr.get("updated_at") or time.strftime("%Y-%m-%d"))[:10]
        for lg in langs:
            alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{a}" href="{SITE}/{page_path(tr["slug"], a)}"/>'
                           for a in langs)
            blocks.append(f"  <url>\n    <loc>{SITE}/{page_path(tr['slug'], lg)}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
                          f"    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>{alts}\n  </url>\n")
            count += 1
    xml = xml.replace("</urlset>", "".join(blocks) + "</urlset>")
    open(path, "w", encoding="utf-8").write(xml)
    print(f"  sitemap: {count} tour pages with language alternates")

def main():
    template = open(os.path.join(ROOT, "featured", "_template.html"), encoding="utf-8").read()
    tours = load_tours()
    count = 0
    # remove pages from an earlier build for languages a tour no longer has
    wanted = {page_path(tr["slug"], lg) for tr in tours for lg in tour_langs(tr)}
    for tr in tours:
        for lg in LANGS:
            rel = page_path(tr["slug"], lg)
            if rel not in wanted and os.path.exists(os.path.join(ROOT, rel)):
                os.remove(os.path.join(ROOT, rel))
                print(f"  removed stale page: {rel}")
    for tour in tours:
        langs = tour_langs(tour)
        for lang in langs:
            html, rel = render(tour, lang, template)
            out = os.path.join(ROOT, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8").write(html)
            count += 1
        print(f"  {tour['slug']}: {', '.join(langs)}")
    write_picker(tours)
    write_home_links(tours)
    update_sitemap(tours)
    print(f"Generated {count} pages from {len(tours)} tour(s).")

if __name__ == "__main__":
    main()
