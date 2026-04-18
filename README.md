# Ideas Block — Website

The official website of **Ideas Block** (VšĮ Idėjų blokas LT), a cultural non-profit organisation based in Vilnius, Lithuania, active since 2014.

---

## Concept

Ideas Block is an independent cultural organisation that produces exhibitions, residencies, workshops, publications, and events. The website serves two simultaneous roles:

1. **Living platform** — editorial blog, upcoming events, open calls, publications, supporter portal, downloadable resources
2. **10-year archive** — 276 blog posts, 154 events, 51 products, and years of cultural production, fully searchable and publicly accessible

The aesthetic direction is dark editorial — comparable to Serpentine Gallery, Mousse Magazine, or e-flux — combining serif display type with clean body text, high contrast, and generous whitespace.

---

## Architecture

### Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Django 5.2 | Python, ORM, i18n, batteries-included |
| CMS | Wagtail 6.4 | Editorial admin, StreamField, page tree, used by cultural orgs worldwide |
| Database | SQLite (dev) / PostgreSQL (production) | Simple locally, robust in production |
| Static files | WhiteNoise (production) | No separate static server needed |
| Payments | Stripe | Ticket sales + recurring supporter subscriptions |
| Analytics | Plausible | Privacy-first, GDPR-compliant, no consent banner needed |
| Email | Django SMTP / console (dev) | Ticket confirmations, contact form |
| Newsletter | MailerLite API v2 | Subscriber management |
| CSS | Custom design system (`ideas_block/static/css/main.css`) | ~2000 lines, dark theme |
| JS | Vanilla JS only | No framework — mobile menu, newsletter AJAX, copy-to-clipboard |

### Page Tree (Wagtail)

```
Root
└── Home (HomePage)
    ├── Blog (BlogIndexPage)                   /blog/
    │   └── BlogPostPage × 276                 /blog/slug/
    ├── Events (EventsIndexPage)               /events/
    │   └── EventPage × 154                    /events/slug/
    ├── Projects (ProjectsIndexPage)           /projects/
    │   └── ProjectPage                        /projects/slug/
    │       ├── Covid-19 Creative Outlet
    │       ├── Mind Sharpener
    │       ├── Artist Residency Programme
    │       └── Arttice
    ├── Shop (ProductsIndexPage)               /shop/
    │   └── ProductPage × 51                   /shop/slug/
    ├── People (PeoplePage)                    /people/
    │   └── PersonPage                         /people/slug/
    ├── Open Calls (OpenCallsIndexPage)        /open-calls/
    │   ├── OpenCallPage (active)              /open-calls/slug/
    │   └── Past Calls (PastCallsIndexPage)    /open-calls/past-calls/
    │       └── OpenCallPage × 13             /open-calls/past-calls/slug/
    ├── Publications (PublicationsIndexPage)   /publications/
    │   └── PublicationPage                    /publications/slug/
    ├── Press (PressPage)                      /press/
    ├── About (AboutPage)                      /about/
    │   ├── Space (SpacePage)                  /about/space/
    │   ├── Transparency (TransparencyPage)    /about/transparency/
    │   └── Privacy Policy (RichPage)          /about/privacy-policy/
    └── Search (Page)                          /search/
```

Contact details (address, email) live on the About page — there is no separate Contact page.

### Apps

| App | Purpose |
|---|---|
| `home` | HomePage — hero, featured content, context for homepage sections |
| `blog` | BlogIndexPage, BlogPostPage — full archive, tags, categories, language filter |
| `events` | EventsIndexPage, EventPage — upcoming/past split, Stripe tickets, year filter |
| `projects` | ProjectsIndexPage, ProjectPage — rich project objects with status, dates, type, gallery, linked participants, and gated downloads |
| `products` | ProductsIndexPage, ProductPage — shop items, Stripe checkout |
| `people` | PeoplePage, PersonPage — team portraits, bios, Instagram, related posts |
| `opencalls` | OpenCallsIndexPage, OpenCallPage — residency/commission calls, deadlines, apply CTA |
| `publications` | PublicationsIndexPage, PublicationPage — books, catalogues, zines, journals, articles, music albums, exhibitions, artworks; ISBN, buy/download |
| `press` | PressPage — press contact, downloadable kits, press images, coverage log, boilerplate |
| `core` | ContactPage, SpacePage, AboutPage, RichPage — shared pages and utilities |
| `tickets` | Stripe checkout, webhook, QR ticket generation, door scanner, subscriptions |
| `members` | Accounts, roles, access control, Stripe subscription linking, dashboard |
| `search` | Site-wide search with type filters and result counts |

