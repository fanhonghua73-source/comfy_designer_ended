import requests
import uuid
from core.config import settings

class ComfyClient:
    def __init__(self, base_url=settings.COMFY_URL):
        self.base_url = base_url
        self.client_id = str(uuid.uuid4())

    def post_prompt(self, prompt_json: dict):
        """发送 JSON 工作流到 ComfyUI"""
        payload = {
            "prompt": prompt_json,
            "client_id": self.client_id
        }
        response = requests.post(f"{self.base_url}/prompt", json=payload)
        response.raise_for_status()
        return response.json()

    def get_queue_status(self):
        """获取当前队列等待情况"""
        response = requests.get(f"{self.base_url}/queue")
        return response.json()

    def interrupt(self):
        """中断当前任务"""
        return requests.post(f"{self.base_url}/interrupt")

# 实例化单例供全局使用
comfy_client = ComfyClient()