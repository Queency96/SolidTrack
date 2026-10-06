"""
Shared pagination classes.

Currently only one class is defined, but the module exists as the
canonical place for pagination behaviour so future endpoints can
import from here rather than re-declaring DRF classes.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPageNumberPagination(PageNumberPagination):
    """
    Standard page-number pagination for list endpoints.

    Query parameters
    ----------------
    ?page=<int>          Page number (1-based).
    ?page_size=<int>     Optional override, capped at max_page_size.

    Response shape
    --------------
    {
        "count": <int>,
        "next": "<url|null>",
        "previous": "<url|null>",
        "results": [...]
    }
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"