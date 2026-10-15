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
ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRADE_COLOR = {"Easy": "#22c55e", "Medium": "#3b82f6", "Hard": "#ef4444", "Very Hard": "#111827"}
GRADE_KEY   = {0: "easy", 10: "medium", 20: "hard", 30: "veryHard"}  # (kept for reference)

# ── UI label catalog ────────────────────────────────────────────────────────
# en is the base; other languages fall back to en for any missing key.
T = {
 "en": {"all_tours":"Featured tours","get_app":"Get the app","modal_title":"Get STEEP map",
   "map_loading":"Loading 3D map…","stats":"Tour stats","grade":"Grade","steepness":"Max steepness",
   "exposure":"Exposure","aspect":"Aspect","distance":"Distance","elev_gain":"Elevation gain",
   "low_point":"Lowest point","high_point":"Highest point","cta_title":"Take this tour with you",
   "cta_body":"Open this exact tour in Steep to navigate it offline, with slope-angle and aspect overlays, 3D terrain and the GPS track.",
   "open_tour":"Open this tour in Steep","show_map":"Show map","prev":"Previous","next":"Next","photos":"photos","explore_map":"Explore map",
   "privacy":"Privacy","terms":"Terms","m_web_t":"Web app","m_web_s":"Open it in your browser",
   "m_and_s":"Get it on Google Play","m_soon":"Coming soon",
   "grade_label":{"Easy":"Easy","Medium":"Medium","Hard":"Hard","Very Hard":"Very Hard"},
   "meta_suffix":"ski tour | Steep",
   "meta_desc":"{title} ski tour: {km} km, {gain} m ascent, up to {steep}° ({grade}). See the tour and take it with you in the Steep app."},
 "de": {"all_tours":"Ausgewählte Touren","get_app":"App holen","modal_title":"STEEP map holen",
   "map_loading":"3D-Karte wird geladen…","stats":"Tourdaten","grade":"Schwierigkeit","steepness":"Max. Steilheit",
   "exposure":"Exposition","aspect":"Ausrichtung","distance":"Distanz","elev_gain":"Höhenmeter",
   "low_point":"Tiefster Punkt","high_point":"Höchster Punkt","cta_title":"Nimm diese Tour mit",
   "cta_body":"Öffne genau diese Tour in Steep, um sie offline zu navigieren – mit Hangneigungs- und Expositions-Overlays, 3D-Gelände und dem GPS-Track.",
   "open_tour":"Tour in Steep öffnen","show_map":"Karte zeigen","prev":"Zurück","next":"Weiter","photos":"Fotos","explore_map":"Karte erkunden",
   "privacy":"Datenschutz","terms":"AGB","m_web_t":"Web-App","m_web_s":"Im Browser öffnen",
   "m_and_s":"Bei Google Play","m_soon":"Demnächst",
   "grade_label":{"Easy":"Leicht","Medium":"Mittel","Hard":"Schwer","Very Hard":"Sehr schwer"},
   "meta_suffix":"Skitour | Steep",
   "meta_desc":"{title} Skitour: {km} km, {gain} Hm, bis zu {steep}° ({grade}). Sieh dir die Tour an und nimm sie mit der Steep-App mit."},
 "fr": {"all_tours":"Sorties en vedette","get_app":"Obtenir l'app","modal_title":"Obtenir STEEP map",
   "map_loading":"Chargement de la carte 3D…","stats":"Infos de la sortie","grade":"Difficulté","steepness":"Pente max.",
   "exposure":"Exposition","aspect":"Orientation","distance":"Distance","elev_gain":"Dénivelé positif",
   "low_point":"Point le plus bas","high_point":"Point le plus haut","cta_title":"Emportez cette sortie",
   "cta_body":"Ouvrez cette sortie exacte dans Steep pour la suivre hors ligne, avec les calques de pente et d'exposition, le relief 3D et la trace GPS.",
   "open_tour":"Ouvrir dans Steep","show_map":"Voir la carte","prev":"Précédent","next":"Suivant","photos":"photos","explore_map":"Explorer la carte",
   "privacy":"Confidentialité","terms":"Conditions","m_web_t":"Application web","m_web_s":"Ouvrir dans le navigateur",
   "m_and_s":"Disponible sur Google Play","m_soon":"Bientôt disponible",
   "grade_label":{"Easy":"Facile","Medium":"Moyen","Hard":"Difficile","Very Hard":"Très difficile"},
   "meta_suffix":"sortie à ski | Steep",
   "meta_desc":"{title} sortie à ski : {km} km, {gain} m de dénivelé, jusqu'à {steep}° ({grade}). Découvrez la sortie et emportez-la dans l'app Steep."},
 "it": {"all_tours":"Tour in evidenza","get_app":"Scarica l'app","modal_title":"Scarica STEEP map",
   "map_loading":"Caricamento mappa 3D…","stats":"Dati del tour","grade":"Difficoltà","steepness":"Pendenza max",
   "exposure":"Esposizione","aspect":"Orientamento","distance":"Distanza","elev_gain":"Dislivello positivo",
   "low_point":"Punto più basso","high_point":"Punto più alto","cta_title":"Porta con te questo tour",
   "cta_body":"Apri esattamente questo tour in Steep per seguirlo offline, con i livelli di pendenza ed esposizione, il terreno 3D e la traccia GPS.",
   "open_tour":"Apri in Steep","show_map":"Mostra mappa","prev":"Precedente","next":"Successiva","photos":"foto","explore_map":"Esplora la mappa",
   "privacy":"Privacy","terms":"Termini","m_web_t":"App web","m_web_s":"Aprila nel browser",
   "m_and_s":"Scaricala su Google Play","m_soon":"Prossimamente",
   "grade_label":{"Easy":"Facile","Medium":"Medio","Hard":"Difficile","Very Hard":"Molto difficile"},
   "meta_suffix":"sci alpinismo | Steep",
   "meta_desc":"{title} tour sci: {km} km, {gain} m di dislivello, fino a {steep}° ({grade}). Guarda il tour e portalo con te nell'app Steep."},
 "es": {"all_tours":"Rutas destacadas","get_app":"Obtener la app","modal_title":"Obtener STEEP map",
   "map_loading":"Cargando mapa 3D…","stats":"Datos de la ruta","grade":"Dificultad","steepness":"Pendiente máx.",
   "exposure":"Exposición","aspect":"Orientación","distance":"Distancia","elev_gain":"Desnivel positivo",
   "low_point":"Punto más bajo","high_point":"Punto más alto","cta_title":"Llévate esta ruta",
   "cta_body":"Abre esta misma ruta en Steep para seguirla sin conexión, con las capas de pendiente y orientación, el terreno 3D y el track GPS.",
   "open_tour":"Abrir en Steep","show_map":"Ver mapa","prev":"Anterior","next":"Siguiente","photos":"fotos","explore_map":"Explorar el mapa",
   "privacy":"Privacidad","terms":"Términos","m_web_t":"App web","m_web_s":"Ábrela en tu navegador",
   "m_and_s":"Disponible en Google Play","m_soon":"Próximamente",
   "grade_label":{"Easy":"Fácil","Medium":"Media","Hard":"Difícil","Very Hard":"Muy difícil"},
   "meta_suffix":"ruta de esquí | Steep",
   "meta_desc":"{title} ruta de esquí: {km} km, {gain} m de desnivel, hasta {steep}° ({grade}). Mira la ruta y llévatela en la app Steep."},
 "ja": {"all_tours":"注目のツアー","get_app":"アプリを入手","modal_title":"STEEP map を入手",
   "map_loading":"3Dマップを読み込み中…","stats":"ツアー情報","grade":"グレード","steepness":"最大斜度",
   "exposure":"露出度","aspect":"斜面方位","distance":"距離","elev_gain":"獲得標高",
   "low_point":"最低地点","high_point":"最高地点","cta_title":"このツアーを持ち歩こう",
   "cta_body":"このツアーをそのまま Steep で開けば、斜度・方位オーバーレイ、3D地形、GPSトラックとともにオフラインでナビゲーションできます。",
   "open_tour":"Steep で開く","show_map":"マップを表示","prev":"前へ","next":"次へ","photos":"枚の写真","explore_map":"マップを見る",
   "privacy":"プライバシー","terms":"利用規約","m_web_t":"ウェブアプリ","m_web_s":"ブラウザで開く",
   "m_and_s":"Google Play で入手","m_soon":"近日公開",
   "grade_label":{"Easy":"初級","Medium":"中級","Hard":"上級","Very Hard":"最上級"},
   "meta_suffix":"スキーツアー | Steep",
   "meta_desc":"{title} スキーツアー：{km} km、獲得標高 {gain} m、最大 {steep}°（{grade}）。ツアーを見て、Steep アプリで持ち歩こう。"},
}