### Non-Wagtail URLs

| URL | View / purpose |
|---|---|
| `/search/` | Full-text search across all page types |
| `/files/download/<id>/` | Gated file download for project attachments |
| `/tickets/checkout/<id>/` | Stripe Checkout for events/products |
| `/tickets/support/` | Supporter subscription page |
| `/tickets/scanner/` | Staff QR scanner (requires login) |
| `/tickets/webhook/stripe/` | Stripe webhook receiver |
| `/members/login/` | Sign in |
| `/members/register/` | Create account |
| `/members/dashboard/` | Account info, access level, order history |
| `/core/newsletter/signup/` | MailerLite AJAX endpoint |
| `/i18n/set_language/` | Django language switcher (POST) |
| `/api/v2/` | Wagtail headless API (pages, images, docs) |
| `/sitemap.xml` | Sitemap for all live Wagtail pages |
| `/blog/feed/` | RSS feed for blog posts |
| `/events/feed/` | RSS feed for upcoming events |
| `/admin/` | Wagtail CMS admin |

---

## Access Control

The platform has a three-tier content access system applied to project downloads (and extensible to other content types).

### Access Levels

| Level | Who can access |
|---|---|
| `public` | Anyone — no login required |
| `members` | Any registered account |
| `payers` | Active subscriber (any plan) **or** anyone with at least one paid order |

### Account Types

Account type is set per member in the Wagtail/Django admin. Supporter and Patron status is determined automatically by the linked Stripe subscription.

| Type | How assigned | Access level |
|---|---|---|
| **Friend** | Default on registration (free account) | Members |
| **Collaborator** | Set by staff — external artists, practitioners | Members |
| **Staff** | Set by staff — internal org team | Full (all levels) |
| **Supporter** | Active Stripe subscription at €5/mo | Payers |
| **Patron** | Active Stripe subscription at €15/mo | Payers |

### Template tag

Any template can gate content with:

```django
{% load members_tags %}
{% if request.user|can_access:"payers" %}
  ... restricted content ...
{% endif %}
```

### Download gating

Project download files set their own access level in the CMS. When a visitor requests a gated file at `/files/download/<id>/`:
- If not logged in → redirected to `/members/login/`
- If logged in but not a payer → 403 with a link to `/tickets/support/`
- If access granted → file served as an attachment

---

## Projects

Projects are rich objects suitable for exhibitions, residencies, community programmes, digital work, research, and performances.

### Fields

| Field | Purpose |
|---|---|
| Title, subtitle | Display name and optional secondary title |
| Status | `In progress` / `Completed` / `Ongoing` / `Archived` |
| Project type | Exhibition / Residency / Community / Digital / Research / Publication / Performance / Other |
| Start date, end date | Date range shown as "Jan 2023 – Jun 2024" or "Jan 2023 – present" |
| Year | Single year (for archival or undated projects) |
| External URL | Project website or documentation link |
| Intro | Short description (up to 500 chars) — used on index cards |
| Featured image | Hero image |
| Body (StreamField) | Rich content: headings, paragraphs with embed support, images with optional captions |
| Gallery | Additional image grid below the body |
| Participants | Linked `PersonPage` entries (shown with photo + role + link to profile) |
| Collaborators | Free-text for external collaborators not in the People section |
| Downloads | Attached files with per-file access level (public / members / payers) |

