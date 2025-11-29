import asyncio
import os
from asyncio import Task
from typing import Dict
import httpx
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
from models import Streamer

load_dotenv()


def load_channels_from_json(filename='channels.json'):
    """Читает данные о каналах из JSON файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ Данные загружены из {filename}")
        return data.get("urls", [])

    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден")
        return []
    except json.JSONDecodeError:
        print(f"❌ Ошибка чтения JSON из {filename}")
        return []
    except Exception as e:
        print(f"❌ Ошибка при загрузке: {e}")
        return []


class VKAPI:
    def __init__(self):
        self.client_id = os.getenv('VK_CLIENT_ID')
        self.client_secret = os.getenv('VK_CLIENT_SECRET')
        self.base_url = "https://api.live.vkvideo.ru"
        self.token = None
        self.token_expires = None
        self.urls = load_channels_from_json('piv_lobby_streamers.json')
        self.piv_lobby: Dict[str, Streamer] = {}
        self.timer = datetime.now()

    async def get_token(self):
        """Получение токена"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth/server/token",
                headers={
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"grant_type": "client_credentials"}
            )

        response.raise_for_status()
        token_data = response.json()

        self.token = token_data['access_token']
        # Сохраняем время истечения токена (минус 5 минут для запаса)
        expires_in = token_data.get('expires_in', 86400)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)

        return self.token

    async def check_streamer_by_url(self, url) -> Streamer:
        token = await self.get_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://apidev.live.vkvideo.ru/v1/channel",  # или правильный endpoint
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                params={"channel_url": url}
            )
        response.raise_for_status()
        channel = response.json()['data']['channel']
        return Streamer(channel["url"], channel["nick"], channel["status"], response.json()['data']['stream']['title'])

    async def check_piv_lobby_streamers(self):
        tasks: Dict[str, Task] = {}
        for piv_streamer in self.urls:
            tasks[piv_streamer] = asyncio.create_task(self.check_streamer_by_url(piv_streamer))

        for piv_streamer, task in tasks.items():
            self.piv_lobby[piv_streamer] = await task

    def format_piv_lobby_data(self):
        result = ""
        for piv_streamer in self.piv_lobby.keys():
            if self.piv_lobby[piv_streamer].status == 'offline':
                status = "🔴"
            elif self.piv_lobby[piv_streamer].status == 'online':
                status = "🟢"
            else:
                status = f"🔵 {self.piv_lobby[piv_streamer].status}"
            result += f"{status} [{self.piv_lobby[piv_streamer].nick}](live.vkvideo.ru/{self.piv_lobby[piv_streamer].url})\n"
        return result
