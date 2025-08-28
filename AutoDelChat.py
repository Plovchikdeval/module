import asyncio
from .. import loader, utils
from telethon.tl.types import Message

class AutoDelChat(loader.Module):
    """
    ✨ AutoDelChat: Эфемерные сообщения для вашей приватности и порядка! ✨

    **Примеры использования:**
    -   Включить: `.autodelete on`
    -   Выключить: `.autodelete off`
    -   Установить задержку удаленя сообщений: `.autodelete и количество секунд
    -   Если не настроено задержка удаления сообщений, то сообщения будет удаляться сразу после отправки 
    **Разработчик:** @Androfon_AI
    """
    
    strings = {"name": "AutoDelChat"}
    
    __version__ = "1.5" # Обновляем версию, так как есть улучшения (добавлен разработчик, небольшие правки)

    CONFIG_SCHEMA = {
        "enabled": loader.ConfigValue(
            True,
            lambda: "Включить/выключить автоматическое удаление исходящих сообщений.",
        ),
        "delay_seconds": loader.ConfigValue(
            0,
            lambda: "Задержка перед удалением сообщения в секундах (0 = немедленно).",
        ),
    }

    async def on_load(self):
        self.log.info(f"Модуль {self.strings['name']} v{self.__version__} загружен!")

    # Вспомогательный метод для планирования удаления
    async def _delete_message_after_delay(self, message: Message, delay: int):
        """
        Запланировать удаление сообщения после заданной задержки.
        """
        if delay > 0:
            await asyncio.sleep(delay)
        
        try:
            # Для исходящих сообщений message.delete() обычно удаляет для всех.
            # Если требуется явное удаление для всех, можно использовать revoke=True,
            # но для своих сообщений это часто избыточно.
            await message.delete() 
            self.log.debug(f"Сообщение {message.id} в чате {message.chat_id} удалено после задержки {delay}с.")
        except Exception as e:
            # В случае ошибки удаления (например, сообщение слишком старое, уже удалено,
            # или нет прав), просто логируем и игнорируем, чтобы не прерывать работу
            self.log.debug(f"Не удалось удалить сообщение {message.id} в чате {message.chat_id}: {e}")

    @loader.watcher(outgoing=True)
    async def watcher(self, message: Message):
        # Проверяем, включен ли модуль
        # ИСПРАВЛЕНИЕ: Использовать self.get() для доступа к конфигурации
        if self.get("enabled"):
            # ИСПРАВЛЕНИЕ: Использовать self.get() для доступа к конфигурации
            delay = self.get("delay_seconds")
            
            # Планируем удаление сообщения в фоновом режиме, не блокируя watcher.
            # Это позволяет watcher'у сразу обрабатывать следующие исходящие сообщения.
            asyncio.create_task(self._delete_message_after_delay(message, delay))

    @loader.command(
        ru_doc=".autodelete [on|off|<секунды>|delay <секунды>] - Включить/выключить автоудаление или установить задержку."
    )
    async def autodelete(self, message: Message):
        args = utils.get_args(message)

        if not args:
            # Вывод текущего статуса модуля
            # ИСПРАВЛЕНИЕ: Использовать self.get() для доступа к конфигурации
            status_text = "<b>Включено</b> <emoji document_id=5823396554345549784>✔️</emoji>" if self.get("enabled") else "<b>Выключено</b> <emoji document_id=5778527486270770928>❌</emoji>"
            # ИСПРАВЛЕНИЕ: Использовать self.get() для доступа к конфигурации
            delay = self.get("delay_seconds")
            delay_text = f"<code>{delay}</code> секунд"
            if delay == 0:
                delay_text += " (мгновенно)"

            await utils.answer( # Используем utils.answer для более гибкого вывода
                message,
                f"<b>⚙️ Статус AutoDelChat:</b>\n"
                f"  Автоудаление: {status_text}\n"
                f"  Задержка: {delay_text}\n\n"
                f"<b>Использование:</b>\n"
                f"  <code>.autodelete on</code> — Включить\n"
                f"  <code>.autodelete off</code> — Выключить\n"
                f"  <code>.autodelete &lt;секунды&gt;</code> — Установить задержку (напр., <code>.autodelete 5</code>)\n"
                f"  <code>.autodelete delay &lt;секунды&gt;</code> — То же самое\n"
                f"  <i>(<code>0</code> секунд для мгновенного удаления)</i>\n\n"
                f"<b>Разработчик:</b> @Androfon_AI" # Добавляем разработчика в вывод команды
            )
            return

        first_arg = args[0].lower()

        if first_arg == "on":
            # ИСПРАВЛЕНИЕ: Использовать self.set() для изменения конфигурации
            self.set("enabled", True)
            await utils.answer(message, "Автоматическое удаление сообщений <b>включено</b>. <emoji document_id=5823396554345549784>✔️</emoji>")
        elif first_arg == "off":
            # ИСПРАВЛЕНИЕ: Использовать self.set() для изменения конфигурации
            self.set("enabled", False)
            await utils.answer(message, "Автоматическое удаление сообщений <b>выключено</b>. <emoji document_id=5778527486270770928>❌</emoji>")
        elif first_arg == "delay":
            if len(args) < 2:
                await utils.answer(message, "Укажите задержку в секундах. Например: <code>.autodelete delay 5</code> <emoji document_id=5778527486270770928>❌</emoji>")
                return
            try:
                delay = int(args[1])
                if delay < 0:
                    raise ValueError("Задержка не может быть отрицательной.") # Защита от отрицательных значений
                # ИСПРАВЛЕНИЕ: Использовать self.set() для изменения конфигурации
                self.set("delay_seconds", delay)
                await utils.answer(message, f"Задержка перед удалением установлена на <code>{delay}</code> секунд. <emoji document_id=5823396554345549784>✔️</emoji>")
            except ValueError:
                await utils.answer(message, f"Неверное значение задержки. Укажите целое положительное число секунд. <emoji document_id=5778527486270770928>❌</emoji>")
        else: # Попытка распарсить аргумент как число для задержки (например, `.autodelete 5`)
            try:
                delay = int(first_arg)
                if delay < 0:
                    raise ValueError("Задержка не может быть отрицательной.") # Защита от отрицательных значений
                # ИСПРАВЛЕНИЕ: Использовать self.set() для изменения конфигурации
                self.set("delay_seconds", delay)
                await utils.answer(message, f"Задержка перед удалением установлена на <code>{delay}</code> секунд. <emoji document_id=5823396554345549784>✔️</emoji>")
            except ValueError:
                await utils.answer(
                    message,
                    "Неверный аргумент. Используйте 'on', 'off', '<секунды>' или 'delay <секунды>'. "
                    "<emoji document_id=5778527486270770928>❌</emoji>"
        )
                                                                                                         
