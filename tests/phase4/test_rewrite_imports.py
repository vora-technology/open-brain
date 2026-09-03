from __future__ import annotations

from tools.phase4.rewrite_imports import rewrite_relative_imports, rewrite_text


def test_manifest_rewriter_changes_only_owned_module_endpoints() -> None:
    old_root = "open_" + "brain"
    engine_root = old_root + "_engine"
    connector_root = old_root + "_connectors"
    legacy_root = old_root + "_legacy"
    rewrites = {
        old_root: engine_root,
        f"{old_root}.capture": f"{engine_root}.capture",
        f"{old_root}.capture.auth": f"{old_root}.capture.auth",
        f"{connector_root}.capture.auth": f"{old_root}.capture.auth",
        f"{old_root}.core.models": f"{engine_root}.core.models",
        f"{engine_root}.core.models": f"{engine_root}.core.models",
        f"{old_root}.parity": f"{old_root}.parity",
        f"{legacy_root}.parity": f"{old_root}.parity",
    }
    source = (
        f"from {old_root} import __version__\n"
        f"from {old_root} import parity\n"
        f"from {old_root}.capture.auth import Token\n"
        f"from {connector_root}.capture.auth import Token as FutureToken\n"
        f"from {old_root}.core.models import Intent\n"
        f"import {old_root}.core.models\n"
        f"value: {old_root}.core.models.Intent\n"
        f'synthetic = "import {old_root}.core.models"\n'
    )

    assert rewrite_text(source, rewrites) == (
        f"from {engine_root} import __version__\n"
        f"from {old_root} import parity\n"
        f"from {old_root}.capture.auth import Token\n"
        f"from {old_root}.capture.auth import Token as FutureToken\n"
        f"from {engine_root}.core.models import Intent\n"
        f"import {engine_root}.core.models\n"
        f"value: {engine_root}.core.models.Intent\n"
        f'synthetic = "import {old_root}.core.models"\n'
    )

    relative = "from .models import ReviewAggregate\n"
    assert rewrite_relative_imports(
        relative,
        source_module=f"{old_root}.review.routing",
        source_is_package=False,
        source_moved=False,
        rewrites={
            f"{old_root}.review.models": f"{engine_root}.review.models",
            f"{engine_root}.review.models": f"{engine_root}.review.models",
        },
    ) == f"from {engine_root}.review.models import ReviewAggregate\n"
    assert rewrite_relative_imports(
        relative,
        source_module=f"{old_root}.review.routing",
        source_is_package=False,
        source_moved=True,
        rewrites={},
    ) == relative
    assert rewrite_relative_imports(
        relative,
        source_module=f"{old_root}.review.routing",
        source_is_package=False,
        source_moved=True,
        rewrites={
            f"{old_root}.review.routing": f"{legacy_root}.review.routing",
            f"{legacy_root}.review.routing": f"{legacy_root}.review.routing",
            f"{old_root}.review.models": f"{engine_root}.review.models",
            f"{engine_root}.review.models": f"{engine_root}.review.models",
        },
    ) == f"from {engine_root}.review.models import ReviewAggregate\n"
