"""Check the bound set's platform assumptions against the deployed configuration.

`PublicRequestBounds` carries `assumed_platform_response_bytes` and
`assumed_platform_timeout_seconds` as named assumptions rather than facts, on the
grounds that the module does not know what is deployed. Naming an assumption is only
worth something if something checks it; otherwise it is a constant with a longer name.

```text
declared constant != configuration in force
a named assumption != a checked assumption
```

So this reads the numbers out of the Terraform that configures the runtime, the same way
the watermark tests read declared column types out of the Glue Terraform rather than
restating them. The first run of this check found the timeout assumption wrong by 2.9x.

What it cannot check is the platform's own ceiling — the bytes a Lambda may return
synchronously is AWS's number, not this repository's, and nothing here can read it. That
one stays an assumption with a stated margin, and the margin is what makes it safe to be
wrong about: the budget projects 1,045,440 bytes, so the assumption would have to be
wrong by more than six times before the ceiling bound.
"""

import re
from pathlib import Path
from typing import Final

from opslens.public_analysis.domain.request_bounds import PUBLIC_REQUEST_BOUNDS

_RUNTIME_TF: Final = (
    Path(__file__).resolve().parents[3]
    / "infra"
    / "environments"
    / "dev"
    / "public_async_runtime.tf"
)


def _integration_timeout_milliseconds() -> int:
    """Read the API Gateway integration timeout out of the Terraform.

    Returns:
        The configured timeout in milliseconds.
    """
    source = _RUNTIME_TF.read_text(encoding="utf-8")
    matched = re.search(r"timeout_milliseconds\s*=\s*(\d+)", source)
    assert matched is not None, "the public runtime no longer configures an integration timeout"
    return int(matched.group(1))


def test_the_runtime_terraform_still_configures_an_integration_timeout() -> None:
    """A bound set assuming a timeout must fail loudly if the timeout disappears."""
    assert _integration_timeout_milliseconds() > 0


def test_the_timeout_assumption_matches_what_is_configured() -> None:
    """The check that caught the first wrong assumption.

    The bound set shipped assuming 29 seconds, which is the classic REST API Gateway
    maximum. The deployed HTTP API integration is configured at 10 seconds — a request
    has under a third of the time the bounds were written against, which changes what
    "a request that reads 5,000 rows" means in practice.
    """
    configured = _integration_timeout_milliseconds() // 1000
    assert PUBLIC_REQUEST_BOUNDS.assumed_platform_timeout_seconds == configured


def test_the_response_budget_leaves_margin_on_the_unverifiable_assumption() -> None:
    """The platform's response ceiling is AWS's number and cannot be read from here.

    So the protection is margin, not verification: the assumption would have to be wrong
    by more than six times before it binds.
    """
    assert PUBLIC_REQUEST_BOUNDS.platform_headroom > 6
