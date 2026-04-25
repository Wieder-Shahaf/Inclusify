<div align="center">

<img src="frontend/public/Inclusify.png" alt="Inclusify" width="220" />

**LGBTQ+ Inclusive Language Analyzer for Academic Texts**

Inclusify is an NLP-powered web platform developed in partnership with the **Achva LGBT Organization**. It helps researchers, editors, and authors identify LGBTQphobic, outdated, biased, or pathologizing language in academic texts — in both Hebrew and English — and suggests inclusive alternatives.

Built as a final academic project at the Technion by a team of five, and delivered as a working product to Achva.

![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?logo=postgresql&logoColor=white)

</div>

---

## What It Does

- Detects problematic language with **severity grading** (High / Medium / Low)
- Provides **educational explanations** and **inclusive alternatives** per finding
- Supports **Hebrew and English** academic texts with full RTL layout
- Generates **downloadable reports** for authors and editors
- **Private mode**: analysis without storing any text to the database
- **Admin dashboard**: usage analytics, glossary management, model performance monitoring

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind v4, Framer Motion, next-intl |
| **Backend** | FastAPI, Python 3.11, Pydantic v2, asyncpg |
| **Database** | PostgreSQL 16 |
| **ML/AI** | QLoRA fine-tuned Qwen2.5-3B-Instruct, vLLM, Docling |
| **Infrastructure** | Microsoft Azure, Docker, GitHub Actions |

---

## Screenshots

### Landing Page
![Landing Page](docs/screenshots/landing.png)

### Analysis Results
![Analysis Results](docs/screenshots/analysis.png)

### Glossary
![Glossary](docs/screenshots/glossary.png)

### Admin Dashboard
![Admin Dashboard](docs/screenshots/admin.png)

---

## Project Timeline

| Date | Milestone |
|------|-----------|
| Dec 2025 | Project kickoff, requirements |
| Jan 2026 | ML fine-tuning, POC validation |
| Feb 2026 | Frontend MVP, backend API |
| Mar 2026 | DB integration, vLLM deployment |
| **Apr 15, 2026** | Second results presentation |
| **Jul 8, 2026** | Final presentation (Part B) |
| **Aug 6, 2026** | Documents & fixes submission |

---

## Team

**Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa**  
Technion — Israel Institute of Technology, 2025–2026

---

## Acknowledgments

- [Achva LGBT Organization](https://achva-lgbt.org.il/) — partner organization and domain expertise
- [Qwen](https://huggingface.co/Qwen) — base model
- [Docling](https://github.com/DS4SD/docling) — document parsing
