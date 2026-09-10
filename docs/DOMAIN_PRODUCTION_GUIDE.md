# Production Domain Configuration Guide: jasuss.tech

This guide details the complete configuration required to launch **JASUSS** on your custom domain: **`jasuss.tech`**.

---

## 1. DNS Records Setup (At Your Domain Registrar / DNS Host)

Point your domain DNS records to your hosting infrastructure:

### Option A: Render Deployment (Using [`render.yaml`](file:///home/devxgamer/ai-qa-agent/render.yaml))
In the Render dashboard under your services:

| Hostname / Record | Type | Target / Value | Notes |
| :--- | :--- | :--- | :--- |
| `@` (`jasuss.tech`) | **ANAME / ALIAS** (or **A**) | Points to Render Web Service (`ai-qa-web.onrender.com` or IP provided) | Apex domain for frontend |
| `www` (`www.jasuss.tech`) | **CNAME** | Points to `ai-qa-web.onrender.com` | Aliased or redirected to apex |
| `api` (`api.jasuss.tech`) | **CNAME** | Points to `ai-qa-api.onrender.com` | Dedicated API backend endpoint |

### Option B: Vercel (Frontend) + Render (Backend/Worker)
| Hostname / Record | Type | Target / Value | Notes |
| :--- | :--- | :--- | :--- |
| `@` (`jasuss.tech`) | **A** | `76.76.21.21` (Vercel Apex) | Frontend on Vercel |
| `www` (`www.jasuss.tech`) | **CNAME** | `cname.vercel-dns.com` | Redirects to apex |
| `api` (`api.jasuss.tech`) | **CNAME** | Points to Render API (`ai-qa-api.onrender.com`) | Backend on Render |

---

## 2. Supabase Authentication Registration & Redirect Whitelist

To allow user logins and social sign-in on `jasuss.tech`, Supabase's authentication service (GoTrue) requires explicit registration of all callback destinations.

> [!WARNING]
> **Silent Fallback Trap**: If a requested `redirectTo` is not in Supabase's Allowed Redirect URLs, Supabase will **silently discard it** and redirect the user's browser to the configured **Site URL** (`http://localhost:3000`). In production, this causes an immediate `localhost refused to connect` (`ERR_CONNECTION_REFUSED`) error.

### Required Supabase Settings:
1. Open **[Supabase Dashboard ➔ Authentication ➔ URL Configuration](https://supabase.com/dashboard/project/xsrcksdtiymswfrlkhtf/auth/url-configuration)**:
2. Set **Site URL**:
   ```
   https://www.jasuss.tech
   ```
3. In **Redirect URLs (Allowed Callback URLs)**, add the following wildcard patterns:
   ```
   https://www.jasuss.tech/**
   https://www.jasuss.tech/auth/callback
   https://jasuss.tech/**
   https://jasuss.tech/auth/callback
   https://web-two-flame-39.vercel.app/**
   https://web-two-flame-39.vercel.app/auth/callback
   http://localhost:3000/**
   http://localhost:3000/auth/callback
   ```
4. Click **Save Changes**.

> [!NOTE]
> **Security Trade-Off Notice (Localhost in Production Allowlist)**:
> Having `http://localhost:3000/**` in the production Supabase project's redirect allowlist is kept for local developer convenience during this phase. In a subsequent security hardening pass, local development should be separated into a dedicated staging/dev Supabase project so the production project only permits valid production and staging HTTPS origins.

---

## 3. Google Cloud Console OAuth Configuration

To ensure Google Sign-In succeeds without `redirect_uri_mismatch` or `origin_not_allowed`:

1. Open **[Google Cloud Console ➔ APIs & Services ➔ Credentials](https://console.cloud.google.com/apis/credentials)**.
2. Select your OAuth 2.0 Web Client (`448372595682-f5833ulhlt7tjv35tkf5it8ofvm7uees.apps.googleusercontent.com`).
3. Under **Authorized JavaScript origins**, add:
   ```
   https://www.jasuss.tech
   https://jasuss.tech
   https://web-two-flame-39.vercel.app
   https://xsrcksdtiymswfrlkhtf.supabase.co
   http://localhost:3000
   ```
4. Under **Authorized redirect URIs**, add Supabase's auth proxy callback:
   ```
   https://xsrcksdtiymswfrlkhtf.supabase.co/auth/v1/callback
   ```
5. Click **Save**.

---

## 4. Automated Verification Script

To verify that your Supabase credentials, Google OAuth provider status, and OAuth redirects are configured correctly without needing manual browser clicks:

```bash
# Run the automated auth and domain verifier:
python3 scripts/verify_auth_config.py
```

**Known Supabase API Limitation:** GoTrue's `/auth/v1/settings` endpoint intentionally does not expose `site_url` or `uri_allow_list` to project API keys (service role or anon) to prevent cross-origin reconnaissance. The verifier validates live OAuth `302` handshake responses from Supabase to verify parameter preservation.

---

## 5. Environment Variables Checklist

### Backend & Celery Worker (`.env.production` / Cloud Dashboard):
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://jasuss.tech,https://www.jasuss.tech,https://api.jasuss.tech
DATABASE_URL=postgresql://... (Managed Postgres)
REDIS_URL=rediss://... (Managed Redis)
GEMINI_API_KEY=your_gemini_api_key
NEXT_PUBLIC_SUPABASE_URL=https://xsrcksdtiymswfrlkhtf.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

### Next.js Frontend (`web/.env.production` / Cloud Dashboard):
```bash
NEXT_PUBLIC_APP_URL=https://jasuss.tech
API_URL=https://api.jasuss.tech
NEXT_PUBLIC_API_URL=https://api.jasuss.tech
NEXT_PUBLIC_SUPABASE_URL=https://xsrcksdtiymswfrlkhtf.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_GOOGLE_CLIENT_ID=448372595682-f5833ulhlt7tjv35tkf5it8ofvm7uees.apps.googleusercontent.com
```

---

## 6. Security & Verification Rules
- **SSL/TLS**: All traffic must terminate with HTTPS (`https://jasuss.tech`). Let's Encrypt certificates are automatically generated by Render/Vercel once DNS records propagate.
- **CORS**: Verified in [`api/main.py`](file:///home/devxgamer/ai-qa-agent/api/main.py) to accept credentials and requests originating from `https://jasuss.tech`.
- **Worker Isolation**: The Celery worker runs in its own container with headless Chromium, fully detached from the web frontend.
