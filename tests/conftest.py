"""Test-wide isolation of uploaded data.

Every test gets its own empty store in a temporary directory, installed before
the test runs and removed after. Two reasons this is autouse rather than opt-in:

* no test can accidentally read or write the developer's real
  ``data/runtime`` history, which used to be a live hazard when the tests
  monkeypatched a module-level path and one forgot;
* a test that loads data cannot leak it into the next test, so the suite has
  no ordering dependency.

The seeded dataset under ``data/`` is read-only and deliberately shared.
"""

from __future__ import annotations

import pytest

from ui.backend import store


@pytest.fixture(autouse=True)
def isolated_store(tmp_path):
    """A fresh file-backed store, scoped to one test."""
    previous = store.get_store()
    store.set_store(store.FileStore(tmp_path))
    token = store.set_workspace(store.DEFAULT_WORKSPACE)
    try:
        yield tmp_path
    finally:
        store.reset_workspace(token)
        store.set_store(previous)
