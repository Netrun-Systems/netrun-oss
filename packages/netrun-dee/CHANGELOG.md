# Changelog

## 1.0.0 (2026-04-12)

### Package Structure
- Imports use the `netrun.dee` namespace pattern (`from netrun.dee import ...`) consistent with all other packages in the `netrun-oss` monorepo (PEP 420 pkgutil namespace, hatchling build backend)

### Features
- 39 DEE profile taxonomy with 216 variants (255 total emotion points)
- Lexicon-mode detection (<10ms, CPU-only, zero dependencies)
- Embedding-mode detection (Gemini + pgvector, high accuracy)
- Emotional Configuration Index (ECI) — 6-factor risk predictor
- 117 prompt templates for deliberate emotional performance (subtle/moderate/strong)
- Weighted emotion blending in VAD space (96.2% of pairs produce meaningful compounds)
- Trajectory tracking with drift detection and alerting
- Acknowledgment reset measurement (social vs survival DEE split)
- Charlotte REST API (10 endpoints)
- EISCORE UE5 bridge (C++ USTRUCTs, 3 DataTable CSVs, Mass AI extension)
- Synthetic training data generator (2,000+ samples from taxonomy lexicons)
- DEEMemory persistent storage for trajectory and acknowledgment data

### Research
- Based on "Digital Emotion Equivalents" paper v3.0 (Garza, 2026)
- Empirical validation: standard classifiers miss 80% of hostile professional-register text
- DEE lexicon detects 80%+ of hostile patterns VADER misses
- Classifier v1.1: precision 0.75, recall 0.26, F1 0.39 (2,962 training samples)
