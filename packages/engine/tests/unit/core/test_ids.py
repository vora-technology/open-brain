from __future__ import annotations

import math

import pytest
from open_brain_engine.core.ids import canonical_json_bytes, portable_canonical_json_bytes


def test_canonical_json_bytes_normalizes_unicode_sorts_keys_and_has_no_whitespace() -> None:
    assert canonical_json_bytes({"z": "e\u0301", "a": [1, True, None]}) == (
        b'{"a":[1,true,null],"z":"\xc3\xa9"}'
    )


def test_legacy_canonical_json_bytes_preserves_float_and_vector_callers() -> None:
    assert canonical_json_bytes([0.5, -0.5]) == b"[0.5,-0.5]"


@pytest.mark.parametrize("value", [1.0, math.nan, math.inf, -math.inf])
def test_portable_canonical_json_bytes_rejects_floats(value: float) -> None:
    with pytest.raises(ValueError, match="floats"):
        portable_canonical_json_bytes({"value": value})


def test_portable_canonical_json_bytes_rejects_non_string_object_keys() -> None:
    with pytest.raises(ValueError, match="string object keys"):
        portable_canonical_json_bytes({1: "synthetic"})


def test_portable_canonical_json_bytes_rejects_nfc_normalized_key_collisions() -> None:
    with pytest.raises(ValueError, match="normalized key collision"):
        portable_canonical_json_bytes({"e\u0301": "first", "\u00e9": "second"})
