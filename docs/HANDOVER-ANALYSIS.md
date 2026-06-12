# Inclusify → Achva Handover Analysis

> **Status:** Living document. Last updated 2026-06-06.
> Grounded in real Azure Cost Management data from resource group `Group07`
> (subscription `DDS - 00940395/6 (EA)`, tenant `technion.ac.il`) and official
> Microsoft Learn documentation. Update as decisions and numbers change.

---

## 0. Decisions locked so far

- **Hosting model: on-demand, NOT 24/7.** Traffic is ~a few users/day, peaking
  ~10–30/day — never hundreds/thousands. No need for always-on inference.
- **Integration: Achva links to Inclusify from their existing website**, on a page
  under the **same domain** (subdomain/page). Offek controls DNS.
- **Team provides NO support after handover.** Therefore a detailed, non-technical
  operator handbook (incl. LLM-rescue prompts) is the critical deliverable.

---

## 1. Real cost analytics

Queried via the Cost Management REST API scoped to the `Group07` resource group.
(The `student_contributor` role is blocked from subscription-level billing APIs —
which itself confirms Technion IT, not the team, owns the subscription.)

### Project lifetime (2026-02-01 → 2026-06-06): **$152.72 total**

| Service                | Lifetime | Approx. monthly |
|------------------------|---------:|----------------:|
| Virtual Machines (GPU) |  $66.78  | varies (see below) |
| Container Registry     |  $34.82  | ~$8–14 |
| PostgreSQL             |  $22.10  | ~$8–11 |
| Storage                |  $13.19  | ~$3 |
| Virtual Network        |   $9.48  | ~$2.3 |
| Container Apps         |   $6.19  | ~$1.5 |
| Bandwidth / Log Analytics | ~$0.16 | ~$0 |

### The GPU is the whole budget question

- The T4 VM (`Standard_NC4as_T4_v3`) ran on **only 26 of 126 days**.
- A **full-on day ≈ $8/day** (peak observed: 2026-03-16 = $7.95).
- **24/7 GPU** ≈ **$240/mo** (EA rate) to **~$380/mo** (pay-as-you-go rate Achva
  would pay) → **~$3,000–4,600/yr**.
- **On-demand GPU** (auto-shutdown, a few users/day) ≈ **$15–40/mo**.
- **Always-on baseline** (everything except GPU) ≈ **$25–28/mo**.

### Bottom line

| Scenario | Monthly | Yearly | Sustainable for Achva? |
|----------|--------:|-------:|:--:|
| **On-demand, non-Azure free/cheap tiers (§6)** | **~$0–25** | **~$0–300** | ✅ Best — no grant needed |
| **On-demand, Azure pay-as-you-go** | ~$40–70 | ~$480–840 | ✅ Yes |
| On-demand, inside nonprofit grant | ~$0 | ~$0 | ⚠️ Only if grant obtained (see caveat) |
| 24/7 always-on | ~$270–410 | ~$3,200–4,900 | ❌ No |

> **Headline for the meeting:** the on-demand model costs only **~$40–70/mo on
> Azure pay-as-you-go**, and **~$0–25/mo on free/cheap non-Azure tiers** (see §6) —
> sustainable **regardless of any grant**. The nonprofit grant is a nice-to-have,
> NOT a prerequisite (see eligibility caveat below).

### ⚠️ Nonprofit grant eligibility — do NOT rely on it

Achva LGBT (`achvalgbt.org.il` = "האחווה הסטודנטיאלית הגאה", LGBTI Students'
Association) is **almost certainly NOT an independent Israeli nonprofit**: no Amuta
number, no GuideStar listing, no own legal entity. It operates **under two parent
amutot** — the National Union of Israeli Students (NUIS) and the Aguda /
האגודה למען הלהט"ב (**Amuta 580014058**). (It is NOT connected to Achva Academic
College — coincidental name. The `.org.il` domain implies nothing — open registration.)

- A grant could *in principle* be obtained **through the Aguda's amuta** (TechSoup
  "programs/projects apply under parent" rule) — BUT if Achva is a *fiscally-sponsored*
  initiative it's ineligible even via the sponsor. Needs clarifying with Achva.
