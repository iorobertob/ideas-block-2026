# Ideas Block — Website

The official website of **Ideas Block** (VšĮ Idėjų blokas LT), a cultural non-profit organisation based in Vilnius, Lithuania, active since 2014.

---

## Concept

Ideas Block is an independent cultural organisation that produces exhibitions, residencies, workshops, publications, and events. The website serves two simultaneous roles:

1. **Living platform** — editorial blog, upcoming events, open calls, publications, supporter portal
2. **10-year archive** — 246 blog posts, 136 events, and years of cultural production, fully searchable and publicly accessible

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
    │   └── BlogPostPage                       /blog/slug/
    ├── Events (EventsIndexPage)               /events/
    │   └── EventPage                          /events/slug/
    ├── Projects (ProjectsIndexPage)           /projects/
    │   └── ProjectPage                        /projects/slug/
    ├── Shop (ProductsIndexPage)               /shop/
    │   └── ProductPage                        /shop/slug/
    ├── People (PeoplePage)                    /people/
    │   └── PersonPage                         /people/slug/
    ├── Open Calls (OpenCallsIndexPage)        /open-calls/
    │   └── OpenCallPage                       /open-calls/slug/
    ├── Publications (PublicationsIndexPage)   /publications/
    │   └── PublicationPage                    /publications/slug/
    ├── Press (PressPage)                      /press/
    ├── About (AboutPage)                      /about/
    ├── Space (SpacePage)                      /space/
    ├── Contact (ContactPage)                  /contact/
    └── Documents (RichPage)                   /documents/
```

### Apps

| App | Purpose |
|---|---|
| `home` | HomePage — hero, featured content, context for homepage sections |
| `blog` | BlogIndexPage, BlogPostPage — full archive, tags, categories, language filter |
| `events` | EventsIndexPage, EventPage — upcoming/past split, Stripe tickets, year filter |
| `projects` | ProjectsIndexPage, ProjectPage — exhibitions, residencies, curated projects |
| `products` | ProductsIndexPage, ProductPage — shop items, Stripe checkout |
| `people` | PeoplePage, PersonPage — team portraits, bios, Instagram, related posts |
| `opencalls` | OpenCallsIndexPage, OpenCallPage — residency/commission calls, deadlines, apply CTA |
| `publications` | PublicationsIndexPage, PublicationPage — books, catalogues, ISBN, buy/download |
| `press` | PressPage — press contact, downloadable kits, press images, coverage log |
| `core` | ContactPage, SpacePage, AboutPage, RichPage — shared pages and utilities |
| `tickets` | Stripe checkout, webhook, QR ticket generation, door scanner, subscriptions |
| `members` | Django auth accounts linked to Stripe subscriptions, dashboard |
| `search` | Site-wide search with type filters and result counts |

### Non-Wagtail URLs

| URL | View / purpose |
|---|---|
| `/search/` | Full-text search across all page types |
| `/tickets/checkout/<id>/` | Stripe Checkout for events/products |
| `/tickets/support/` | Supporter subscription page |
| `/tickets/scanner/` | Staff QR scanner (requires login) |
| `/tickets/webhook/stripe/` | Stripe webhook receiver |
| `/members/login/` | Sign in |
| `/members/register/` | Create account |
| `/members/dashboard/` | Account + order history |
| `/core/newsletter/signup/` | MailerLite AJAX endpoint |
| `/i18n/set_language/` | Django language switcher (POST) |
| `/api/v2/` | Wagtail headless API (pages, images, docs) |
| `/sitemap.xml` | Sitemap for all live Wagtail pages |
| `/blog/feed/` | RSS feed for blog posts |
| `/events/feed/` | RSS feed for upcoming events |
| `/admin/` | Wagtail CMS admin |

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

Create `ideas_block/settings/local.py` (git-ignored):

```python
# ideas_block/settings/local.py
STRIPE_PUBLISHABLE_KEY = "pk_test_..."
STRIPE_SECRET_KEY = "sk_test_..."
STRIPE_WEBHOOK_SECRET = "whsec_..."
STRIPE_PRICE_SUPPORTER = "price_..."
STRIPE_PRICE_PATRON = "price_..."
MAILERLITE_API_KEY = ""          # leave blank in dev
PLAUSIBLE_DOMAIN = ""            # leave blank in dev
```

Or use a `.env` file with `python-dotenv` (already installed).

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
sudo -u postgres psql
CREATE DATABASE ideas_block;
CREATE USER ideas_block_user WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE ideas_block TO ideas_block_user;
\q
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

Create `/srv/ideas_block/new_website/.env`:

```env
DJANGO_SETTINGS_MODULE=ideas_block.settings.production
SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DATABASE_URL=postgres://ideas_block_user:password@localhost/ideas_block
ALLOWED_HOSTS=ideas-block.com,www.ideas-block.com
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_SUPPORTER=price_...
STRIPE_PRICE_PATRON=price_...
MAILERLITE_API_KEY=...
PLAUSIBLE_DOMAIN=ideas-block.com
WAGTAILADMIN_BASE_URL=https://ideas-block.com
```

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

## Git Strategy — What Is and Isn't Tracked

### Tracked in git ✓
- All Python source code (`*.py`)
- All Django templates (`templates/`)
- Source CSS (`ideas_block/static/css/main.css`)
- Wagtail migrations (`*/migrations/*.py`)
- Requirements (`requirements.txt`)
- This README

### NOT tracked in git ✗

| Item | Why | How to handle |
|---|---|---|
| `media/` | User uploads, 1–10 GB, binary | `rsync` to server; or use object storage |
| `static/` (top-level) | Generated by `collectstatic` | Run on server after deploy |
| `db.sqlite3` | Dev database, binary | Transfer with `pg_dump` for production |
| `.env` / `local.py` | Secrets | Copy manually or use secret manager |
| `venv/` | Python packages | `pip install -r requirements.txt` |

### Workflow for media

```bash
# After adding images in dev, push to server:
rsync -avz --checksum new_website/media/ user@server:/srv/ideas_block/media/

# Pull server media to local dev (if editors uploaded via admin):
rsync -avz user@server:/srv/ideas_block/media/ new_website/media/
```

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
python manage.py migrate_from_wordpress --sql-path=../backup.sql

# Create a DB backup
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.permission --indent 2 > backup.json

# Restore DB backup
python manage.py loaddata backup.json
```

---

## Environment Variables Reference

| Variable | Required in prod | Description |
|---|---|---|
| `SECRET_KEY` | ✓ | Django secret key — generate a fresh one |
| `ALLOWED_HOSTS` | ✓ | Comma-separated domains |
| `DATABASE_URL` | ✓ | PostgreSQL connection string |
| `STRIPE_PUBLISHABLE_KEY` | For tickets | Stripe publishable key |
| `STRIPE_SECRET_KEY` | For tickets | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | For tickets | Stripe webhook signing secret |
| `STRIPE_PRICE_SUPPORTER` | For subscriptions | Stripe Price ID for €5/mo plan |
| `STRIPE_PRICE_PATRON` | For subscriptions | Stripe Price ID for €15/mo plan |
| `MAILERLITE_API_KEY` | For newsletter | MailerLite API v2 token |
| `PLAUSIBLE_DOMAIN` | For analytics | e.g. `ideas-block.com` |
| `WAGTAILADMIN_BASE_URL` | For emails | e.g. `https://ideas-block.com` |

---

## Licence

All code is proprietary. Content and media are © Ideas Block (VšĮ Idėjų blokas LT).
