# ADR-002: External article images via allowlisted attachments (temporary)

- Status: accepted (temporary — see migration below)
- Date: 2026-10-20 (workaround introduced for #195; recorded here by the
  #290 audit)
- Context: no billable object storage, so article images embed by direct
  GitHub issue-attachment URL.
- Decision: single source of truth `_data/image_hosts.yml` (`https` only,
  allowlisted hosts, attachment path prefixes); enforced by
  `script/check-external-images` + `tests/e2e/test_external_images.py`;
  every consumer added for #195 stays easy to remove.
- Consequences: posts depend on attachment URLs; Lighthouse budget carries
  an exemption. Migration (owner-approved storage): repoint the data file,
  rewrite post URLs, drop the exemption and the attachment-host entry,
  update README + `docs/conventions-173.md` + `data-model.md`.