- **Implication:** the grant depends on a parent org's cooperation + legal IDs, has
  lead time, and is outside Offek's control. **Plan for the no-grant path (§6); treat
  the grant as a later optimization.**
- **Also unresolved:** since Achva has no legal entity, **who owns the cloud account
  and payment method** post-handover? (Aguda/NUIS account, or an org-owned account on
  free tiers + backup card.) Settle this at the meeting.

### Already cost-optimized (no action needed)

- ACR = **Basic** (cheapest tier)
- PostgreSQL = **B1ms Burstable**, 32 GB (cheapest practical tier)
- GPU VM **auto-shutdown already enabled**, daily 01:00 Israel time

---

## 2. Ownership transfer — practical path

### The situation (confirmed via CLI + docs)

- Subscription is a **Technion Enterprise Agreement (EA)** sub
  (`DDS - 00940395/6 (EA)`, tenant `technion.ac.il`).
- The team holds only a custom **`student_contributor`** role — **Technion IT owns
  the subscription.**
- **EA/academic subscriptions cannot be transferred** to an outside organization.
- Cross-tenant **resource move is not supported** for these resource types.
- Assigning Achva an **Owner role on the resource group ≠ billing ownership** —
  Technion would still pay and could pull the plug. Not a real handover.

### Recommended path: re-provision in Achva's own subscription

