# meta developer: @yourhandle
# meta name: CountMe
# meta version: 1.1.0
#
# (арт)
#  _   _             _
# | | | | __ _ _ __ | |_ ___
# | |_| |/ _` | '_ \| __/ __|
# |  _  | (_| | | | | |_\__ \
# |_| |_|\__,_|_| |_|\__|___/
#

from .. import loader, utils
from telethon.tl.types import Message, Channel, Chat, User
from telethon.errors import FloodWaitError
import asyncio

@loader.tds
class CountMeMod(loader.Module):
    """Считает ваши сообщения в чате и общее количество сообщений"""
    strings = {"name": "CountMe"}

    async def on_install(self):
        """Вызывается при установке модуля."""
        await self.client.send_message(
            self.tg_id,
            "<b>[CountMe]</b> Модуль успешно установлен! Версия: 1.1.0 <emoji document_id=5825794181183836432>✔️</emoji>"
        )

    @loader.command(ru_doc="Посчитать ваши сообщения в текущем чате")
    async def me(self, message: Message):
        """Посчитать ваши сообщения в текущем чате <emoji document_id=5877482652302315100>📁</emoji>"""
        initial_message = await utils.answer(message, "<b>[CountMe]</b> Считаю сообщения в текущем чате... <emoji document_id=5875465628285931233>✈️</emoji>")
        
        count = 0
        me_id = (await self.client.get_me()).id

        try:
            async for msg in self.client.iter_messages(message.chat_id, from_user=me_id):
                count += 1
                if count % 1000 == 0:
                    await self.client.edit_message(
                        initial_message.chat_id,
                        initial_message.id,
                        f"<b>[CountMe]</b> Подсчитано {count} сообщений в текущем чате... <emoji document_id=5900104897885376843>🕓</emoji>"
                    )

            await self.client.edit_message(
                initial_message.chat_id,
                initial_message.id,
                f"<b>[CountMe]</b> В этом чате у вас <code>{count}</code> сообщений. <emoji document_id=5825794181183836432>✔️</emoji>",
            )
        except FloodWaitError as e:
            await self.client.edit_message(
                initial_message.chat_id,
                initial_message.id,
                f"<b>[CountMe]</b> Превышен лимит запросов Telegram. Попробуйте снова через {e.seconds} секунд. <emoji document_id=5778527486270770928>❌</emoji>"
            )
        except Exception as e:
            await self.client.edit_message(
                initial_message.chat_id,
                initial_message.id,
                f"<b>[CountMe]</b> Произошла ошибка при подсчете сообщений: <code>{e}</code> <emoji document_id=5778527486270770928>❌</emoji>"
            )

    @loader.command(ru_doc="Посчитать все ваши сообщения во всех чатах Telegram", command="ma")
    async def ma(self, message: Message):
        """Посчитать все ваши сообщения во всех чатах Telegram <emoji document_id=5877316724830768997>🗃</emoji>"""
        initial_message = await utils.answer(message, "<b>[CountMe]</b> Начинаю подсчет всех ваших сообщений в Telegram. Это может занять много времени... <emoji document_id=5776213190387961618>🕓</emoji>")
        
        total_messages = 0
        me_id = (await self.client.get_me()).id

        try:
            async for dialog in self.client.iter_dialogs():
                # Пропускаем служебные диалоги или те, где нет возможности получить сообщения
                if not isinstance(dialog.entity, (Channel, Chat, User)):
                    continue

                try:
                    async for msg in self.client.iter_messages(dialog.entity, from_user=me_id):
                        total_messages += 1
                        if total_messages % 10000 == 0:
                            await self.client.edit_message(
                                initial_message.chat_id,
                                initial_message.id,
                                f"<b>[CountMe]</b> Подсчитано {total_messages} сообщений... <emoji document_id=5900104897885376843>🕓</emoji>"
                            )
                except FloodWaitError as e:
                    await self.client.edit_message(
                        initial_message.chat_id,
                        initial_message.id,
                        f"<b>[CountMe]</b> Превышен лимит запросов Telegram. Пауза на {e.seconds} секунд... <emoji document_id=5778527486270770928>❌</emoji>"
                    )
                    await asyncio.sleep(e.seconds + 5)
                except Exception:
                    # Игнорируем ошибки для отдельных диалогов (например, удаленные или недоступные пиры)
                    pass 

            await self.client.edit_message(
                initial_message.chat_id,
                initial_message.id,
                f"<b>[CountMe]</b> Всего вы отправили <code>{total_messages}</code> сообщений в Telegram. <emoji document_id=5825794181183836432>✔️</emoji>",
            )
        except FloodWaitError as e:
            await self.client.edit_message(
                initial_message.chat_id,
                initial_message.id,
                f"<b>[CountMe]</b> Превышен лимит запросов Telegram. Попробуйте снова через {e.seconds} секунд. <emoji document_id=5778527486270770928>❌</emoji>"
            )
        except Exception as e:
            await self.client.edit_message(
                initial_message.chat_id,
                initial_message.id,
                f"<b>[CountMe]</b> Произошла общая ошибка при подсчете всех сообщений: <code>{e}</code> <emoji document_id=5778527486270770928>❌</emoji>"
            )