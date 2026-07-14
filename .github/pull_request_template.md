## Summary
<!-- 1–2 sentences: what this changes and why. -->

## Changes
<!-- Key changes, one bullet each. -->
-

## Type & surface
- **Type:** <!-- feat | fix | refactor | docs | chore -->
- **Surface:** <!-- API | UI | DB | infra — list all that apply -->

## Testing
<!-- How you verified. Backend auth/contract/migration/permission changes REQUIRE automated tests. -->
-

## Checklist
- [ ] `make test` passes (UI-only: `cd ui && bun run build` is clean)
- [ ] No removed/renamed API request/response keys; list pagination preserved
- [ ] Tests added for any auth / contract / migration / permission change
- [ ] No committed secrets; auth stays JWT + bcrypt
- [ ] New UI strings added to **both** `en.json` and `es.json`
- [ ] `memory/CHANGELOG.md` updated (one entry for this PR)
