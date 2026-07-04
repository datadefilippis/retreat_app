"""``modules`` package marker.

Each module sub-package (``cashflow_monitor``, ``commerce``,
``commerce_signals``, ``customer_insights``, ``product_catalog``)
registers itself at import time via ``core.module_registry.register()``
called from its own ``__init__.py``.  See ``core/module_registry.py``
for the registry contract.

This file used to contain a legacy ``ModuleRegistry`` class that scanned
the filesystem for ``modules/<x>/config.py`` files at first use and
cached the result via ``_discovered = True``.  That registry was the
source of truth for the merchant-facing ``GET /api/modules/available``
and ``/active`` endpoints, while the modern explicit registry in
``core/module_registry.py`` drove capabilities (overview, AI tools,
post-upload hooks, …).  The two stayed in sync only as long as both
were updated together — a renamed folder or a missing ``config.py``
silently broke the merchant page.

The legacy registry has been removed.  Now the single source of truth
is the explicit ``register()`` call in each module's ``__init__.py``,
exposed for the UI via ``core.module_registry.get_all_for_ui()``.
"""
