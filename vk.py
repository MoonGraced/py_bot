import os
import aiohttp
import asyncio
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

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
        self.piv_lobby = {}
        self.timer = datetime.now()

    async def initialize(self):
        """Асинхронная инициализация"""
        streams = load_channels_from_json('piv_lobby_streamers.json')
        self.piv_lobby = {
            s: await self.check_streamer_by_url(s)
            for s in streams
        }
        await self.check_piv_lobby_streamers()

    async def get_token(self):
        """Асинхронное получение токена"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/oauth/server/token",
                headers={
                    "Authorization": f"Basic {encoded_credentials}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"grant_type": "client_credentials"}
            ) as response:
                response.raise_for_status()
                token_data = await response.json()

        self.token = token_data['access_token']
        expires_in = token_data.get('expires_in', 86400)
        self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)
        return self.token

    async def check_streamer_by_url(self, url):
        """Асинхронная проверка статуса стримера"""
        token = await self.get_token()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://apidev.live.vkvideo.ru/v1/channel",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                params={"channel_url": url}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data

    async def check_piv_lobby_streamers(self):
        """Обновление статусов всех стримеров"""
        for piv_streamer in self.piv_lobby.keys():
            self.piv_lobby[piv_streamer] = (await self.check_streamer_by_url(piv_streamer))['data']['channel']

    def format_piv_lobby_data(self):
        """Форматирование данных (синхронный метод не требует изменений)"""
        result = ""
        for piv_streamer in self.piv_lobby.keys():
            channel_data = self.piv_lobby[piv_streamer]
            if channel_data['status'] == 'offline':
                result += "🔴 "
            elif channel_data['status'] == 'online':
                result += "🟢 "
            else:
                result += f"🔵 {channel_data['status']}"
            result += f"[{channel_data['nick']}](live.vkvideo.ru/{channel_data['url']})\n"
        return result


# Пример использования
async def main():
    vk_api = VKAPI()

    print(await vk_api.format_piv_lobby_data())

if __name__ == "__main__":
    asyncio.run(main())