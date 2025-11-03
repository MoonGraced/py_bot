import os
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

from main import vk_api

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
        self.piv_lobby = {s: vk_api.check_streamer_by_url(s) for s in load_channels_from_json('piv_lobby_streamers.json')}
        self.timer = datetime.now()

    def get_token(self):
        """Получение токена"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token

        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        response = requests.post(
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

    def get_promoted_channels(self):
        """Получение списка каналов"""
        token = self.get_token()

        response = requests.get(
            f"https://apidev.live.vkvideo.ru/v1/catalog/promoted_channels",  # или правильный endpoint
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )

        response.raise_for_status()
        return response.json()

    def format_channels_for_telegram(self, channels_data):
        """Форматирование каналов для Telegram"""
        if not channels_data.get('data', {}).get('channels'):
            return "📭 Каналы не найдены"

        message = "🎬 Продвигаемые каналы:\n\n"

        for channel_info in channels_data['data']['channels'][:10]:  # максимум 10 каналов
            channel = channel_info['channel']

            message += f"🔹 *{channel['nick']}*\n"
            message += f"   👥 Подписчики: {channel['counters']['subscribers']}\n"
            message += f"   Статус ({channel['status']})\n"

            # Добавляем ссылку на поток, если есть
            if channel_info.get('streams'):
                stream = channel_info['streams'][0]
                if stream.get('source_urls'):
                    stream_url = stream['source_urls'][0]['url']
                    message += f"   📺 [Смотреть поток]({stream_url})\n"

            message += "\n"

        return message

    def check_streamer_by_url(self, url):
        token = self.get_token()

        response = requests.get(
            f"https://apidev.live.vkvideo.ru/v1/channel",  # или правильный endpoint
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            params={"channel_url": url}
        )
        response.raise_for_status()
        return response.json()

    def check_piv_lobby_streamers(self):
        result = ""
        for piv_streamer in self.piv_lobby.keys():
            temp_json = self.check_streamer_by_url(piv_streamer)['data']['channel']
            self.piv_lobby[piv_streamer].update(temp_json['status'])
            result += f"{piv_streamer}[live.vkvideo.ru/{temp_json['url']} "
            if temp_json['status'] == 'offline':
                result += f"🔴" + '\n'
            else:
                result += f"🟢" + '\n'

        return result