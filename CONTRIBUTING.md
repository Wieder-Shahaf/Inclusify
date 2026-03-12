# Contributing to Inclusify

Thank you for your interest in contributing to Inclusify! We welcome contributions from the community.

## Code of Conduct

This project and everyone participating in it is governed by our commitment to fostering an inclusive, respectful environment. By participating, you are expected to uphold this standard.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title** and description
- **Steps to reproduce** the behavior
- **Expected behavior**
- **Actual behavior**
- **Screenshots** (if applicable)
- **Environment details** (OS, browser, Node/Python versions)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- Use a clear and descriptive title
- Provide a detailed description of the suggested enhancement
- Explain why this enhancement would be useful
- List any alternative solutions you've considered

### Pull Requests

1. **Fork** the repository and create your branch from `main`
2. **Make your changes** following our coding standards (see below)
3. **Add tests** if you're adding functionality
4. **Update documentation** if you're changing functionality
5. **Ensure tests pass** before submitting
6. **Write clear commit messages** following our convention (see below)

## Development Setup

See the [README.md](README.md#-quick-start) for detailed setup instructions.

## Coding Standards

### TypeScript/Frontend

- Use **TypeScript** for all new code
- Follow **ESLint** configuration (run `npm run lint`)
- Use **functional components** with hooks
- Write **meaningful variable names**
- Add **JSDoc comments** for complex functions
- Keep components **small and focused**

### Python/Backend

- Follow **PEP 8** style guide
- Use **type hints** for all function signatures
- Write **docstrings** for modules, classes, and functions
- Use **async/await** for I/O operations
- Run **ruff** and **mypy** before committing

### Git Commit Messages

Follow conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(analysis): add confidence score to detection results

Adds a confidence score (0-1) to each detected issue based on
rule weight and context matching. Updates API response schema
and adds corresponding frontend display.

Closes #123
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

## Testing

### Frontend Tests

```bash
cd frontend
npm test
npm run test:coverage
```

### Backend Tests

```bash
cd backend
pytest
pytest --cov=app --cov-report=html
```

## Documentation

- Update relevant documentation when making changes
- Add JSDoc/docstrings for new functions
- Update API documentation if endpoints change
- Include screenshots for UI changes

## Questions?

Feel free to open an issue with the `question` label or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
