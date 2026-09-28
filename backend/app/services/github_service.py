from typing import Any

import httpx

from app.config.settings import get_settings


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


class GitHubService:
    def __init__(self) -> None:
        settings = get_settings()
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret
        self.redirect_uri = settings.github_redirect_uri

    def get_authorization_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read:user user:email repo",
        }

        request = httpx.Request(
            "GET",
            GITHUB_AUTHORIZE_URL,
            params=params,
        )
        return str(request.url)

    async def exchange_code_for_token(self, code: str) -> str:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data=payload,
                headers=headers,
            )

        response.raise_for_status()
        token_data: dict[str, Any] = response.json()
        access_token = token_data.get("access_token")

        if not isinstance(access_token, str) or not access_token:
            raise ValueError("GitHub did not return an access token")

        return access_token

    async def get_authenticated_user(
        self,
        access_token: str,
    ) -> dict[str, Any]:
        headers = self._headers(access_token)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/user",
                headers=headers,
            )

        response.raise_for_status()
        return response.json()

    async def get_user_repositories(
        self,
        access_token: str,
    ) -> list[dict[str, Any]]:
        headers = self._headers(access_token)
        repositories: list[dict[str, Any]] = []
        page = 1

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{GITHUB_API_URL}/user/repos",
                    headers=headers,
                    params={
                        "per_page": 100,
                        "page": page,
                        "sort": "updated",
                    },
                )
                response.raise_for_status()

                page_data: list[dict[str, Any]] = response.json()
                repositories.extend(page_data)

                if len(page_data) < 100:
                    break

                page += 1

        return repositories

    async def get_repository_commits(
        self,
        access_token: str,
        owner: str,
        repository_name: str,
    ) -> list[dict[str, Any]]:
        headers = self._headers(access_token)
        commits: list[dict[str, Any]] = []
        page = 1

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{GITHUB_API_URL}/repos/{owner}/{repository_name}/commits",
                    headers=headers,
                    params={
                        "per_page": 100,
                        "page": page,
                    },
                )
                response.raise_for_status()

                page_data: list[dict[str, Any]] = response.json()
                commits.extend(page_data)

                if len(page_data) < 100:
                    break

                page += 1

        return commits

    @staticmethod
    def _headers(access_token: str) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }