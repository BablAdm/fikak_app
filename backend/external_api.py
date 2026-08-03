import httpx
from typing import List, Optional
from config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class ExternalAPIClient:
    """Client for external API integrations"""

    def __init__(self):
        """Store the external API base URL and key from settings"""
        self.base_url = settings.external_api_url
        self.api_key = settings.external_api_key

    async def get_posts(self, limit: Optional[int] = 10) -> List[dict]:
        """Fetch posts from external API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/posts",
                    params={"_limit": limit},
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.exception("Error fetching external posts")
            raise RuntimeError(f"Failed to fetch external data: {e}") from e

    async def get_post_by_id(self, post_id: int) -> dict:
        """Fetch a single post by ID"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/posts/{post_id}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.exception(f"Error fetching external post {post_id}")
            raise RuntimeError(f"Failed to fetch post: {e}") from e

    async def get_users(self) -> List[dict]:
        """Fetch users from external API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/users",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.exception("Error fetching external users")
            raise RuntimeError(f"Failed to fetch users: {e}") from e

    def _get_headers(self) -> dict:
        """Get headers for API requests"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


# Singleton instance
external_api_client = ExternalAPIClient()
