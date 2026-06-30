# HANDOFF v0.43.2 - Fix CI health check

## Key Changes
- **Health Check node_modules Exclusion:** Patched   to ignore  and  directories. This prevents scanning tsconfig.json (JSONC) and temporary library files, ensuring a completely green and fast CI run.
- **Inmutable v0.43.1 Preservation:** Retained all 0.43.1 features (contraportadas, vertical flyers, and React compilation fixes) perfectly untouched.
- **Unified Versioning:** Bumped version to  across  and , with a dedicated changelog entry.
