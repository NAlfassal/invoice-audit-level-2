"""Shared fixtures: the invoices are loaded and the checks run once per test session."""

import pytest

from audit import io
from audit.checks import Finding, run_all
from audit.io import AuditData


@pytest.fixture(scope="session")
def data() -> AuditData:
    return io.load_all()


@pytest.fixture(scope="session")
def findings(data: AuditData) -> list[Finding]:
    return run_all(data)
