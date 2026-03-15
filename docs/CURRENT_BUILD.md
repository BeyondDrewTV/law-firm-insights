# Current Build Scope

## Active Pass
Operator startup launcher layer for one-click local Clarion access.

## In Scope (This Pass Only)
- Add root-level operator launchers for startup, command center access, and calibration.
- Reuse verified startup conventions and repo paths (no guessed commands).
- Keep changes additive and local-operator focused.

## Out of Scope
- Calibration engine logic rewrites.
- Frontend/product redesign or architecture refactors.
- Auth/session/security model rewrites.
- Benchmark behavior changes.

## Definition of Done
- Root-level launcher files make startup and calibration one-click from repo root.
- START_CLARION opens command center URL after service startup.
- Paths/commands are verified against existing repo startup scripts.

## Next Likely Passes
1. Additional targeted deterministic calibration tuning.
2. Calibration completion/hardening validation pass.
3. Landing/marketing clarity pass (copy + structure only, grounded in existing capabilities).
