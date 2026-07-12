# SteepMap — Website

Public website for **SteepMap**, the backcountry ski-tour app: discover new tours,
keep a bucket list, repeat your friends' lines, and plan with slope & aspect overlays.

The whole public presence (marketing + legal) lives here and is served from one domain
(**steepmap.eu**).

## Structure

```
.
├── index.html              # Marketing landing page (the homepage)
└── legal/
    ├── privacy.html        # Privacy Policy
    └── delete-account.html # Account & Data Deletion (required by the app stores)
```

## Deploying

Static site — no build step. Host the repo root as-is (GitHub Pages, Cloudflare Pages,
Netlify, Vercel, …) and point `steepmap.eu` at it.

Suggested URLs once deployed:

| Page | Path |
|------|------|
| Home | `/` |
| Privacy policy | `/legal/privacy.html` |
| Delete account | `/legal/delete-account.html` |

## Placeholders to replace later

- **Imagery** — the landing page uses Unsplash photos as placeholders (see the credit
  line in the footer) and CSS mockups instead of real app screenshots. Swap in real
  screenshots / owned photography before launch.
- **Store links** — the "Get the app" modal's Android / iOS / Web links are `#`
  placeholders. Drop in the real Google Play / App Store / web-app URLs when live
  (there's a comment in `index.html` marking the Android link).
- **Contact email** — currently `alpinemapapp@gmail.com`. Update if a SteepMap-branded
  address is set up.