def t(lang, key):
    return T.get(lang, {}).get(key, T["en"][key])

PHOTO_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
  'stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/>'
  '<circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>')

def page_path(slug, lang):
    return f"featured/{slug}.html" if lang == "en" else f"{lang}/featured/{slug}.html"

def page_strings(tour, lang):
    """All text for one language: UI labels + tour text. Shipped in every page so
    the language switcher can update the text in place without reloading."""
    s = tour["stats"]
    title = tour.get("title_i18n", {}).get(lang) or tour["title"]
    desc_txt = tour["description"].get(lang) or tour["description"].get(tour.get("source_lang") or "en")
    grade_lbl = t(lang, "grade_label").get(s["grade"], s["grade"])
    out = {k: v for k, v in T[lang].items() if k != "grade_label" and k != "meta_desc"}
    out.update({
        "title": title,
        "description": "<p>" + desc_txt.replace(chr(10), "</p><p>") + "</p>" if desc_txt else "",
        "grade_val": grade_lbl,
        "meta_title": f"{title} {t(lang, 'meta_suffix')}",
        "meta_desc": t(lang, "meta_desc").format(
            title=title, km=s["distance_km"], gain=s["elev_gain_m"], steep=s["max_steep"], grade=grade_lbl),
    })
    return out

def render(tour, lang, template):
    slug = tour["slug"]
    s = tour["stats"]
    title = tour.get("title_i18n", {}).get(lang) or tour["title"]
    desc_txt = tour["description"].get(lang) or tour["description"].get(tour.get("source_lang") or "en")
    grade_lbl = t(lang, "grade_label").get(s["grade"], s["grade"])

    # Alternates: host-relative for the in-page switcher (works on localhost and
    # prod); absolute for the SEO hreflang block.
    rel = {lg: ("/" + page_path(slug, lg)) for lg in LANGS}
    hreflang = "\n".join(
        f'<link rel="alternate" hreflang="{lg}" href="{SITE}{rel[lg]}" />' for lg in LANGS
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{rel["en"]}" />'
    canonical = f"{SITE}{rel[lang]}"

    photos = tour.get("photos", [])
    track_color = GRADE_COLOR.get(s["grade"], "#3b82f6")
    meta_title = f"{title} {t(lang,'meta_suffix')}"
    meta_desc = t(lang, "meta_desc").format(
        title=title, km=s["distance_km"], gain=s["elev_gain_m"], steep=s["max_steep"], grade=grade_lbl)
    ogimg = photos[0] if photos else f"{SITE}/media/brand/og-cover.jpg"
    jsonld = ('<script type="application/ld+json">\n' + json.dumps({
        "@context": "https://schema.org", "@type": "TouristTrip", "name": title,
        "description": meta_desc, "image": ogimg, "touristType": "Ski touring / backcountry skiing",
        "url": canonical, "inLanguage": lang,
        "provider": {"@type": "Organization", "name": "Steep", "url": SITE + "/"},
    }, ensure_ascii=False) + "\n</script>")

    gallery = ""  # photos live in the in-map strip; no separate bottom gallery
    toggle = (f'<button id="mediaToggle" type="button" aria-label="{t(lang,"photos")}" '
              f'data-cover="{photos[0]}"><span class="mt-label">'
              f'<span class="mt-icon">{PHOTO_ICON}</span>'
              f'<span class="mt-count">{len(photos)} {t(lang,"photos")}</span></span></button>') if photos else ""
    desc_html = "<p>" + desc_txt.replace("\n", "</p><p>") + "</p>" if desc_txt else ""

    tok = {
        "{{LANG}}": lang, "{{SLUG}}": slug, "{{CANONICAL_URL}}": canonical,
        "{{HREFLANG_BLOCK}}": hreflang, "{{LANG_ALTERNATES_JSON}}": json.dumps(rel),
        "{{ASSET_VER}}": str(int(time.time())),
        "{{I18N_JSON}}": json.dumps({lg: page_strings(tour, lg) for lg in LANGS}, ensure_ascii=False).replace("</", "<\/"),
        "{{META_TITLE}}": meta_title, "{{META_DESCRIPTION}}": meta_desc, "{{OG_IMAGE}}": ogimg, "{{JSONLD_BLOCK}}": jsonld,
        "{{TRACK_GEOJSON}}": json.dumps(tour["track"]), "{{MAP_CENTER}}": json.dumps(tour["center"]),
        "{{MAP_ZOOM}}": str(tour["zoom"]), "{{TRACK_COLOR}}": track_color,
        "{{PHOTOS_JSON}}": json.dumps(photos), "{{MEDIA_TOGGLE_BLOCK}}": toggle,
        "{{TOUR_TITLE}}": title, "{{REGION}}": "",
        "{{AUTHOR_NAME}}": tour["author"]["name"], "{{AUTHOR_AVATAR}}": tour["author"]["avatar"],
        "{{CREATED_DATE}}": tour["created_date"], "{{DESCRIPTION_HTML}}": desc_html,
        "{{PHOTO_GALLERY_BLOCK}}": gallery,
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
    }
    html = template
    for k, v in tok.items():
        html = html.replace(k, v)
    left = set(re.findall(r"\{\{[A-Z_]+\}\}", html)) - {"{{TOKENS}}", "{{TOUR_ID}}"}
    if left:
        raise SystemExit(f"[{slug}/{lang}] unreplaced tokens: {left}")
    return html, page_path(slug, lang)

def main():
    template = open(os.path.join(ROOT, "featured", "_template.html"), encoding="utf-8").read()
    data_files = glob.glob(os.path.join(ROOT, "data", "featured", "*.json"))
    count = 0
    for f in data_files:
        tour = json.load(open(f, encoding="utf-8"))
        for lang in LANGS:
            html, rel = render(tour, lang, template)
            out = os.path.join(ROOT, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8").write(html)
            count += 1
        print(f"  {tour['slug']}: {len(LANGS)} languages")
    print(f"Generated {count} pages from {len(data_files)} tour(s).")

if __name__ == "__main__":
    main()