### Index filters

The projects index (`/projects/`) supports filtering by **type** and **year**, combinable in the URL as `?type=exhibition&year=2023`. Full-text search is also available.

---

## Publications

Publications support the following types, selectable per entry:

| Value | Label |
|---|---|
| `book` | Book |
| `catalogue` | Exhibition catalogue |
| `zine` | Zine / artist book |
| `journal` | Journal / magazine |
| `article` | Article |
| `report` | Report |
| `online` | Online publication |
| `album` | Music album |
| `exhibition` | Exhibition |
| `artwork` | Artwork |
| `other` | Other |

Each publication can have a cover image, ISBN, authors, publisher, price, external buy URL, and an open-access PDF download.

The index (`/publications/`) supports filtering by type and year, and full-text search.

---

## Press

The Press page (`/press/`) is a single CMS-managed page (not an index) containing:

- **Press contact** — name, email, phone
- **Press kits** — downloadable ZIP/PDF files with title and description
- **Press images** — high-res images with caption and credit
- **Boilerplate** — standard organisation description with a "Copy to clipboard" button
- **Coverage log** — logged press articles with headline, publication, date, URL, and language (EN/LT)

---

## Admin Credentials

**Wagtail admin URL:** `http://localhost:8000/admin/`

| Field | Value |
|---|---|
| Username | `admin` |
| Email | `admin@ideas-block.com` |
| Password | *(set during initial setup — see below to reset)* |

To reset the admin password:
```bash
python manage.py changepassword admin
```

To create a new superuser:
```bash
python manage.py createsuperuser
```

---

## Development Setup

### Prerequisites

- Python 3.12+
- Git

### 1. Clone and set up virtual environment

```bash
git clone <repo-url> ideas_block_website
cd ideas_block_website/new_website
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
# Open .env and fill in your Stripe test keys at minimum.
# Everything else has safe defaults for local development.
```

The `.env` file is loaded automatically via `python-dotenv` (already in `requirements.txt`). For local dev, `DJANGO_SETTINGS_MODULE` defaults to `ideas_block.settings.dev` which uses SQLite and the console email backend — no database or SMTP setup needed.

### 3. Database and initial pages

```bash
python manage.py migrate
python manage.py setup_pages        # creates open-calls, press, publications pages
python manage.py createsuperuser    # or: changepassword admin
```

### 4. Run the development server

```bash
python manage.py runserver 0.0.0.0:8000
```

Access at `http://localhost:8000` and the admin at `http://localhost:8000/admin/`.

### 5. Access from other devices on the local network

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit `http://<your-local-ip>:8000` from any device on the same Wi-Fi network. Find your IP with `ipconfig getifaddr en0` (macOS) or `ip addr` (Linux).

### Static files

The CSS source is at `ideas_block/static/css/main.css`. In development, Django serves it directly — no build step needed. The `dev.py` settings override `ManifestStaticFilesStorage` to use plain `StaticFilesStorage`.

### Preview error pages

Visit these URLs in development to preview the custom 404/500 pages:
- `http://localhost:8000/__404__/`
- `http://localhost:8000/__500__/`

> **Note:** The standard Django debug error pages are shown in development when `DEBUG=True`. This is correct. The custom 404/500 only activate in production (`DEBUG=False`).

---

## Deployment — VPS (bare metal / VM)

### Server requirements

