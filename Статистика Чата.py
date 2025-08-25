# meta developer: @Androfon_AI
# meta name: Статистика Чата
# meta version: 1.3.9

import logging
from telethon import events
from telethon.tl.types import Channel, Chat, User, MessageActionTopicCreate, Message
from .. import loader

class ChatStatsMod(loader.Module):
    """
    Предоставляет подробную статистику чата и топика.
    """
    strings = {
        "name": "Статистика Чата",
        "no_chat": "❗️ Эту команду можно использовать только в чате.",
        "collecting_chat_stats": "<emoji document_id=5900104897885376843>🕓</emoji> Собираю статистику чата, пожалуйста, подождите...",
        "collecting_topic_stats": "<emoji document_id=5900104897885376843>🕓</emoji> Собираю статистику топика, пожалуйста, подождите...",
        "chat_stats": (
            "<emoji document_id=5877485980901971030>📊</emoji> <b>Статистика чата:</b>\n\n"
            "<emoji document_id=5771887475421090729>👤</emoji> <b>Участников:</b> <code>{}</code>\n"
            "<emoji document_id=5886666250158870040>💬</emoji> <b>Всего сообщений:</b> <code>{}</code>\n"
            "<emoji document_id=5776004296063585809>🖼</emoji> <b>Фото:</b> <code>{}</code>\n"
            "<emoji document_id=5882002216323125435>🎥</emoji> <b>Видео:</b> <code>{}</code>\n"
            "<emoji document_id=5884448719889240368>💾</emoji> <b>Файлов:</b> <code>{}</code>\n"
            "<emoji document_id=5897554554894946515>🎤</emoji> <b>Голосовых сообщений:</b> <code>{}</code>\n"
            "<emoji document_id=5931757531251612084>📷</emoji> <b>Видеосообщений:</b> <code>{}</code>"
        ),
        "topic_stats": (
            "<emoji document_id=5877485980901971030>📊</emoji> <b>Статистика топика \"{}\":</b>\n\n"
            "<emoji document_id=5886666250158870040>💬</emoji> <b>Всего сообщений:</b> <code>{}</code>\n"
            "<emoji document_id=5776004296063585809>🖼</emoji> <b>Фото:</b> <code>{}</code>\n"
            "<emoji document_id=5882002216323125435>🎥</emoji> <b>Видео:</b> <code>{}</code>\n"
            "<emoji document_id=5884448719889240368>💾</emoji> <b>Файлов:</b> <code>{}</code>\n"
            "<emoji document_id=5897554554894946515>🎤</emoji> <b>Голосовых сообщений:</b> <code>{}</code>\n"
            "<emoji document_id=5931757531251612084>📷</emoji> <b>Видеосообщений:</b> <code>{}</code>"
        ),
        "chat_stats_desc": "Показывает подробную статистику текущего чата или топика: количество участников (для чата), сообщений, фото, видео, файлов, голосовых и видеосообщений."
    }

    strings_doc = {
        "chatstats": (
            "Показывает подробную статистику текущего чата или топика.\n"
            "Используйте в обычном чате для статистики всего чата, или в топике "
            "(отвечая на сообщение в топике или отправляя команду прямо в топике) "
            "для статистики конкретного топика. "
            "Включает количество участников (для чата), сообщений, фото, видео, файлов, голосовых и видеосообщений."
        )
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self.logger = logging.getLogger(__name__)

    @loader.command()
    async def chatstats(self, message: Message):
        """Показывает подробную статистику текущего чата или топика."""
        if not message.chat:
            await message.edit(self.strings("no_chat"))
            return

        chat = await message.get_chat()
        
        is_topic_context = False
        target_topic_id = None
        topic_title = None

        if isinstance(chat, Channel) and chat.forum:
            current_message_topic_id = getattr(message, 'topic_id', None)
            if current_message_topic_id:
                target_topic_id = current_message_topic_id
                is_topic_context = True
            elif message.reply_to_msg_id:
                replied_msg = await message.get_reply_message()
                if replied_msg:
                    replied_msg_topic_id = getattr(replied_msg, 'topic_id', None)
                    if replied_msg_topic_id:
                        target_topic_id = replied_msg_topic_id
                        is_topic_context = True
                    elif isinstance(replied_msg.action, MessageActionTopicCreate):
                        target_topic_id = replied_msg.id
                        is_topic_context = True
                        topic_title = replied_msg.action.title
        
        if is_topic_context:
            await message.edit(self.strings("collecting_topic_stats"))
            
            if topic_title is None and target_topic_id:
                try:
                    topic_creation_message = await self.client.get_messages(chat, ids=target_topic_id)
                    if topic_creation_message and isinstance(topic_creation_message.action, MessageActionTopicCreate):
                        topic_title = topic_creation_message.action.title
                except Exception as e:
                    self.logger.warning(f"Не удалось получить название топика {target_topic_id} в чате {chat.id}: {e}")
            
            if topic_title is None:
                topic_title = f"ID: {target_topic_id}"

            video_count = 0
            file_count = 0
            voice_count = 0
            video_note_count = 0
            photo_count = 0
            messages_iterated_count = 0

            try:
                async for msg in self.client.iter_messages(chat, reply_to=target_topic_id, limit=None):
                    messages_iterated_count += 1
                    if msg.media:
                        if msg.video_note:
                            video_note_count += 1
                        elif msg.voice:
                            voice_count += 1
                        elif msg.video:
                            video_count += 1
                        elif msg.photo:
                            photo_count += 1
                        elif msg.document:
                            if not msg.gif and not msg.sticker:
                                file_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка во время итерации сообщений для топика {target_topic_id} в чате {chat.id}: {e}")
                messages_iterated_count = "Недоступно"
                video_count = "Недоступно"
                file_count = "Недоступно"
                voice_count = "Недоступно"
                video_note_count = "Недоступно"
                photo_count = "Недоступно"
            
            await message.edit(self.strings("topic_stats").format(
                topic_title,
                messages_iterated_count,
                photo_count,
                video_count,
                file_count,
                voice_count,
                video_note_count
            ))

        else:
            await message.edit(self.strings("collecting_chat_stats"))

            participants_count = "Недоступно"
            if isinstance(chat, (Channel, Chat)):
                if chat.participants_count is not None:
                    participants_count = chat.participants_count
                else:
                    try:
                        participants_obj = await self.client.get_participants(chat, limit=0)
                        participants_count = participants_obj.total
                    except Exception as e:
                        self.logger.error(f"Ошибка при получении количества участников для чата {chat.id}: {e}")
            elif isinstance(chat, User):
                participants_count = 2

            video_count = 0
            file_count = 0
            voice_count = 0
            video_note_count = 0
            photo_count = 0
            messages_iterated_count = 0

            try:
                async for msg in self.client.iter_messages(chat, limit=None):
                    messages_iterated_count += 1
                    if msg.media:
                        if msg.video_note:
                            video_note_count += 1
                        elif msg.voice:
                            voice_count += 1
                        elif msg.video:
                            video_count += 1
                        elif msg.photo:
                            photo_count += 1
                        elif msg.document:
                            if not msg.gif and not msg.sticker:
                                file_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка во время итерации сообщений для чата {chat.id}: {e}")
                messages_iterated_count = "Недоступно"
                video_count = "Недоступно"
                file_count = "Недоступно"
                voice_count = "Недоступно"
                video_note_count = "Недоступно"
                photo_count = "Недоступно"
            
            await message.edit(self.strings("chat_stats").format(
                participants_count,
                messages_iterated_count,
                photo_count,
                video_count,
                file_count,
                voice_count,
                video_note_count
            ))
