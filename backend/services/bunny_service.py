"""
bunny_service.py — back-compat shim. The real implementation moved to
`services/bunny/signer.py` in Step 7 of the bunny consolidation.

Existing call sites (e.g. `from services.bunny_service import
generate_signed_embed_url, validate_bunny_config, BunnyConfigError`)
keep working unchanged thanks to this shim. New code should import
directly from `services.bunny`:

    from services.bunny import (
        generate_signed_embed_url,
        validate_bunny_config,
        BunnyConfigError,
        verify_credentials,        # NEW (Step 1)
        BunnyStatus,               # NEW (Step 1)
    )

Future cleanup: once every consumer has migrated to the new path, this
shim file can be deleted. There's only one consumer today
(routers/customer_portal.py); the migration is mechanical.
"""

# Re-export every public symbol of the new module. Star-import is OK
# here because signer.py has a small, well-documented public surface
# and we WANT every name forwarded.
from services.bunny.signer import (  # noqa: F401
    BunnyConfigError,
    SignedEmbedUrl,
    DEFAULT_PLAY_URL_TTL_SECONDS,
    REFRESH_MARGIN_SECONDS,
    generate_signed_embed_url,
    validate_bunny_config,
)
