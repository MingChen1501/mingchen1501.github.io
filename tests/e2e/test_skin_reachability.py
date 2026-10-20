"""Guard for #296: every minima skin file must be referenced or removed.

``assets/css/style.scss`` compiles only ``minima/skins/{{ site.minima.skin }}``
(``auto`` in ``_config.yml``, ``classic`` in ``_config_theme-dev.yml``), and
the kept skins re-export each other (``classic``/``dark`` import ``auto``).
The solarized trio (``solarized``/``solarized-light``/``solarized-dark``)
had no importer from any configured skin, so it could never reach the
compiled CSS and was deleted.

These guards keep dead skins from creeping back:

- the ``skins/`` directory holds exactly the supported catalog — ``auto``
  (the site skin), ``classic`` (the theme-dev sample skin), ``dark`` (the
  selectable dark-only alternate). A re-added or newly vendored skin fails
  here: reference it from a config and extend the catalog deliberately, or
  delete it instead of keeping it "just in case";
- every configured ``minima.skin`` value (across ``_config*.yml``) must
  resolve to a file on disk, so a typo'd skin fails statically instead of
  breaking the Sass build;
- no ``solarized*.scss`` file may exist — the explicit #296 regression pin.

Static tests (no Ruby, no browser): they run in the fast CI job.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKINS_DIR = REPO_ROOT / "_sass" / "minima" / "skins"

# The supported skin catalog (#296). `auto` is the site skin (`_config.yml`)
# and builds on the `classic` + `dark` palettes; `classic` is the skin of
# the theme-dev sample site (`_config_theme-dev.yml`, built by
# `script/build`); `dark` stays as the selectable dark-only alternate.
# Anything else on disk is dead weight.
EXPECTED_SKINS = frozenset({"auto", "classic", "dark"})


def _configured_skins() -> dict[str, str]:
    """Map each ``_config*.yml`` to its ``minima.skin`` value."""
    skins = {}
    for config_path in sorted(REPO_ROOT.glob("_config*.yml")):
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        skin = (config.get("minima") or {}).get("skin")
        if skin is not None:
            skins[config_path.name] = str(skin).strip()
    return skins


@pytest.mark.static
def test_skin_directory_holds_only_the_supported_catalog():
    """Every skin file is referenced or removed — nothing else may sit here."""
    on_disk = frozenset(path.stem for path in SKINS_DIR.glob("*.scss"))
    assert on_disk == EXPECTED_SKINS, (
        "unexpected skin file(s) in _sass/minima/skins: "
        + ", ".join(sorted(on_disk ^ EXPECTED_SKINS))
        + " — reference them from a config or delete them (see #296)"
    )


@pytest.mark.static
def test_every_configured_skin_exists_on_disk():
    """Each configured ``minima.skin`` must resolve to a skin file."""
    skins = _configured_skins()
    assert skins, "no minima.skin value found in _config*.yml"
    missing = {
        f"{name} (skin: {skin})"
        for name, skin in skins.items()
        if (SKINS_DIR / f"{skin}.scss").is_file() is False
    }
    assert not missing, (
        "configured skin(s) with no file in _sass/minima/skins: "
        + ", ".join(sorted(missing))
    )


@pytest.mark.static
def test_no_solarized_skin_file_remains():
    """The unreachable solarized trio removed in #296 must not come back."""
    offenders = sorted(path.name for path in SKINS_DIR.glob("solarized*.scss"))
    assert not offenders, (
        "unreachable solarized skin file(s) in _sass/minima/skins: "
        + ", ".join(offenders)
    )
