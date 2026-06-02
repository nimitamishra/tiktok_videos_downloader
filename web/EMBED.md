# Adding this to your portfolio site

Copy the entire `web/` folder into your site, e.g.:

```text
your-site/
  projects/
    tiktok-export-downloader/
      index.html
      css/
      js/
```

## Requirements

- Serve over **HTTPS** (or `localhost`) so ES modules load correctly.
- Do **not** open `index.html` via `file://` — browsers block module imports.

### Local preview

```bash
cd web
python3 -m http.server 8080
# open http://localhost:8080
```

### GitHub Pages (same repo)

Enable Pages for the `/web` folder, or move `web/*` to `/docs` and set Pages source to `/docs`.

## Customize

In `index.html`, set the GitHub link on `<body>`:

```html
<body data-repo="https://github.com/YOUR_USERNAME/YOUR_REPO">
```

## iframe embed (optional)

```html
<iframe
  src="/projects/tiktok-export-downloader/"
  title="TikTok Export Downloader"
  width="100%"
  height="900"
  style="border: 0; border-radius: 12px; max-width: 720px;"
></iframe>
```

Adjust height to fit your layout.
