"""MkDocs hook to strip doctest flags from rendered documentation.

Doctest flags like `# doctest: +SKIP` are useful for controlling doctest execution,
but they clutter the documentation. This hook removes them from the rendered HTML.
"""

import re
from typing import Any

# Pattern to match doctest flags like: # doctest: +SKIP, # doctest: +ELLIPSIS, etc.
# Also handles multiple flags like: # doctest: +SKIP, +ELLIPSIS
DOCTEST_FLAG_PATTERN = re.compile(r"\s*#\s*doctest:\s*[+\w,\s]+")


def on_page_content(html: str, **kwargs: Any) -> str:
    """Remove doctest flags from page content.

    Args:
        html: The rendered HTML content of the page.
        **kwargs: Additional keyword arguments passed by MkDocs.

    Returns:
        The HTML content with doctest flags removed.
    """
    return DOCTEST_FLAG_PATTERN.sub("", html)
