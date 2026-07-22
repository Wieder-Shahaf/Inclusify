# Inclusify — Infrastructure & Code Handover Runbook

Step-by-step guide to hand **full ownership** of Inclusify (code + all live
infrastructure + billing) from Shahaf Wieder to the Achva organization
(point of contact: **Offek**).

> This is a click-by-click runbook. UI labels were verified against the
> platforms' official docs in July 2026. If a button label has since changed,
> the surrounding step still describes what you are looking for.

---

## 0. The one thing to understand before you start

Every platform separates **two** things that people assume are one:

| | What it gives Achva | How it moves |
|---|---|---|
| **Ownership** (role) | Control: deploy, change secrets, manage members | Transfer the owner/admin role |
| **Billing** (payment method) | Who pays | A **separate** step — replace the credit card |

**Transferring ownership does NOT move the credit card.** On Modal and
Cloudflare the old card stays attached until someone explicitly replaces it —
so if you skip the billing step, *Shahaf keeps getting charged even though
Offek is now the owner.*

### The success test (how you know the handover is truly done)

> ✅ Shahaf's payment method is removed from **all** platforms, **and**
> ✅ Offek can ship a change end-to-end (git push → deploy → live) **without**
> Shahaf's account being involved anywhere.

Anything short of both is a partial handover.

---

## 1. What Offek needs ready before the cutover

- A **GitHub account** (his own or an Achva one).
- A **payment method** (card) ready to add on **each** platform. Railway will
  not even accept the project transfer into an unpaid workspace.
- The **email addresses** he wants to own each account with. Prefer a shared
  Achva address (e.g. an `@achva.ac.il` alias or a shared ops mailbox) over a
  personal one, so the accounts survive Offek leaving.

---

## 2. Order of operations (do this in sequence)

The order is chosen so **production never goes down** during the handover. It
works because transferring (rather than recreating) keeps the identifiers that
Railway points at (`VLLM_URL`, `S3_ENDPOINT_URL`) unchanged.

```
1. GitHub        → transfer repo to an Achva-owned Org       (source of all deploys)
2. Cloudflare R2 → transfer Super Administrator of the account (keeps S3_* creds valid)
3. Modal         → transfer Owner of the existing workspace   (keeps VLLM_URL unchanged)
4. Google + Resend → transfer or reissue OAuth + email        (the hidden accounts)
5. Railway       → transfer the whole project to Offek's workspace (backend+frontend+Postgres+env)
6. VERIFY        → full end-to-end smoke test
7. DECOMMISSION  → remove Shahaf's cards + access everywhere   (the success test)
```

### Why this order

- **Railway is the hub.** Its env vars point at Modal, R2, Google, Resend and
  its own Postgres. Move the things it points at *first* (keeping their
  identifiers stable), then move Railway last, then verify.
- **Postgres travels inside the Railway project** — transferring the project
  carries the database *and its data* (users, saved analyses). No DB migration.
- Do **not** delete anything of Shahaf's until step 6 passes. Keep a rollback.

---

## 3. Platform 1 — GitHub (the code)

**Goal:** the repo lives in an Achva-owned Organization, not on Shahaf's
personal account. (A "collaborator" is *not* an owner — skip that idea.)

### 3A. Ownership

