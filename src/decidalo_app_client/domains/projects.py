"""Projects domain client."""
from __future__ import annotations
from decidalo_app_client._http import HttpHelper

class ProjectsDomain:
    def __init__(self, http: HttpHelper) -> None:
        self._http = http
