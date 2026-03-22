<div align="center">

  # Inclusify

  ### LGBTQ+ Inclusive Language Analyzer for Academic Texts

  <p align="center">
    <strong>AI-powered platform for detecting and correcting exclusionary language in Hebrew and English academic texts</strong>
  </p>

  <p align="center">
    <a href="#-features">Features</a> •
    <a href="#-demo">Demo</a> •
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-documentation">Documentation</a> •
    <a href="#-team">Team</a>
  </p>

  ![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript&logoColor=white)
  ![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
  ![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?logo=postgresql&logoColor=white)
  ![License](https://img.shields.io/badge/License-MIT-green.svg)

</div>

---

## 🌈 About

**Inclusify** is an NLP-powered web platform developed in partnership with **Achva LGBT organization** to promote inclusive language in academic research and publications. The platform identifies LGBTQphobic, outdated, biased, or pathologizing language and provides:

- ✅ **Severity-graded alerts** (High, Medium, Low)
- 📚 **Educational explanations** of why language is problematic
- 💡 **Inclusive alternatives** and suggestions
- 📄 **Downloadable reports** for editors and authors
- 🌍 **Bilingual support** (Hebrew + English with RTL)

Built as a final project for academic coursework with real-world deployment goals.

---

## ✨ Features

### 🔍 **Smart Detection**
- **Hybrid Analysis**: Rule-based detection for known terms + LLM-powered contextual analysis
- **Multilingual**: Native support for Hebrew and English academic texts
- **Fine-tuned Model**: Custom QLoRA fine-tuned `lightblue/suzume-llama-3-8B-multilingual`

### 🎨 **Modern UI/UX**
- **Drag & Drop Upload**: PDF, DOCX, and plain text support
- **Interactive Highlights**: Click flagged text to see detailed explanations
- **Real-time Processing**: Live feedback during analysis
- **Accessibility First**: WCAG 2.1 compliant, full RTL support

### 🔒 **Privacy & Security**
- **Private Mode**: Optional no-storage mode (text never saved to database)
- **GDPR Compliant**: User consent, data retention policies
- **Azure Hosted**: Enterprise-grade infrastructure

### 📊 **Admin Dashboard**
- User analytics and usage statistics
- Glossary management (add/edit/remove terms)
- Issue tracking and improvement metrics

---

## 🎬 Demo

### Upload & Analyze
<table>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/upload.png" alt="Upload Interface" />
      <p align="center"><em>Drag-and-drop file upload</em></p>
    </td>
    <td width="50%">
      <img src="docs/screenshots/analysis.png" alt="Analysis Results" />
      <p align="center"><em>Real-time analysis with highlights</em></p>
    </td>
  </tr>
</table>

### Results & Insights
<table>
  <tr>
    <td width="50%">
      <img src="docs/screenshots/details.png" alt="Issue Details" />
      <p align="center"><em>Detailed issue explanations</em></p>
    </td>
    <td width="50%">
      <img src="docs/screenshots/report.png" alt="Export Report" />
      <p align="center"><em>Downloadable PDF reports</em></p>
    </td>
  </tr>
</table>

> **Note**: Screenshots will be added after UI finalization (Phase 6.2)

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Node.js | `>= 18.0.0` |
| Python | `>= 3.11` |
| PostgreSQL | `>= 14` |
| npm/yarn | Latest |

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/inclusify.git
cd inclusify
```

### 2️⃣ Database Setup

```bash
# Start PostgreSQL (if not running)
brew services start postgresql@14  # macOS
# OR
sudo systemctl start postgresql    # Linux

# Create database and apply schema
createdb inclusify
psql inclusify -f db/schema.sql
psql inclusify -f db/seed.sql
```

### 3️⃣ Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Azure and DB credentials

# Start backend server
uvicorn app.main:app --reload --port 8000
```

Backend will run at **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4️⃣ Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run at **http://localhost:3000**

---

## 🏗️ Tech Stack

<table>
  <tr>
    <th>Layer</th>
    <th>Technologies</th>
  </tr>
  <tr>
    <td><strong>Frontend</strong></td>
    <td>
      <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" />
      <img src="https://img.shields.io/badge/TypeScript-5.0+-blue?logo=typescript" />
      <img src="https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?logo=tailwind-css" />
      <img src="https://img.shields.io/badge/Framer_Motion-pink?logo=framer" />
    </td>
  </tr>
  <tr>
    <td><strong>Backend</strong></td>
    <td>
      <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi" />
      <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python" />
      <img src="https://img.shields.io/badge/Pydantic-v2-E92063" />
      <img src="https://img.shields.io/badge/asyncpg-latest-blue" />
    </td>
  </tr>
  <tr>
    <td><strong>Database</strong></td>
    <td>
      <img src="https://img.shields.io/badge/PostgreSQL-16-316192?logo=postgresql" />
    </td>
  </tr>
  <tr>
    <td><strong>ML/AI</strong></td>
    <td>
      <img src="https://img.shields.io/badge/vLLM-latest-green" />
      <img src="https://img.shields.io/badge/Llama_3-8B-purple" />
      <img src="https://img.shields.io/badge/QLoRA-orange" />
      <img src="https://img.shields.io/badge/Docling-latest-blue" />
    </td>
  </tr>
  <tr>
    <td><strong>Infrastructure</strong></td>
    <td>
      <img src="https://img.shields.io/badge/Microsoft_Azure-0078D4?logo=microsoft-azure" />
      <img src="https://img.shields.io/badge/Docker-blue?logo=docker" />
      <img src="https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions" />
    </td>
  </tr>
</table>

### Architecture Highlights

- **Monorepo Structure**: Unified codebase for frontend, backend, and ML pipelines
- **Async-First**: FastAPI with asyncpg for high-throughput concurrent requests
- **Type Safety**: End-to-end TypeScript + Pydantic validation
- **Internationalization**: next-intl with dynamic locale routing (`/en`, `/he`)
- **Document Processing**: Docling for robust PDF/DOCX text extraction
- **GPU Inference**: vLLM on Azure VM with T4 GPU for production scalability

---

## 📁 Project Structure

```
inclusify/
├── frontend/              # Next.js 16 App Router
│   ├── app/[locale]/     # Locale-based routing (en, he)
│   ├── components/       # UI components (shadcn-style)
│   ├── lib/              # API client, utilities
│   └── messages/         # i18n translations (en.json, he.json)
│
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py      # Application entry point
│   │   ├── core/        # Config, security, middleware
│   │   ├── db/          # Database connection & repositories
│   │   └── modules/     # Feature modules (analysis, ingestion)
│   └── tests/           # pytest test suite
│
├── ml/                   # Machine Learning pipelines
│   ├── LoRA_Adapters/   # Fine-tuned model adapters
│   ├── notebooks/       # Training & evaluation notebooks
│   ├── inference_demo.py # Local inference testing
│   └── outputs/         # Training results & visualizations
│
├── db/                   # Database schemas & seeds
│   ├── schema.sql       # PostgreSQL schema (canonical)
│   └── seed.sql         # Initial data seeding
│
├── data/                 # Training datasets
│   ├── Inclusify_Dataset.csv
│   └── augmented_dataset.csv
│
├── infra/               # Infrastructure as Code
│   └── azure/           # Azure deployment configs
│
├── docs/                # Documentation
│   ├── requirements/    # Product requirements
│   ├── architecture/    # System design docs
│   └── threat_model/    # Security analysis
│
└── scripts/             # Development utilities
    ├── setup_db.sh
    └── setup_ml_env.sh
```

---

## 📚 API Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/` | Health check | ✅ Live |
| `POST` | `/api/v1/ingestion/upload` | Upload PDF/DOCX for text extraction | ✅ Live |
| `POST` | `/api/v1/analysis/analyze` | Analyze text for inclusive language | 🚧 Demo (rule-based) |
| `GET` | `/api/v1/glossary/terms` | Retrieve glossary terms | 🔜 Coming |
| `POST` | `/api/v1/reports/generate` | Generate downloadable report | 🔜 Coming |

### Example: Analyze Text

```bash
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The homosexual lifestyle is a choice.",
    "language": "en",
    "private_mode": true
  }'
```

**Response:**
```json
{
  "issues": [
    {
      "term": "homosexual lifestyle",
      "severity": "high",
      "explanation": "Pathologizing term that implies LGBTQ+ identity is a behavior choice.",
      "alternative": "LGBTQ+ identity",
      "positions": [{"start": 4, "end": 24}]
    }
  ],
  "summary": {
    "total": 1,
    "high": 1,
    "medium": 0,
    "low": 0
  }
}
```

---

## 🧪 Development

### Running Tests

**Backend:**
```bash
cd backend
pytest                              # Run all tests
pytest tests/test_analysis.py      # Run specific test file
pytest -v --cov=app --cov-report=html  # With coverage report
```

**Frontend:**
```bash
cd frontend
npm test                   # Run Jest tests
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage
```

### Code Quality

```bash
# Frontend linting
npm run lint
npm run lint:fix

# Backend linting
cd backend
ruff check .              # Fast linting
mypy app/                # Type checking
black app/ --check      # Code formatting check
```

### Database Migrations

```bash
# Apply schema changes
psql inclusify -f db/schema.sql

# Reset database (⚠️ destroys data)
dropdb inclusify && createdb inclusify
psql inclusify -f db/schema.sql
psql inclusify -f db/seed.sql
```

---

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/inclusify
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Azure ML Endpoint
AZURE_ML_ENDPOINT=https://your-endpoint.azure.com
AZURE_ML_API_KEY=your_api_key

# API Settings
API_V1_PREFIX=/api/v1
DEBUG=true
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Frontend Environment Variables

Create `frontend/.env.local`:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_TIMEOUT=30000

# Feature Flags
NEXT_PUBLIC_ENABLE_PRIVATE_MODE=true
NEXT_PUBLIC_MAX_FILE_SIZE_MB=10
```

---

## 📖 Documentation

- **[Developer Onboarding Guide](ONBOARDING.md)** - Setup instructions for new team members
- **[Product Requirements](docs/requirements/)** - Feature specs and user stories
- **[System Architecture](docs/architecture/)** - Technical design and data flow
- **[Threat Model](docs/threat_model/)** - Security analysis and mitigations
- **[ML Pipeline](ml/README.md)** - Training, evaluation, and inference guide
- **[API Reference](http://localhost:8000/docs)** - Interactive API documentation

---

## 🤝 Contributing

We welcome contributions from the community! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting PRs.

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (descriptive commit messages)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Commit Message Convention

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example:**
```
feat(analysis): add severity filtering to API endpoint

Allows clients to filter results by severity level (high/medium/low).
Includes query parameter validation and updated API docs.

Closes #42
```

---

## 👥 Team

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/shahafwieder">
        <img src="https://github.com/shahafwieder.png" width="100px;" alt="Shahaf Wieder"/><br />
        <sub><b>Shahaf Wieder</b></sub>
      </a><br />
      <sub>Full Stack & ML</sub>
    </td>
    <td align="center">
      <a href="https://github.com/baraksharon">
        <img src="https://github.com/baraksharon.png" width="100px;" alt="Barak Sharon"/><br />
        <sub><b>Barak Sharon</b></sub>
      </a><br />
      <sub>Backend & Infrastructure</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=RD" width="100px;" alt="Rasha Daher"/><br />
      <sub><b>Rasha Daher</b></sub><br />
      <sub>Frontend & UX</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=LZ" width="100px;" alt="Lama Zarka"/><br />
      <sub><b>Lama Zarka</b></sub><br />
      <sub>ML & NLP</sub>
    </td>
    <td align="center">
      <img src="https://via.placeholder.com/100?text=AD" width="100px;" alt="Adan Daxa"/><br />
      <sub><b>Adan Daxa</b></sub><br />
      <sub>Research & QA</sub>
    </td>
  </tr>
</table>

---

## 📅 Project Timeline

| Date | Milestone |
|------|-----------|
| **Dec 2025** | ✅ Project kickoff, requirements gathering |
| **Jan 2026** | ✅ ML model fine-tuning, POC validation |
| **Feb 2026** | ✅ Frontend MVP, backend API design |
| **Mar 2026** | 🚧 Database integration, vLLM deployment |
| **Apr 15, 2026** | 🎯 **Second results presentation** |
| **Jul 8, 2026** | 🎯 **Final presentation (Part B)** |
| **Aug 6, 2026** | 🎯 **Documentation & submission deadline** |

---

## 🏆 Acknowledgments

- **[Achva LGBT Organization](https://achva-lgbt.org.il/)** - Partner organization & domain expertise
- **[LightBlue AI](https://huggingface.co/lightblue)** - Suzume Llama 3 base model
- **[Docling](https://github.com/DS4SD/docling)** - Advanced document parsing
- **Academic Advisors** - Guidance and feedback throughout development

Special thanks to the LGBTQ+ community and allies who provided feedback during beta testing.

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

- **Email**: inclusify.support@example.com
- **Website**: https://inclusify.org
- **Bug Reports**: [GitHub Issues](https://github.com/yourusername/inclusify/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/yourusername/inclusify/discussions)

---

<div align="center">
  <p>Made with 🏳️‍🌈 by Team Inclusify</p>
  <p>
    <sub>Building a more inclusive academic world, one word at a time.</sub>
  </p>

  <a href="#-about">Back to Top ↑</a>
</div>
