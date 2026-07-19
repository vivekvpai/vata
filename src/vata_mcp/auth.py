"""Static bearer-token auth for the HTTP transport.

Single-user, zero-infra: one shared secret checked in-process, no OAuth
server, no separate auth backend, no extra hosting. Set VATA_MCP_TOKEN and
every tool/prompt call over HTTP must send `Authorization: Bearer <token>`.
If VATA_MCP_TOKEN is unset, auth is disabled (local/stdio dev default).
"""

import hmac

from fastmcp.server.auth.auth import AccessToken, TokenVerifier

from . import config


class StaticTokenVerifier(TokenVerifier):
    def __init__(self, expected_token: str):
        super().__init__()
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._expected_token):
            return None
        return AccessToken(token=token, client_id="vata-single-user", scopes=[])


def build_auth_provider() -> StaticTokenVerifier | None:
    token = config.get("VATA_MCP_TOKEN")
    if not token:
        return None
    return StaticTokenVerifier(token)