- Ubuntu 22.04+
- Python 3.12, pip, venv
- Nginx
- Gunicorn (or uWSGI)
- PostgreSQL 14+
- Certbot (Let's Encrypt SSL)

### 1. Server setup

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip nginx postgresql certbot python3-certbot-nginx
```

### 2. PostgreSQL

```bash
source .env  # load DB_* variables
sudo -u postgres psql \
  -c "CREATE DATABASE $DB_NAME;" \
  -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" \
  -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
```

### 3. Deploy code

```bash
cd /srv
git clone <repo-url> ideas_block
cd ideas_block/new_website
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 4. Production environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
DJANGO_SETTINGS_MODULE=ideas_block.settings.production
DJANGO_SECRET_KEY=<generate a fresh one>
DB_PASSWORD=<your postgres password>
EMAIL_HOST_USER=<your smtp login>
EMAIL_HOST_PASSWORD=<your smtp password>
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_SUPPORTER=price_...
STRIPE_PRICE_PATRON=price_...
MAILERLITE_API_KEY=<your mailerlite token>
```

See the **Environment Variables Reference** section for all available options.

### 5. Initialise

```bash
python manage.py migrate --settings=ideas_block.settings.production
python manage.py collectstatic --no-input --settings=ideas_block.settings.production
python manage.py setup_pages --settings=ideas_block.settings.production
python manage.py createsuperuser --settings=ideas_block.settings.production
```

### 6. Gunicorn systemd service

`/etc/systemd/system/ideas_block.service`:

```ini
[Unit]
Description=Ideas Block Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/ideas_block/new_website
EnvironmentFile=/srv/ideas_block/new_website/.env
ExecStart=/srv/ideas_block/new_website/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/ideas_block.sock \
    ideas_block.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ideas_block
sudo systemctl start ideas_block
```

### 7. Nginx

`/etc/nginx/sites-available/ideas-block.com`:

```nginx
server {
    listen 80;
    server_name ideas-block.com www.ideas-block.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ideas-block.com www.ideas-block.com;

    ssl_certificate /etc/letsencrypt/live/ideas-block.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ideas-block.com/privkey.pem;

    client_max_body_size 50M;  # for image uploads

    location /static/ {
        alias /srv/ideas_block/new_website/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /srv/ideas_block/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://unix:/run/ideas_block.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ideas-block.com /etc/nginx/sites-enabled/
sudo certbot --nginx -d ideas-block.com -d www.ideas-block.com
sudo nginx -t && sudo systemctl reload nginx
```

### 8. Media files

Media is **not in git**. Upload once and sync as needed:

```bash
# Initial upload from local dev machine
rsync -avz --progress \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/ \
  user@your-server:/srv/ideas_block/media/

# Subsequent syncs (only changed files)
rsync -avz --update \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/ \
  user@your-server:/srv/ideas_block/media/
```

For high-traffic production: migrate media to object storage (Cloudflare R2, Hetzner Storage Box, AWS S3) using `django-storages`.

---

## Deployment — Namecheap Shared Hosting (cPanel)

This is the simplest deployment path — no server administration required. Namecheap's shared hosting runs Apache + Phusion Passenger, which serves Django via WSGI.

**Files already in the repo for this:**
- `passenger_wsgi.py` — Passenger entry point (place manually in app root, outside the repo)
- `ideas_block/settings/cpanel.py` — cPanel-specific settings (SQLite, Apache-served static)

### Directory layout on the server

```
~/ideas_block/                  ← cPanel application root (set in Step 2)
    passenger_wsgi.py           ← copied manually from the repo (Step 3)
    .env                        ← created manually (Step 4) — never in git
    db.sqlite3                  ← transferred from local (Step 6) — never in git
    git/                        ← the cloned repository (Step 3)
        manage.py
        requirements.txt
        passenger_wsgi.py       ← source copy lives here in git
        static/                 ← populated by collectstatic (Step 7)
        media/                  ← populated by rsync (Step 8)
        ideas_block/
        templates/
        ...
```

`.env` and `db.sqlite3` live in the application root, **outside** the git repo — they are never committed. `static/` and `media/` live inside `git/` and are served by WhiteNoise through Passenger — no `public_html` involvement.

### Constraints vs. VPS

| | VPS / Docker | cPanel shared |
|---|---|---|
| Database | PostgreSQL | SQLite (stored outside `public_html`) |
| Static files | WhiteNoise / Nginx | WhiteNoise via Passenger (`git/static/`) |
| Process manager | systemd / Docker | Passenger (managed by cPanel) |
| SSL | Certbot | AutoSSL (one click in cPanel) |
| SSH access | Full root | Yes, but no sudo |

---

### Step 1 — Enable SSH on Namecheap

cPanel → **SSH Access** → enable SSH and add your public key. All subsequent steps use SSH.

---

### Step 2 — Create the Python app in cPanel

1. cPanel → **Software** → **Setup Python App**
2. Click **Create Application** and fill in:

| Field | Value |
|---|---|
| Python version | `3.12` (or highest available) |
| Application root | `ideas_block` *(folder in your home dir — cPanel creates it)* |
| Application URL | `ideas-block.com` |
| Application startup file | `passenger_wsgi.py` |
| Application entry point | `application` |

3. Click **Create** — cPanel creates the virtualenv and shows you the activation command. Note it down.

---

### Step 3 — Upload the code and place passenger_wsgi.py

```bash
# Clone the repo into ~/ideas_block/git/
cd ~/ideas_block
git clone <repo-url> git

# Copy passenger_wsgi.py from the repo up to the app root
cp ~/ideas_block/git/passenger_wsgi.py ~/ideas_block/passenger_wsgi.py
```

`passenger_wsgi.py` must sit directly in `~/ideas_block/` (the app root), not inside the `git/` subfolder. The copy in `git/` is just the source that lives in version control.

---

### Step 4 — Configure .env

```bash
# Create .env in the app root (outside the git repo)
cp ~/ideas_block/git/.env.example ~/ideas_block/.env
nano ~/ideas_block/.env
```

Set at minimum:

```env
DJANGO_SETTINGS_MODULE=ideas_block.settings.cpanel
DJANGO_SECRET_KEY=<generate one — see .env.example>
SITE_URL=https://ideas-block.com
ALLOWED_HOSTS=ideas-block.com,www.ideas-block.com
EMAIL_HOST_USER=<your smtp login>
EMAIL_HOST_PASSWORD=<your smtp password>
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_SUPPORTER=price_...
STRIPE_PRICE_PATRON=price_...
MAILERLITE_API_KEY=<your token>
PLAUSIBLE_DOMAIN=ideas-block.com
```

> Find your cPanel username in cPanel → General Information, or run `whoami` via SSH.

---

### Step 5 — Install Python dependencies

```bash
# Activate the virtualenv cPanel created (command shown in Setup Python App)
source /home/<username>/virtualenv/ideas_block/3.12/bin/activate

pip install -r ~/ideas_block/git/requirements.txt
```

---

### Step 6 — Transfer the database

```bash
# From your local machine — copy the SQLite database to the app root (not inside git/)
scp /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/db.sqlite3 \
  <username>@<server>:~/ideas_block/db.sqlite3
```

Then apply any pending migrations:

```bash
# On the server (virtualenv activated)
cd ~/ideas_block/git
python manage.py migrate --settings=ideas_block.settings.cpanel
```

---

### Step 7 — Collect static files

```bash
# On the server (virtualenv activated)
cd ~/ideas_block/git
python manage.py collectstatic --noinput --settings=ideas_block.settings.cpanel
```

This writes all static files to `~/ideas_block/git/static/`. WhiteNoise serves them via Passenger — no `public_html` step needed.

---

### Step 8 — Upload media files

```bash
# From your local machine — initial upload (~6.5 GB, run once)
rsync -avz --progress \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/ \
  <username>@<server>:~/ideas_block/git/media/

# Subsequent syncs — only new/changed files
rsync -avz --update --checksum \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/ \
  <username>@<server>:~/ideas_block/git/media/
```

> **Bandwidth tip:** Skip the `images/` renditions folder (3.3 GB) — Wagtail regenerates them on demand:
> ```bash
> rsync -avz media/original_images/ <username>@<server>:~/ideas_block/git/media/original_images/
> rsync -avz media/documents/       <username>@<server>:~/ideas_block/git/media/documents/
> ```

---

### Step 9 — Restart the app

cPanel → **Setup Python App** → click **Restart**. Or via SSH:

```bash
touch ~/ideas_block/tmp/restart.txt   # Passenger watches this file
```

The site should now be live at `https://ideas-block.com`.

---

### Step 10 — Enable SSL

cPanel → **Security** → **SSL/TLS** → **AutoSSL** → run for your domain. Free, automatic, renews itself.

---

### Updating after code changes

```bash
# On the server (via SSH)
cd ~/ideas_block/git
git pull

source /home/<username>/virtualenv/ideas_block/3.12/bin/activate
pip install -r requirements.txt                                          # if dependencies changed
python manage.py migrate --settings=ideas_block.settings.cpanel          # if models changed
python manage.py collectstatic --noinput --settings=ideas_block.settings.cpanel

# If passenger_wsgi.py changed in the repo, copy it to the app root again
cp ~/ideas_block/git/passenger_wsgi.py ~/ideas_block/passenger_wsgi.py

touch ~/ideas_block/tmp/restart.txt                                      # reload Passenger
```

---

### Troubleshooting

| Problem | Fix |
|---|---|
| 500 error on all pages | Check `~/logs/` or cPanel → **Errors** for the Passenger traceback |
| `SECRET_KEY` not found | Confirm `.env` is at `~/ideas_block/.env` (not inside `git/`) |
| Static files 404 | Confirm `collectstatic` ran and `~/ideas_block/git/static/` exists |
| Media files 404 | Confirm rsync completed and `~/ideas_block/git/media/` exists |
| `ModuleNotFoundError` | Confirm virtualenv is activated and `pip install -r requirements.txt` ran |
| App won't restart | Passenger can take 30–60 s; hard-restart via cPanel Setup Python App |

---

## Deployment — Docker / Containers

### Files needed (add to repo root)

**`Dockerfile`:**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=ideas_block.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

COPY new_website/ .

RUN python manage.py collectstatic --no-input

EXPOSE 8000
CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:8000", "ideas_block.wsgi:application"]
```

**`docker-compose.yml`:**

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file: .env

  web:
    build: .
    restart: always
    depends_on:
      - db
    volumes:
      - media_files:/app/media
    env_file: .env
    ports:
      - "8000:8000"

  nginx:
    image: nginx:alpine
    restart: always
    depends_on:
      - web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - media_files:/media:ro
      - static_files:/static:ro
      - certbot_certs:/etc/letsencrypt:ro

volumes:
  postgres_data:
  media_files:
  static_files:
```

### Deploy with Docker

```bash
# On the server
git clone <repo-url> ideas_block
cd ideas_block
cp .env.example .env   # fill in production values

docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py setup_pages
docker compose exec web python manage.py createsuperuser

# Sync media from local machine
rsync -avz ./new_website/media/ user@server:/srv/ideas_block/media_volume/
```

---

## What Is Not in Git — and How to Transfer It

Two things are excluded from version control and must be transferred manually on every fresh deployment: the **database** and the **media files**.

### Database (`db.sqlite3`) — ~12 MB

The SQLite database contains everything: all 276 blog posts, 154 events, all project pages, past open calls, press entries, publications, members, tickets, site settings, and every Wagtail page relationship. The code is useless without it.

**It is never committed to git.** Transfer it using one of the two methods below.

#### Option A — Keep SQLite in production (simplest, low-traffic)

If you are deploying to a single server and traffic is modest, you can run production on SQLite too. Just copy the file:

```bash
# From your local machine to the server
scp new_website/db.sqlite3 user@your-server:/srv/ideas_block/new_website/db.sqlite3
```

Change `production.py` to use SQLite by adding this override to `.env` / `local.py` on the server:

```python
# ideas_block/settings/local.py on the server
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

Make sure the file is writable by the web process (`chown www-data`) and that it lives on a persistent volume (not inside a Docker container's writable layer).

#### Option B — Migrate to PostgreSQL (recommended for production)

The production settings already configure PostgreSQL. To migrate the content from the local SQLite database:

**Step 1 — Export from SQLite on your local machine:**

```bash
cd new_website
source venv/bin/activate

python manage.py dumpdata \
  --natural-foreign \
  --natural-primary \
  --exclude contenttypes \
  --exclude auth.permission \
  --indent 2 \
  > full_export.json
```

This produces a ~10–30 MB JSON file with all content.

**Step 2 — On the server, create the PostgreSQL database and run migrations:**

```bash
sudo -u postgres psql -c "CREATE DATABASE ideas_block;"
sudo -u postgres psql -c "CREATE USER ideas_block_user WITH PASSWORD 'yourpassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ideas_block TO ideas_block_user;"

cd /srv/ideas_block/new_website
source venv/bin/activate
python manage.py migrate --settings=ideas_block.settings.production
```

**Step 3 — Transfer and load the export:**

```bash
# Copy the export to the server
scp full_export.json user@your-server:/srv/ideas_block/new_website/

# On the server, load it
python manage.py loaddata full_export.json --settings=ideas_block.settings.production
```

> **Note:** `loaddata` must run against an already-migrated database. Always run `migrate` before `loaddata`.

**Step 4 — Verify:**

```bash
python manage.py shell --settings=ideas_block.settings.production -c "
from blog.models import BlogPostPage
from wagtail.models import Page
print('Pages:', Page.objects.count())
print('Blog posts:', BlogPostPage.objects.count())
"
```

---

### Media Files (`media/`) — ~6.5 GB, 5,181 files

The media directory holds all user-uploaded images and documents managed through the Wagtail admin. It is never committed to git.

```
media/
├── images/          # Wagtail-resized image renditions (~3.3 GB)
├── original_images/ # Source uploads as uploaded (~3 GB)
├── documents/       # PDFs, downloads, press kits
└── tickets/         # Generated QR ticket PDFs
```

**First upload (from local dev machine to server):**

```bash
rsync -avz --progress \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/ \
  user@your-server:/srv/ideas_block/media/
```

This will take a while over a standard connection (6.5 GB). Run it overnight or from a machine on a fast connection.

**Subsequent syncs — only transfer new/changed files:**

```bash
rsync -avz --update --checksum \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/ \
  user@your-server:/srv/ideas_block/media/
```

**Pull from server back to local (if editors have uploaded via the admin):**

```bash
rsync -avz --update \
  user@your-server:/srv/ideas_block/media/ \
  /Users/selves/Documents/ROBERTO/WORKS/DEVELOPMENT/IDEAS-BLOCK/new_website/media/
```

> **Tip — skip renditions:** The `images/` subdirectory contains Wagtail-generated renditions (resized thumbnails). These are reproducible — Wagtail regenerates them on demand. If bandwidth is tight, you can rsync only `original_images/` and `documents/` and let renditions rebuild:
>
> ```bash
> rsync -avz media/original_images/ user@server:/srv/ideas_block/media/original_images/
> rsync -avz media/documents/ user@server:/srv/ideas_block/media/documents/
> ```

---

## Git Strategy — What Is and Isn't Tracked

### Tracked in git ✓
- All Python source code (`*.py`)
- All Django templates (`templates/`)
- Source CSS (`ideas_block/static/css/main.css`)
- Wagtail migrations (`*/migrations/*.py`)
- Requirements (`requirements.txt`)
- This README

### NOT tracked in git ✗

| Item | Size | Why | How to handle |
|---|---|---|---|
| `media/` | ~6.5 GB, 5,181 files | User uploads, binary | `rsync` to server — see section above |
| `static/` (top-level) | Generated | Output of `collectstatic` | Run `collectstatic` on server after each deploy |
| `db.sqlite3` | ~12 MB | All content, binary | Transfer via `dumpdata`/`loaddata` or `scp` — see section above |
| `.env` / `local.py` | — | Secrets | Copy manually; never commit |
| `venv/` | — | Python packages | `pip install -r requirements.txt` |

---

## Updating the Site

### Code changes

```bash
# On server
cd /srv/ideas_block
git pull
source new_website/venv/bin/activate
cd new_website
pip install -r requirements.txt       # if dependencies changed
python manage.py migrate              # if models changed
python manage.py collectstatic --no-input
sudo systemctl restart ideas_block
```

### Content changes

Everything editorial (posts, events, pages) is managed entirely in the Wagtail admin at `/admin/`. No code deploy needed.

---

## Key Management Commands

```bash
# Set up required Wagtail pages (safe to re-run)
python manage.py setup_pages

# Change admin password
python manage.py changepassword admin

# Import WordPress content from SQL dump
python manage.py import_wordpress --sql-path=../iopaveqd_wp290_20260328.sql

# Import media from WordPress uploads directory
python manage.py import_media --sql-path=../iopaveqd_wp290_20260328.sql \
  --uploads-dir=../ideas-block.com/wp-content/uploads

# Create structural pages from WordPress content
python manage.py create_site_pages --sql-path=../iopaveqd_wp290_20260328.sql

# Create a DB backup
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.permission --indent 2 > backup.json

# Restore DB backup
python manage.py loaddata backup.json
```

---

## Environment Variables Reference

All configuration is driven by a `.env` file in the project root. Copy `.env.example` to `.env` and fill in the blanks.

```bash
cp .env.example .env
```

`.env` is git-ignored and must never be committed. `.env.example` is committed and kept up to date.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | ✓ | — | `ideas_block.settings.dev` locally, `ideas_block.settings.production` on server |
| `DJANGO_SECRET_KEY` | ✓ prod | — | Random string — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `ALLOWED_HOSTS` | ✓ prod | `ideas-block.com,...` | Comma-separated domain list |
| `SITE_URL` | ✓ prod | `https://ideas-block.com` | Full URL used in Wagtail admin notification emails |
| `DB_NAME` | prod | `ideas_block` | PostgreSQL database name |
| `DB_USER` | prod | `ideas_block_user` | PostgreSQL user |
| `DB_PASSWORD` | prod | — | PostgreSQL password |
| `DB_HOST` | prod | `localhost` | PostgreSQL host |
| `DB_PORT` | prod | `5432` | PostgreSQL port |
| `EMAIL_HOST` | prod | — | SMTP server hostname (e.g. `smtp.gmail.com`) |
| `EMAIL_PORT` | prod | `587` | SMTP port |
| `EMAIL_HOST_USER` | prod | — | SMTP login |
| `EMAIL_HOST_PASSWORD` | prod | — | SMTP password or app password |
| `DEFAULT_FROM_EMAIL` | prod | `noreply@ideas-block.com` | From address on outbound emails |
| `TICKETS_BCC_EMAIL` | — | `contact@ideas-block.com` | BCC address on all ticket confirmation emails |
| `STRIPE_PUBLISHABLE_KEY` | tickets | — | `pk_test_…` in dev, `pk_live_…` in prod |
| `STRIPE_SECRET_KEY` | tickets | — | `sk_test_…` in dev, `sk_live_…` in prod |
| `STRIPE_WEBHOOK_SECRET` | tickets | — | `whsec_…` — from Stripe Dashboard > Webhooks |
| `STRIPE_PRICE_SUPPORTER` | subscriptions | — | Stripe Price ID for €5/mo Supporter plan |
| `STRIPE_PRICE_PATRON` | subscriptions | — | Stripe Price ID for €15/mo Patron plan |
| `MAILERLITE_API_KEY` | newsletter | _(blank)_ | MailerLite API v2 token — leave blank to disable |
| `PLAUSIBLE_DOMAIN` | analytics | _(blank)_ | e.g. `ideas-block.com` — leave blank to disable |
| `MEMBER_DISCOUNT_EUR` | — | `2.00` | EUR discount applied to ticket price for active members |

---

## Licence

All code is proprietary. Content and media are © Ideas Block (VšĮ Idėjų blokas LT).