**First, create the org (Offek, or Shahaf on Offek's behalf):**
1. Go to https://github.com → top-right **+** → **New organization**.
2. Choose the **Free** plan (fine for this project).
3. Name it (e.g. `achva-inclusify`) and set the billing email to the Achva address.
4. Add Offek as an **Owner** of the org (Org → **People** → **Invite member** → role **Owner**).

**Then, transfer the repo (Shahaf, as current repo owner):**
1. Open the repo → **Settings** tab.
2. Scroll to the bottom → **Danger Zone**.
3. Click **Transfer**.
4. Choose **Select one of my organizations** and pick the Achva org
   (or **Specify an organization or username** and type it).
5. Type the repository name to confirm.
6. Click **I understand, transfer this repository**.

**What transfers automatically:** issues, pull requests, wiki, stars, watchers,
webhooks, deploy keys, and **URL redirects** from the old path (old links keep
working).

### 3B. Billing

Nothing to pay. A public repo is free; a private repo on the Free org plan is
also free (Actions has free minutes, then paid — this project's CI is light).
Just make sure the org's billing email is the Achva address, not Shahaf's.

### 3C. Verify

- [ ] Repo appears under `github.com/<achva-org>/inclusify`.
- [ ] Offek (Org Owner) can see **Settings → Danger Zone** on the repo.
- [ ] An old repo URL redirects to the new location.
- [ ] Leave Shahaf as a member for now (removed in step 7).

---

## 4. Platform 2 — Cloudflare R2 (document / report storage)

**Goal:** Achva owns the Cloudflare **account** (the R2 buckets live inside it).
Transferring the account keeps the buckets, objects, **and** the R2 API tokens —
so `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` in Railway stay
valid and prod keeps working. **Do not** create a fresh account unless you
accept a data migration (see alt at the end).

### 4A. Ownership (transfer Super Administrator)

**Shahaf (current Super Administrator):**
1. Cloudflare dashboard → **Manage Account** → **Members**.
2. Click **Invite**.
3. Enter Offek's email; under **Roles** assign **Super Administrator**
   (Administrator - All Privileges).
4. **Continue to summary** → **Invite**.

**Offek:** accept the email invitation and log in.

Removing Shahaf happens in step 7 (Members → expand Shahaf's row → **Revoke** →
**Yes, revoke access**), *after* Offek confirms he has full access.

### 4B. Billing

**Offek (now Super Administrator):**
1. **Manage Account** → **Billing** → **Payment**.
2. **Add Payment Method** (his card), then set it as the account's method.
3. Remove Shahaf's old card once the new one is active (a card can't be deleted
   while a payment is failing or a balance is outstanding).

### 4C. Verify

- [ ] Offek is **Super Administrator** on the account.
- [ ] R2 → the existing bucket(s) are visible with their objects.
- [ ] R2 API tokens still listed (R2 → **Account Details** → **Manage** next to
      **API Tokens**) — these are **account-level** tokens and remain valid.
- [ ] Offek's card is the account payment method; Shahaf's is removed.
- [ ] `S3_*` env vars in Railway are **unchanged** (they should be — same account).

> **Alternative (only if Achva insists on a brand-new Cloudflare account):**
> Offek creates his own account → create a new R2 bucket → migrate objects with
> Cloudflare **Super Slurper** or `rclone` → create new R2 API tokens →
> **update `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`,
> `S3_BUCKET` in Railway**. More work and a brief data-sync window — avoid
> unless required.

---

## 5. Platform 3 — Modal (GPU / LLM inference)

**Goal:** Achva owns the Modal **workspace**. Owner-swapping the *existing*
workspace keeps its name — so `VLLM_URL`
(`https://<workspace>--inclusify-vllm-serve.modal.run`) and the
`inclusify-vllm-key` secret are unchanged, and Railway needs no edits.

### 5A. Ownership (make Offek Owner of the existing workspace)

**Shahaf (current Owner):**
1. Modal dashboard → sidebar, under the workspace name (e.g. `wieder-shahaf`) →
   **Workspace Management**. (There is **no** separate "Members" tab — invites
   and roles both live here. Do not confuse it with the top **Account** group,
   which is your personal login.)
2. Send Offek an **email invite** (or share the invite link) from this page.

**Offek:** accept and join the workspace.

**Shahaf:** back on **Workspace Management**, set Offek's role to **Owner**.
(Do not leave the workspace yet — that happens in step 7, and only after a new
Owner exists.)

**Offek — point his CLI at this workspace so he can deploy:**
```bash
modal token new              # authenticate the CLI (creates a token for this workspace)
modal profile activate <workspace>   # if he has more than one workspace
modal deploy infra/modal/vllm_app.py # redeploy from the Achva-owned repo checkout
```

### 5B. Billing

**Offek (as Owner):**
1. Sidebar, under the workspace name → **Usage & Billing** → **Manage payment details**.
2. On the **Stripe-hosted page**, set his **payment method** and **billing email**.
3. Confirm Shahaf's card is no longer the method on file.

### 5C. Verify

- [ ] Offek is **Owner** in Workspace Management.
- [ ] `modal deploy infra/modal/vllm_app.py` succeeds from his machine.
- [ ] Endpoint responds: `curl https://<workspace>--inclusify-vllm-serve.modal.run/health`
      (or run `backend/tests/test_vllm_integration.py` against it).
- [ ] Offek's card + billing email are on the Stripe page; Shahaf's removed.
- [ ] `VLLM_URL` / `VLLM_API_KEY` in Railway are **unchanged**.

> **Alternative (fresh workspace under Offek):** create a new workspace → set
> billing → recreate the secret with
> `modal secret create inclusify-vllm-key VLLM_API_KEY=<key>` → `modal deploy`.
> The workspace name changes, so **update `VLLM_URL` (and `VLLM_API_KEY` if you
> regenerated the key) in Railway**. Cleaner billing identity, but requires the
> Railway edit and a brief LLM downtime.

---

## 6. Platform 4 — The two hidden accounts (Google OAuth + Resend)

These aren't Railway/Modal/R2, but Google login and contact-form email depend
on them, and they're currently tied to Shahaf. Skipping them leaves the app
half-owned.

### 6A. Google OAuth — `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`

Google login is driven by an **OAuth 2.0 client** that lives inside a **Google
Cloud project**. We **transfer the project** (add Offek as Owner) rather than
reissue the client — that keeps the same client ID/secret, so **no Railway
change** and **no login downtime**.

> **Console layout note:** this project (`Inclusify-Web`) uses the **classic**
> layout — the left sidebar has a **Credentials** page and a separate
> **OAuth consent screen** item. (Newer projects instead show
> **APIs & Services → Google Auth Platform** with **Branding / Audience /
> Clients** tabs; if Google migrates this project later, the fields map 1:1.)

#### Ownership (transfer the project)

**Step 1 — Confirm the project (Shahaf) — already identified.**
The project is **`Inclusify-Web`** (project number **865751097580**). This is
confirmed correct because the OAuth client ID in Railway
(`GOOGLE_CLIENT_ID = 865751097580-ra6r….apps.googleusercontent.com`) starts with
that same project number. To re-check: top-bar **project picker** → `Inclusify-Web`,
then **APIs & Services → Credentials → OAuth 2.0 Client IDs** → the client named
**`Inclusify`** (Web application).

> ⚠️ There is a **warning icon** on the `Inclusify` client. Before handover,
> click the client name and resolve it (usually an unverified app or a
> redirect-URI mismatch) — don't hand Offek a pre-flagged client.

**Step 2 — Add Offek as Owner (Shahaf).**
1. Console → **IAM & Admin → IAM**.
2. Click **GRANT ACCESS** (top of the page).
3. **New principals** → enter Offek's Google account email.
4. **Assign roles** → Role → **Basic → Owner**.
5. Click **SAVE**. Google sends Offek an **invitation** to the project.
   *(You must use the console — not the `gcloud` CLI — to grant Owner to someone
   outside your organization. That applies here, since the project sits under a
   personal Gmail with no organization.)*

**Step 3 — Offek accepts.**
Offek opens the invitation email and accepts, then confirms he can open the
project and see himself listed as **Owner** under **IAM & Admin → IAM**.

**Step 4 — Move the consent-screen contact details to Achva (Offek or Shahaf).**
Console → **APIs & Services → OAuth consent screen** (opens the **Branding**
page in this console):
- **User support email** → currently `inclusify.support@gmail.com`. This is a
  *shared* address (not Shahaf's personal), and it's also the Resend sender
  (§6B). For a clean handover, **hand Achva the `inclusify.support@gmail.com`
  Google account itself** (solves Google login contact + Resend in one), or
  change this field to an Achva-controlled address.
- **Developer contact information** (bottom of the Branding page) → an Achva address.

> **Credentials delivery — do NOT paste passwords into this repo.** The
> `inclusify.support@gmail.com` login is a live shared credential that also
> controls Resend (§6B) and the domain contact. Deliver it to Offek **out of
> band** — a shared password-manager vault (1Password / Bitwarden) or a direct
> secure message — **never** in this git-tracked file (repo history is permanent
> and the repo is being transferred to Achva). On receipt, Offek should
> **change the password** and set his own recovery so the old shared password
> stops mattering.

**Step 4b — Check the publishing status (IMPORTANT).**
Console → **APIs & Services → OAuth consent screen → Audience** page. If the app
is in **Testing** status:
- Only **explicitly-added test users** can log in via Google (max 100), and
  refresh tokens **expire every 7 days** — a new Achva user's login will simply fail.
- For a live service, click **Publish app** to move it to **In production**.
  With only basic email/profile scopes this usually needs **no formal
  verification** (the app currently shows "Verification is not required").
- This is Offek's decision to make consciously — don't leave it in Testing by
  default and let it surface as an outage later.

**Step 5 — Shahaf removes himself (later — part of the §10 decommission).**
Only after Offek confirms Owner access **and** login still works on the live app:
Console → **IAM & Admin → IAM** → find Shahaf's row → **Edit principal (pencil)**
→ remove the **Owner** role → **SAVE**. A project must always keep at least one
Owner, so this only succeeds once Offek is Owner.

#### Billing

Google Sign-In (Google Identity) is **free** — this project almost certainly has
**no billing account**, so there is nothing to move here. Verify anyway: open
the console **Billing** page. If a billing account *is* linked (the project uses
paid Google APIs), note that **billing accounts have separate ownership** and
must be transferred on their own (**Billing → Account Management →** add Offek as
a **Billing Account Administrator**). For pure OAuth login, expect none.

#### Verify

- [ ] Offek is **Owner** in **IAM & Admin → IAM**.
- [ ] **APIs & Services → Credentials → OAuth 2.0 Client IDs** shows the `Inclusify`
      client with the **same** client ID (`865751097580-ra6r…`) as
      `GOOGLE_CLIENT_ID` in Railway (unchanged — this is the whole point).
- [ ] Open the `Inclusify` client → its **Authorized redirect URIs** match the
      app's live callback (typically `https://<backend-domain>/auth/google/callback`).
      If Railway assigned a new public domain during handover, **add the new URI here**.
- [ ] The ⚠️ warning on the client is resolved.
- [ ] Consent-screen **support email / developer contact** point to an
      Achva-controlled address (or the `inclusify.support@gmail.com` account is
      handed over).
- [ ] Publishing status decided: **In production** for a live service, or a
      documented reason it stays in **Testing**.
- [ ] Google login works end-to-end on the live app (also covered by §9, step 3).
- [ ] `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in Railway are **unchanged**.

> **Alternative (reissue instead of transfer):** Offek creates his own GCP
> project → **APIs & Services → Credentials → Create credentials → OAuth client
> ID** (application type *Web application*) → set the **Authorized redirect
> URIs** → **update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in Railway**.
> Cleaner identity, but requires the Railway edit and forces users to re-consent.

### 6B. Resend — email (`RESEND_API_KEY` + `RESEND_FROM`)

Resend sends **all** transactional mail — password reset **and** the contact
form. Both now read the single `RESEND_FROM` sender var (there is no `EMAIL_FROM`
anymore — one var controls both). Handing over Resend has two parts: **owning the
account**, and — the part that actually decides whether real users get mail —
**verifying a sending domain**.

#### The hard prerequisite: a verified domain (this is what unblocks delivery)

Without a verified domain, Resend sends from its shared test address
(`onboarding@resend.dev`) and **only delivers to the Resend account owner's own
inbox** — every other recipient gets nothing, silently. No code change fixes
this; it is a Resend + DNS task:

1. **Resend dashboard → Domains → Add Domain.** Use a domain Achva controls —
   `achvalgbt.org.il`, or a mail subdomain like `send.achvalgbt.org.il`
   (a subdomain keeps email reputation off the main site — recommended).
2. Resend shows DNS records to add (SPF `TXT`, DKIM `TXT`/`CNAME`, usually a
   return-path `MX`, and a recommended DMARC `TXT`).
3. **Add them in Wix → Manage DNS Records** — the *same* panel as the Railway
   custom domain (§7D). Offek does both DNS jobs in one sitting.
4. Wait for Resend to show the domain **Verified** (minutes to a few hours).
5. **Set `RESEND_FROM` in Railway** (backend service) to an address on that
   verified domain, e.g. `Inclusify <noreply@achvalgbt.org.il>`. This fixes the
   contact form and password reset **together**.
6. Redeploy the backend.

Free tier covers this app's volume — a verified domain plus modest daily/monthly
limits are included; a paid plan is only for higher volume, **not** for delivery
itself.

#### Ownership + billing

Either **transfer the Resend account** to Achva (it's on
`inclusify.support@gmail.com`, so handing over that Google login per §6A carries
it), **or** Offek creates a fresh Resend account, verifies the domain as above,
generates a new API key, and **updates `RESEND_API_KEY` in Railway**. Free tier
needs no card; a card is only required if they move to paid for volume.

#### Verify

- [ ] Resend shows the sending domain **Verified** (green).
- [ ] `RESEND_FROM` in Railway points at an address on that domain (not
      `onboarding@resend.dev`).
- [ ] A password reset **and** a contact-form submit both arrive at a
      **non-owner** test inbox (proves the domain, not just owner-only delivery).
- [ ] If the account was recreated, `RESEND_API_KEY` in Railway is the new key.

> **Diagnosing "no email arrives"** — check the Railway backend logs after a send:
> `RESEND_API_KEY not set — skipping` = key missing; `403 … testing emails to your
> own email` = **domain not verified** (the usual cause); logged as "sent" but
> nothing received = recipient wasn't the account owner and the domain still isn't
> verified.

---

## 7. Platform 5 — Railway (backend + frontend + Postgres) — do this LAST

**Goal:** the whole project moves to Offek's Railway workspace, carrying the
backend, frontend, **Postgres + its data**, and **all environment variables** in
one transfer.

### 7A. Billing (must be set up BEFORE the transfer)

**Offek — create and fund the destination workspace first:**
1. Railway → create a **workspace** (or use his personal one).
2. Put it on an **active Hobby (or Pro) plan** with **his card**.
   - The transfer will be rejected if the destination workspace is not on a paid plan.
   - Both source and destination need an active Hobby/Pro plan for the transfer.

### 7B. Ownership (transfer the project)

**Shahaf (must be project Admin):**
1. Open the project → **Settings** page.
2. Click **Transfer Project**.
3. In the modal, select Offek's workspace and confirm.

*If workspace-to-workspace isn't available on the current plans:* add Offek as a
project **member** (Members tab) → click the **three dots** next to his name →
**Transfer Ownership** → he gets an email and has **24 hours** to accept.

**Then re-point the deploy source to the Achva repo:**
1. Install the **Railway GitHub App** on the new Achva GitHub org (GitHub → org
   **Settings → GitHub Apps**, or Railway will prompt to grant access).
2. In each Railway service → **Settings** → the **Source** / connected repo →
   reconnect to `<achva-org>/inclusify` on the correct branch (prod deploys from
   `main`).

### 7C. Verify

- [ ] Project appears under **Offek's workspace**; Offek is the workspace owner.
- [ ] The **Postgres** service is present and its data is intact (log in to the
      app; existing users / saved analyses are still there).
- [ ] All critical env vars are present on the services (see the table in §8) —
      Railway carries them with the project, but **confirm** the list.
- [ ] Each service's **Source** points at `<achva-org>/inclusify`.
- [ ] A test commit to `main` triggers a deploy in Offek's workspace.
- [ ] Offek's card is the workspace payment method; Shahaf's is removed.
- [ ] The app's **public domain** is unchanged (if it changed, update the Google
      OAuth redirect URI in §6A and any hard-coded frontend API base). See §7D
      for the branded custom domain.

### 7D. Custom domain — `inclusify.achvalgbt.org.il` (Wix DNS, operated by Offek)

Achva's site `achvalgbt.org.il` runs on **Wix** (Wix nameservers) and **Offek**
manages it. Goal: create the subdomain `inclusify.achvalgbt.org.il` pointing at
our app, and Achva adds a **link/button** from their Wix site to it.

**Architecture decision — point the subdomain at the FRONTEND only.**
Auth is **bearer-token JWT in localStorage (not cookies)**, and the Google OAuth
callback lives on the **backend** (`/auth/google/callback`, built from the
backend's own host in `backend/app/auth/oauth.py`). Therefore:
- `inclusify.achvalgbt.org.il` → the **frontend** Railway service.
- The **backend stays on its Railway domain** → the **Google redirect URI does
  not change**, and there is only **one** DNS record set to add.
- *(Optional/heavier: also give the backend `api.inclusify.achvalgbt.org.il`.
  Nicer URLs, but then you add a 2nd CNAME/TXT, update the Google redirect URI,
  and change `NEXT_PUBLIC_API_URL`. Not needed — skip it.)*

**Step 1 — Railway (Offek): add the custom domain to the FRONTEND service.**
1. Railway → **frontend** service → **Settings** → **Public Networking**.
2. Click **+ Custom Domain** → enter `inclusify.achvalgbt.org.il`.
3. Railway shows **two records** — a **CNAME** (routes traffic) and a **TXT**
   (verifies ownership). **Both are required**; with only the CNAME the domain
   returns 404. Copy each record's host + value.

**Step 2 — Wix (Offek): add those records.**
1. Wix account → **Domains** → **Domain Actions** (⋮) next to `achvalgbt.org.il`
   → **Manage DNS Records**.
2. Under **CNAME (Aliases)** → **+ Add Record** → **Host Name** = `inclusify`
   (just the label, not the full domain) → **Value** = Railway's CNAME target.
3. Under **TXT** → **+ Add Record** → the host + value Railway gave for verification.
4. **Save** → **Save Changes**. Propagation can take up to ~48h (usually minutes).

**Step 3 — Railway auto-issues TLS.** Once DNS resolves, Railway provisions a
Let's Encrypt certificate automatically; the domain flips to **Active**.

**Step 4 — Update backend env vars (Railway → backend service → Variables):**
- `FRONTEND_URL` = `https://inclusify.achvalgbt.org.il` (OAuth-success redirect +
  password-reset links point here).
- `ALLOWED_ORIGINS` — **add** `https://inclusify.achvalgbt.org.il` (CORS;
  comma-separated — keep the old Railway frontend origin until fully cut over).
- `NEXT_PUBLIC_API_URL` — **no change** (stays pointing at the backend). Note it
  is baked at frontend **build** time, so *if* you ever change it, redeploy the frontend.

**Step 5 — Achva links to it (Offek).** On the Wix site, add a button/link to
`https://inclusify.achvalgbt.org.il`. **Do NOT embed it in an iframe** — Google
OAuth refuses to run inside a frame and login will break. A plain link (fine to
use `target="_blank"`) is correct.

**Verify:**
- [ ] `https://inclusify.achvalgbt.org.il` loads the app over HTTPS (valid cert).
- [ ] Both the `inclusify` **CNAME** and the **TXT** exist in Wix DNS.
- [ ] Google login works **from the subdomain** (redirect lands back on
      `inclusify.achvalgbt.org.il` — proves `FRONTEND_URL` + `ALLOWED_ORIGINS`).
- [ ] Upload → analyze → download works from the subdomain (proves CORS to backend).
- [ ] The link on the Achva Wix site opens the app (not iframed).

---

## 8. Environment-variable cross-reference (what changes, and when)

All of these live on the **Railway** backend service. "Changes?" = do you have
to edit it in Railway during handover.

| Env var | Points at | Changes if you **transfer**? | Changes if you **recreate**? |
|---|---|---|---|
| `VLLM_URL` | Modal workspace | **No** (same workspace name) | **Yes** (new workspace in URL) |
| `VLLM_API_KEY` | Modal secret `inclusify-vllm-key` | **No** | **Yes** if you regenerate the key |
| `VLLM_MODEL_NAME` (`inclusify`) | LoRA adapter name | No | No |
| `S3_ENDPOINT_URL` | Cloudflare account ID | **No** (same account) | **Yes** (new account ID) |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | R2 API token | **No** | **Yes** (new tokens) |
| `S3_BUCKET` / `S3_REGION` | R2 bucket | No | **Yes** if new bucket |
| `DATABASE_URL` | Railway Postgres | No (travels with project) | — |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud project | **No** (transfer project) | **Yes** (new OAuth client) |
| `RESEND_API_KEY` / `RESEND_FROM` | Resend account | **No** (transfer account) | **Yes** (new key/address) |
| `JWT_SECRET` | app-internal | No — keep as-is | No |
| `FRONTEND_URL` | frontend public URL | n/a — set to the custom domain in **§7D** | same |
| `ALLOWED_ORIGINS` | CORS allow-list | n/a — add the custom domain in **§7D** | same |
| `NEXT_PUBLIC_API_URL` | backend public URL (frontend build-time) | **No** (backend domain stable) | **Yes** if the backend domain changes |

**Takeaway:** the account-transfer path (column 3) requires **zero** env edits
and keeps prod live. The recreate path (column 4) forces synchronized env edits.
The three domain vars change only when you adopt the custom domain (**§7D**), not
from the account transfers.

---

## 9. Final end-to-end smoke test (run after step 7)

Do this as a normal user against the live app, on Offek's infrastructure. If the
custom domain (§7D) is set up, run it against `https://inclusify.achvalgbt.org.il`:

1. `GET /` → health check returns OK.
2. `GET /api/v1/health/model` → vLLM reachable / circuit-breaker closed
   (may cold-start on Modal — allow scale-from-zero time).
3. **Log in with Google** → OAuth round-trip succeeds (proves §6A).
4. **Upload a document** → ingestion parses it (proves R2 write, §4).
5. **Run analysis** → issues returned (proves Modal, §5).
6. **Download the report** → renders (proves R2 read).
7. **Submit the contact form** → email arrives at a **non-owner** inbox (proves
   Resend **with a verified domain**, §6B — the usual failure point).
8. Push a trivial commit to `main` → Railway auto-deploys in Offek's workspace.

If all 8 pass on Offek's accounts, the technical handover is complete.

---

## 10. Decommission checklist — the actual definition of "done"

Only after §9 passes:

- [ ] **GitHub:** Shahaf removed from the org (or downgraded), repo owned by Achva org.
- [ ] **Cloudflare:** Shahaf's access revoked; Offek is sole Super Administrator; Shahaf's card removed.
- [ ] **Modal:** Shahaf left the workspace; Offek is Owner; Shahaf's card removed from Stripe.
- [ ] **Google Cloud:** Shahaf removed from the project (or new OAuth client in use); no Shahaf-owned credentials in Railway.
- [ ] **Resend:** account owned by Achva or new key in use.
- [ ] **Railway:** project in Offek's workspace; Shahaf's card removed; deploys from Achva repo.
- [ ] **No Shahaf payment method** remains on any platform. ← the success test.
- [ ] `docs/OPERATIONS.md` updated with the new account locations/owners.

---

## 11. Safety / rollback

- **Grace window:** keep Shahaf as an admin/member on each platform for ~2–4
  weeks after cutover, in case something breaks. Remove access (step 10) only
  once Offek has run a full deploy + smoke test himself.
- **Do not delete** the old Modal workspace / old R2 data / old repo until §9
  has passed on the new accounts.
- **Budget alert:** have Offek set a Modal spend alert and a Railway usage
  alert on day one — GPU (Modal T4) and the Railway replica are the recurring
  costs, and they're now on his card.
