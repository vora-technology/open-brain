from __future__ import annotations

from typing import Any, cast

from hatchling.builders.hooks.plugin.interface import (  # type: ignore[import-not-found]
    BuildHookInterface,
)


class CustomBuildHook(BuildHookInterface):  # type: ignore[misc]
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        force_include = build_data.get("force_include")
        if not isinstance(force_include, dict):
            raise TypeError("invalid Hatch force-include data")
        includes = cast(dict[str, str], force_include)
        for source, destination in tuple(includes.items()):
            if destination == ".gitignore":
                del includes[source]
