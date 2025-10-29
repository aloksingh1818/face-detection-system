Netlify frontend + Render backend — deployment guide

This repository already contains a static frontend in `docs/` and a Flask backend (`app.py`).
Follow the steps below to deploy the frontend to Netlify and the backend to Render.

1) Deploy backend to Render
----------------------------
- Push your repo changes to GitHub (if not already):

```bash
git add -A
git commit -m "Prepare for Netlify + Render deployment: CORS, Procfile, docs/"
git push origin main
```

- Create a Render account and click "New" → "Web Service" → connect this repo.
- Use `main` branch. Render will detect Python and install `requirements.txt`.
- Start command (explicit):

```
gunicorn app:app --bind 0.0.0.0:$PORT
```

- Add any environment variables your app needs via Render dashboard (for example SECRET_KEY). Render injects $PORT automatically.
- Wait for the deployment to finish. Note the public URL (e.g. `https://face-detection-system.onrender.com`).

2) Prepare the frontend for Netlify
----------------------------------
- The static frontend is in `docs/`. By default it contains `docs/index.html` which has a placeholder `window.API_BASE = ''`.
- After your Render deployment is ready, edit `docs/index.html` and set `window.API_BASE` to your Render URL. Example:

```html
<script>
  window.API_BASE = 'https://your-app.onrender.com';
  window.STATIC_BASE = '';
  window.FACEATTEND_CONFIG = { RECOGNITION_COOLDOWN_MS: 2000, SOUND_COOLDOWN_MS: 30000, MIN_CONSECUTIVE_FRAMES: 3 };
</script>
```

Commit and push that change.

3) Deploy frontend to Netlify
----------------------------
Option A — Connect repo (recommended):

- Go to https://app.netlify.com and create a new site from Git.
- Choose GitHub and select this repository.
- For build settings:
  - Build command: (leave empty) — the site is already static
  - Publish directory: `docs`
- Deploy site. Netlify will build and publish the static site.

Option B — Drag-and-drop (fast):

- Zip the `docs/` folder contents and drag it into Netlify's drag-and-drop deploy area. This is manual and doesn't auto-update on pushes.

4) Verify & test
-----------------
- Open your Netlify site URL. Open DevTools → Network and confirm requests to `${API_BASE}/api/*` go to your Render URL and return responses.
- If you see CORS errors, confirm the Render app has CORS enabled on `/api/*` (this repo has `flask-cors` enabled in `app.py`).

Notes and tips
--------------
- If you prefer Netlify to inject the Render URL automatically at build time, you can use Netlify environment variables and a tiny build script to write them into `docs/index.html` during the build. For simplicity, editing `docs/index.html` is a straightforward approach.
- Tighten CORS origins in `app.py` when you know your Netlify domain:

```python
CORS(app, resources={r"/api/*": {"origins": "https://your-netlify-site.netlify.app"}})
```

- The repository includes `netlify.toml` which sets the publish directory to `docs/`.

If you want, I can:
- Automate replacing `window.API_BASE` from a Netlify environment variable during build.
- Add `admin_dashboard.html` and `register_student.html` static copies into `docs/` (they currently require server-side Jinja to work).
