"""Verify M1 tenant isolation logic.

Uses an in-memory SQLite DB so this runs without Postgres or Railway.
Proves:
  1. Run rows can be scoped to different tenants
  2. Tenant-filtered queries return only matching tenant's runs
  3. resolve_tenant() defaults to 'local-dev' in safe mode, and to
     'cardinal-element' when CE_ALLOW_PROD=1 (Railway's production setting).
     SQLModel column default remains 'cardinal-element' (storage-layer
     backward compat, independent of application logic).
"""

from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine, select


def _make_engine():
    engine = create_engine("sqlite:///:memory:")
    from api import models  # noqa: F401  -- registers SQLModel tables
    SQLModel.metadata.create_all(engine)
    return engine


def test_run_default_tenant_is_cardinal_element() -> None:
    from api.models import Run
    engine = _make_engine()
    with Session(engine) as s:
        r = Run(type="protocol", protocol_key="p06_triz", question="test")
        s.add(r)
        s.commit()
        s.refresh(r)
        assert r.tenant_slug == "cardinal-element"


def test_tenant_filter_returns_only_matching_runs() -> None:
    from api.models import Run
    engine = _make_engine()
    with Session(engine) as s:
        s.add(Run(type="protocol", protocol_key="p04", question="A1", tenant_slug="acme"))
        s.add(Run(type="protocol", protocol_key="p06", question="A2", tenant_slug="acme"))
        s.add(Run(type="protocol", protocol_key="p04", question="W1", tenant_slug="workload"))
        s.add(Run(type="protocol", protocol_key="p06", question="W2", tenant_slug="workload"))
        s.commit()

        acme_runs = list(s.exec(select(Run).where(Run.tenant_slug == "acme")).all())
        workload_runs = list(s.exec(select(Run).where(Run.tenant_slug == "workload")).all())

        assert len(acme_runs) == 2
        assert len(workload_runs) == 2
        assert all(r.tenant_slug == "acme" for r in acme_runs)
        assert all(r.tenant_slug == "workload" for r in workload_runs)

        wrong = s.get(Run, workload_runs[0].id)
        assert wrong is not None
        assert wrong.tenant_slug == "workload"


def test_resolve_tenant_defaults_to_local_dev_in_safe_mode() -> None:
    import os, asyncio, importlib
    from unittest.mock import MagicMock

    saved = {
        k: os.environ.pop(k, None)
        for k in ("CLERK_JWKS_URL", "CE_DEV_TENANT", "CE_ALLOW_PROD")
    }
    try:
        from api.middleware import clerk_auth
        importlib.reload(clerk_auth)  # DEFAULT_TENANT is evaluated at import time
        clerk_auth._config.cache_clear()
        req = MagicMock()
        req.headers = {}
        result = asyncio.run(clerk_auth.resolve_tenant(req))
        assert result == "local-dev"
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
        from api.middleware import clerk_auth as _ca
        importlib.reload(_ca)
        _ca._config.cache_clear()


def test_resolve_tenant_defaults_to_cardinal_element_when_allow_prod_set() -> None:
    import os, asyncio, importlib
    from unittest.mock import MagicMock

    saved = {
        k: os.environ.pop(k, None)
        for k in ("CLERK_JWKS_URL", "CE_DEV_TENANT", "CE_ALLOW_PROD")
    }
    os.environ["CE_ALLOW_PROD"] = "1"
    try:
        from api.middleware import clerk_auth
        importlib.reload(clerk_auth)
        clerk_auth._config.cache_clear()
        req = MagicMock()
        req.headers = {}
        result = asyncio.run(clerk_auth.resolve_tenant(req))
        assert result == "cardinal-element"
    finally:
        os.environ.pop("CE_ALLOW_PROD", None)
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
        from api.middleware import clerk_auth as _ca
        importlib.reload(_ca)
        _ca._config.cache_clear()


def test_resolve_tenant_uses_dev_tenant_env_override() -> None:
    import os, asyncio
    from unittest.mock import MagicMock

    saved_jwks = os.environ.pop("CLERK_JWKS_URL", None)
    os.environ["CE_DEV_TENANT"] = "imagine-wireless"
    try:
        from api.middleware.clerk_auth import resolve_tenant, _config
        _config.cache_clear()
        req = MagicMock()
        req.headers = {}
        result = asyncio.run(resolve_tenant(req))
        assert result == "imagine-wireless"
    finally:
        os.environ.pop("CE_DEV_TENANT", None)
        if saved_jwks:
            os.environ["CLERK_JWKS_URL"] = saved_jwks
        from api.middleware.clerk_auth import _config as _c
        _c.cache_clear()
