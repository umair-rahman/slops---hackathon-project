# Contributing to Marginalia

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone
git clone https://github.com/marginalia-ai/marginalia
cd marginalia

# Backend
cd backend
pip install -e ".[dev]"
python -m spacy download en_core_web_sm

# Frontend
cd ../frontend
pnpm install --ignore-scripts
```

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Code Style

- Python: `ruff check src/` + `mypy src/`
- TypeScript: `pnpm lint` + `pnpm tsc --noEmit`

## Pull Requests

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes
4. Push and open a PR

## License

By contributing, you agree your contributions will be licensed under MIT.