1. **Achva** registers at [nonprofit.microsoft.com](https://nonprofit.microsoft.com/),
   completes nonprofit eligibility validation (needs Israeli nonprofit legal docs;
   **takes days–weeks → start ASAP, this is the critical path**), and **activates
   the Azure grant** (~$2,000/yr credit) → creates a new Azure subscription in
   Achva's own account/tenant.
2. **Team re-provisions from scratch** using existing IaC:
   - `infra/scripts/azure-setup.sh` — stands up ACR + PostgreSQL + Container Apps env (VNet)
   - `infra/scripts/azure-deploy.sh` / `azure-push.sh` — build/push images + deploy apps
   - `infra/azure/vllm-vm/setup.sh` — provision GPU VM (with auto-shutdown)
   - Migrate DB: `pg_dump` → `pg_restore` (or `db/schema.sql` + `db/seed.sql`)
   - Migrate blobs: `azcopy` / `az storage blob copy`
   - Repoint **DNS** to the new Container Apps ingress (lower TTL beforehand)
3. **Faculty IT involvement is minimal:** keep `Group07` alive until data is copied
   out, then tear it down (`infra/scripts/azure-teardown.sh`). No transfer paperwork —
   there is nothing transferable.

### Credentials handover (no blockers)

- **Google OAuth/email:** dedicated `inclusify.support` Google account already
  created; credentials handed over directly.
- **Resend / SMTP** keys: handed over directly.

### Key references

- [Transfer billing ownership (MOSP)](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/billing-subscription-transfer) — academic/sponsored offers not transferable
- [Subscription transfer hub / eligibility](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-transfer)
- [Resource move support matrix](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/move-support-resources)
- [Microsoft for Nonprofits — activate Azure grant](https://learn.microsoft.com/en-us/industry/nonprofit/microsoft-for-nonprofits/claim-activate-nonprofit-azure-grant)

---

## 3. Resources currently in `Group07`

| Resource | Type | Notes |
|----------|------|-------|
| `InclusifyModel` (+ vnet/nsg/ip/disk/key/nic) | GPU VM stack | `Standard_NC4as_T4_v3`, T4, vLLM. Auto-shutdown 01:00 IST. |
| `shutdown-computevm-InclusifyModel` | DevTestLab schedule | GPU auto-shutdown (enabled) |
| `inclusify-postgres` | PostgreSQL Flexible Server | B1ms Burstable, 32GB, PG16, region eastus2 |
| `inclusifyacr` | Container Registry | Basic tier |
| `inclusify-env` | Container Apps environment | VNet-integrated |
| `inclusify-backend`, `inclusify-frontend` | Container Apps | scale-to-zero |
| `inclusifystorage` | Storage account | blob container `texts` |
| `Inclusify` | (app resource) | |
| `workspace-roup07*` (x2) | Log Analytics | negligible cost |

---

## 4. Outstanding to-do (4-week window)

**Critical path (start immediately):**
- [ ] Decide hosting target: non-Azure free tiers (§6) vs Azure pay-as-you-go vs grant-via-Aguda
- [ ] Settle who owns the cloud account + payment method (Achva has no legal entity — Aguda/NUIS?)
- [ ] (Optional) Pursue nonprofit grant via the Aguda's amuta (580014058) — clarify program vs fiscal-sponsorship first
- [ ] Confirm DNS/subdomain plan with Offek (Wix — see §7)

**Must do regardless:**
- [x] **Operator handbook** — non-technical, incl. LLM-rescue prompts →
      delivered as `operator-handbook.html` (interactive, bilingual HE/EN, with a
      symptom-based troubleshooter, copy-able AI-rescue prompts incl. a system context
      primer, fill-in credential tables, and monthly/quarterly checklists). Fill in the
      concrete account/dashboard values once the hosting stack is chosen (§8).
- [ ] Credential/account inventory + transfer plan
- [ ] Re-provision + data-migration dry run into a fresh subscription/RG
- [ ] Admin/glossary guide so Offek can manage content himself
- [ ] Load Achva's sample papers into the platform (demo + validation content)

**Conditional / lower priority:**
- [ ] Implement/verify clean on-demand GPU wake-sleep workflow
- [ ] Decide model retrain vs. fold validated data into rule-based layer
      (rule layer = zero infra cost, Offek-controllable → likely better ROI)

---

## 5. Open questions for Achva

- Monthly budget ceiling they can sustain indefinitely (target ~$0–25/mo, see §6)
- **Who is the legal/billing owner of the cloud account?** (No Achva amuta — Aguda? NUIS? org account + card?)
- Do they want to pursue the nonprofit grant via the Aguda, or just use free tiers?
- Public access vs. internal-to-Achva-affiliated users
- Is the "no third-party / no text storage" privacy promise essential? (gates serverless-API GPU options)
- Who is the single post-handover point person (Offek?) and what is he able to do?
- Expectation on model improvement vs. stability for the remaining 4 weeks

---

## 6. Cheaper / non-Azure deployment alternatives

Only the **GPU is expensive or hard to move**; the rest of the stack is already
Dockerized and runs cheaply anywhere. The one Azure-specific code dependency is the
Blob Storage SDK → minor swap to S3-compatible (R2 / Backblaze). **None of the options
below require nonprofit status.**

### GPU inference layer (the cost driver) — true scale-to-zero

| Option | Notes | Cost at ~few–30 req/day |
|---|---|---|
| **Modal** (recommended) | Serverless GPU, custom vLLM+LoRA container, per-second, **$30/mo free credits** | **~$0–10/mo** |
| RunPod Serverless | Cheapest raw serverless GPU, bring Docker image | ~$5–20/mo |
| Together.ai | Upload LoRA, per-token, zero infra to manage | ~$2–5/mo |
| HF Inference Endpoints | scale-to-zero, T4 ~$0.50/hr | ~$20–60/mo |
| _Azure GPU VM 24/7 (contrast)_ | _always-on_ | _~$240–380/mo_ |

### Web / DB / storage layer (cheap & portable, mostly free tiers)

- **DB:** Neon free tier (scale-to-zero) — $0; or Supabase free
- **Storage:** Cloudflare R2 (free egress) or Backblaze B2 — ~$0 at this volume
- **Web/API:** Render or Fly.io small tier ($0–7/mo), or a single Hetzner CX22 box (~€4/mo) running the whole non-GPU docker-compose
- **Redis:** Upstash free tier

### Recommended cheapest+simplest combo (no grant needed)
**Modal (GPU) + Neon (DB) + Cloudflare R2 (storage) + Render/Fly (web/API)**
→ **~$0–25/month, nothing to manage, true scale-to-zero everywhere.**

> Strategic note: even if the Azure grant comes through, the strongest argument to move
> the GPU off an always-on Azure VM is **operational simplicity** — serverless GPU has
> no VM to forget to turn off (the single biggest risk for a no-IT org).
>
> Pricing snapshot June 2026 — verify live before budgeting; serverless-GPU rates change often.

---

## 7. Wix domain integration (achvalgbt.org.il)

**Live DNS check:** the domain's nameservers are **`ns4.wixdns.net` / `ns5.wixdns.net`**
→ **Wix fully controls DNS.** Root/www point to Wix infra (185.230.63.x). `.org.il`
registered via ISOC-IL but delegated to Wix. **Good case:** Offek can add records from
the Wix dashboard (Domains → Manage DNS Records); no external registrar needed.

**Pattern (Wix is a closed host — cannot run the app on Wix):** put Inclusify on a
**subdomain** (e.g. `inclusify.achvalgbt.org.il`) pointing to the app host, plus a
**link/button** from the Wix site. **Do NOT iframe-embed** the full app — Google login
is blocked in iframes, and RTL/mobile break.

**What's needed from Offek:**
1. Confirm admin access to the Wix account's **Manage DNS Records** screen.
2. Agree the subdomain name (`inclusify.` / `app.` / `tool.`).
3. Add 2 DNS records we provide (one-time, ~5 min): a **CNAME** subdomain → app host,
   and a **TXT/CNAME verification** record for the SSL cert. (SSL is then automatic;
   Wix isn't involved in the cert. Root domain/site untouched.)
4. Add the **link/button** in the Wix Editor (which page/menu + HE/EN text) →
   `https://inclusify.achvalgbt.org.il`.

**Dev-team side (not Offek):** add the new subdomain to Google OAuth authorized
redirect URIs and to the app's `FRONTEND_URL` / `ALLOWED_ORIGINS`, or login will fail.

**First question to ask Offek:** "Do you have access to the DNS Records section in the
Wix dashboard for achvalgbt.org.il?" — everything follows from that.

---

## 8. Full Azure → modern-stack migration mapping

This is the concrete service-by-service plan for moving the whole platform off Azure
onto a cheaper, simpler, more handover-friendly stack. Grounded in the actual Azure
dependencies in the codebase, not a generic list.

### What Azure does for us today

| # | Azure service | Role in Inclusify | Where it lives in code |
|---|---|---|---|
| 1 | GPU VM (`Standard_NC4as_T4_v3`) | vLLM + LoRA inference | `VLLM_URL` → `backend/app/modules/analysis/llm_client.py` |
| 2 | PostgreSQL Flexible Server | All app data | `DATABASE_URL` / `PG*` → `backend/app/core/config.py` |
| 3 | Blob Storage | Stores uploaded text/files | `backend/app/core/blob_storage.py` (Azure SDK) |
| 4 | Container Apps ×2 | Hosts backend + frontend containers | `infra/scripts/azure-deploy.sh` |
| 5 | Container Registry (ACR) | Stores Docker images | `infra/scripts/azure-push.sh` |
| 6 | Redis | Refresh-token store (30-day TTL) | `REDIS_URL` → `backend/app/core/redis.py` |
| 7 | VNet + Log Analytics | Networking + logs | infra only |

**Already non-Azure (zero migration):** Google OAuth and Resend (email) are external
SaaS — only their redirect URIs / origins need updating.

### Target stack — consolidated, 3 vendors (~$5–15/mo)

Optimized for the **fewest dashboards a non-technical operator must touch** (no
post-handover support → simplicity beats squeezing the last dollar).

| Azure | → | Replacement | Why |
|---|---|---|---|
| GPU VM | → | **Modal** | true scale-to-zero serverless GPU, $30/mo free credit, per-second billing |
| Postgres + Redis + backend + frontend | → | **Railway** | one dashboard hosts all four; Postgres & Redis are one-click plugins; builds straight from our existing Dockerfiles/repo |
| Blob Storage | → | **Cloudflare R2** | S3-compatible, free egress, ~$0 at this volume |
| ACR | → | *gone* | Railway builds images from git — no registry to manage |

→ **3 vendors total: Railway + Modal + Cloudflare R2.** A single operator can run the
entire non-GPU stack from Railway's UI.

> The 6-vendor "best free tiers" variant (Vercel + Render + Neon + Upstash + R2 + Modal)
> is genuinely ~$0/mo but spreads the system across six dashboards — too cumbersome to
> hand to an org with no IT staff. Rejected for that reason.

### Code changes required (this is the entire list)

The migration is overwhelmingly config, not code. Only **one file** contains
Azure-specific code.

1. **`backend/app/core/blob_storage.py` → S3/R2 swap** *(the only real code work, ~1 hr).*
   94-line thin wrapper with 3 public async functions (`ensure_container`,
   `upload_text`, `upload_file_bytes`). R2 is S3-compatible → replace the Azure SDK
   internals with `boto3`/`aioboto3`, keep the function signatures identical so nothing
   that calls it changes. New env vars: `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET`,
   `S3_BUCKET` replace `AZURE_STORAGE_CONNECTION_STRING`.
2. **`backend/app/modules/analysis/llm_client.py` → add auth header** *(~4 lines).*
   Modal web endpoints are token-authenticated by default; add an
   `Authorization: Bearer <token>` header to the two `httpx` POST calls.
3. **Pure env-var changes — no code:** `DATABASE_URL` → Railway Postgres string
   (asyncpg already speaks standard Postgres); `REDIS_URL` → Railway Redis; `VLLM_URL`
   → Modal endpoint; `FRONTEND_URL` + Google OAuth redirect URIs → new domain.
4. **Infra:** retire `infra/scripts/azure-*.sh`; replace with a Railway project (git
   connect) + a Modal `app.py` that boots vLLM and loads the LoRA from
   `ml/LoRA_Adapters/`. **The Dockerfiles in `infra/docker/` carry over unchanged** —
   the payoff of having everything Dockerized.

### What disappears entirely (the friendliness win)

- **ACR** — platforms build from the repo/Dockerfile.
- **VNet + Log Analytics** — managed by the platform; logs live in the dashboard.
- **The "did someone leave the GPU on?" risk** — scale-to-zero everywhere means no
  always-on resource to forget. This is the single biggest operational risk for a
  no-IT org, and it is engineered away rather than relying on discipline.

### One wrinkle to flag: cold starts

Scale-to-zero means the first request after an idle period pays a model-load penalty
(loading the 3B model + LoRA = tens of seconds to ~a minute). `VLLM_TIMEOUT` is
`120s` and Container Apps ingress is now `240s`, so a cold start fits the budget — but
the first user after a quiet spell waits. Acceptable for a few-users/day tool in
exchange for ~95% cost reduction; just don't promise sub-second first response.

### Migration order (low-risk sequence)

1. **Storage** — stand up R2, swap `blob_storage.py`, test uploads (additive; doesn't break Azure).
2. **DB** — `pg_dump` from Azure → restore to Railway Postgres; flip `DATABASE_URL`.
3. **Redis** — Railway Redis plugin; flip `REDIS_URL` (refresh tokens just re-issue — low stakes).
4. **GPU** — deploy Modal app; flip `VLLM_URL` + add auth header.
5. **Web/API** — deploy backend + frontend to Railway from the same Dockerfiles.
6. **DNS** — point `inclusify.achvalgbt.org.il` (Wix, §7) at the new frontend; update OAuth redirect URIs.
7. **Tear down** `Group07` once verified (`infra/scripts/azure-teardown.sh`).

### Open dependencies (from §5)

- **"No third-party / no text storage" privacy promise** — if binding, it constrains
  both R2 and any serverless GPU (text leaves our control). Resolve with Achva first.
- **Billing-account ownership** on Railway / Modal / Cloudflare post-handover.

### Reference

- Modal pricing: <https://modal.com/pricing> · vLLM example: <https://modal.com/docs/examples/vllm_inference>
