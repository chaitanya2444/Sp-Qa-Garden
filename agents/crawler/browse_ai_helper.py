import httpx
import logging
import os

logger = logging.getLogger("qa_crawler.browse_ai")

class BrowseAIHelper:
    """
    Bridge to Browse AI robots for specialist extraction.
    """
    def __init__(self, combined_key: str = None):
        self.api_key = None
        self.robot_id = None
        
        key = combined_key or os.getenv('BROWSE_AI_API_KEY')
        if key and ":" in key:
            parts = key.split(":")
            self.robot_id = parts[0]
            self.api_key = parts[1]
            logger.info(f"Browse AI Helper initialized with Robot ID: {self.robot_id}")
        else:
            logger.warning("Browse AI API Key missing or malformed. Use ROBOT_ID:API_KEY format.")

    @property
    def is_active(self):
        return self.api_key and self.robot_id

    async def trigger_robot(self, url: str, input_params: dict = None):
        """
        Triggers the specialist robot for a specific URL.
        Useful when the crawler hits a complex page structure.
        """
        if not self.is_active:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "originUrl": url,
            "inputParameters": input_params or {}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"https://api.browse.ai/v2/robots/{self.robot_id}/tasks",
                    json=payload,
                    headers=headers
                )
                if response.status_code == 201 or response.status_code == 200:
                    data = response.json()
                    task_id = data.get('result', {}).get('id')
                    logger.info(f"Browse AI Task triggered! Task ID: {task_id}")
                    return data
                else:
                    logger.error(f"Browse AI Error {response.status_code}: {response.text}")
                    return None
            except Exception as e:
                logger.error(f"Failed to communicate with Browse AI: {e}")
                return None
