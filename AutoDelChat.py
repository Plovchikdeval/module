import asyncio
import re
from .. import loader, utils
from telethon.tl.types import Message

class AutoDelChat(loader.Module):
    """
    ✨ AutoDelChat: Эфемерные сообщения для вашей приватности и порядка! ✨

    **Примеры использования:**
    -   Включить: `.autodelete on`
    -   Выключить: `.autodelete off`
    -   Установить задержку удаления сообщения . autodelete число и время. Пример : .autodelete 5h (Значит что автоудаление отправленного сообщения будет через 5 часов) 
    -Для поминания работы задержки удаления сообщений 
    s - Секунда
    m - Минута
    h - Час
    d - День
    -   Если не настроена задержка удаления сообщений (или установлена 0), то сообщения будут удаляться сразу после отправки.
    **Разработчик:** @Androfon_AI
    """
    
    strings = {"name": "AutoDelChat"}
    
    __version__ = "1.7" # Обновляем версию, так как внесены правки и улучшения

    CONFIG_SCHEMA = {
        "enabled": loader.ConfigValue(
            True,
            lambda: "Включить/выключить автоматическое удаление исходящих сообщений.",
        ),
        "delay_seconds": loader.ConfigValue(
            0,
            lambda: "Задержка перед удалением сообщения в секундах (0 = немедленно). Поддерживает 's', 'm', 'h', 'd' при установке.",
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
        if self.get("enabled"):
            delay = self.get("delay_seconds")
            
            # Планируем удаление сообщения в фоновом режиме, не блокируя watcher.
            # Это позволяет watcher'у сразу обрабатывать следующие исходящие сообщения.
            asyncio.create_task(self._delete_message_after_delay(message, delay))

    # --- Вспомогательные методы для парсинга и форматирования времени ---

    def _parse_delay_string(self, delay_str: str) -> int | None:
        """
        Парсит строку задержки (например, "10s", "5m", "2h", "1d" или просто "30")
        и возвращает общее количество секунд.
        Возвращает None, если строка не может быть распарсена или содержит неверную единицу.
        """
        # Регулярное выражение для захвата числа и опциональной единицы измерения
        # Например: "10" (группа 1: 10, группа 2: None)
        # "5m" (группа 1: 5, группа 2: m)
        match = re.match(r"^(\d+)([smhd])?$", delay_str.lower())
        if not match:
            return None

        value_str, unit_char = match.groups()
        value = int(value_str)

        # value < 0 уже покрывается regex (\d+), но можно оставить для доп. проверки,
        # хотя в данном случае это избыточно.

        unit_multipliers = {
            's': 1,       # Секунды
            'm': 60,      # Минуты
            'h': 3600,    # Часы
            'd': 86400    # Дни
        }

        # Если единица не указана, по умолчанию используем секунды
        if unit_char is None:
            unit_char = 's'

        # ИСПРАВЛЕНИЕ: Если единица измерения не найдена, возвращаем None,
        # чтобы _parse_delay_string явно указывал на ошибку парсинга,
        # а не возвращал 0 (что означало бы мгновенное удаление).
        multiplier = unit_multipliers.get(unit_char)
        if multiplier is None:
            return None # Неизвестная единица измерения

        return value * multiplier

    def _format_seconds_to_human_readable(self, total_seconds: int) -> str:
        """
        Преобразует общее количество секунд в человекочитаемый формат (например, "1д 2ч 30м 15с").
        """
        if total_seconds == 0:
            return "0с (мгновенно)"

        parts = []
        
        days = total_seconds // 86400
        if days > 0:
            parts.append(f"{days}д")
            total_seconds %= 86400

        hours = total_seconds // 3600
        if hours > 0:
            parts.append(f"{hours}ч")
            total_seconds %= 3600

        minutes = total_seconds // 60
        if minutes > 0:
            parts.append(f"{minutes}м")
            total_seconds %= 60

        seconds = total_seconds
        # Всегда показывать секунды, если они есть, или если это единственная часть (например, "0с" для остатка)
        if seconds > 0 or not parts: 
            parts.append(f"{seconds}с")
        
        return " ".join(parts)

    # --- Команда autodelete ---

    @loader.command(
        ru_doc=".autodelete [on|off|<время>] - Включить/выключить автоудаление или установить задержку. "
              "Примеры времени: 10s (секунды), 5m (минуты), 2h (часы), 1d (дни)."
    )
    async def autodelete(self, message: Message):
        args = utils.get_args(message)

        if not args:
            # Вывод текущего статуса модуля
            status_text = "<b>Включено</b> <emoji document_id=5823396554345549784>✔️</emoji>" if self.get("enabled") else "<b>Выключено</b> <emoji document_id=5778527486270770928>❌</emoji>"
            delay_seconds = self.get("delay_seconds")
            delay_text = self._format_seconds_to_human_readable(delay_seconds)

            await utils.answer(
                message,
                f"<b>⚙️ Статус AutoDelChat:</b>\n"
                f"  Автоудаление: {status_text}\n"
                f"  Задержка: <code>{delay_text}</code>\n\n"
                f"<b>Использование:</b>\n"
                f"  <code>.autodelete on</code> — Включить\n"
                f"  <code>.autodelete off</code> — Выключить\n"
                f"  <code>.autodelete &lt;время&gt;</code> — Установить задержку\n"
                f"  <i>Примеры времени: <code>10s</code>, <code>5m</code>, <code>2h</code>, <code>1d</code> (<code>0s</code> для мгновенного удаления)</i>\n\n"
                f"<b>Разработчик:</b> @Androfon_AI"
            )
            return

        first_arg = args[0].lower()

        if first_arg == "on":
            self.set("enabled", True)
            await utils.answer(message, "Автоматическое удаление сообщений <b>включено</b>. <emoji document_id=5823396554345549784>✔️</emoji>")
        elif first_arg == "off":
            self.set("enabled", False)
            await utils.answer(message, "Автоматическое удаление сообщений <b>выключено</b>. <emoji document_id=5778527486270770928>❌</emoji>")
        # УЛУЧШЕНИЕ: Можно убрать явный 'delay' аргумент, так как `<время>` уже обрабатывается.
        # Но если вы хотите сохранить его для большей ясности синтаксиса, это тоже допустимо.
        # Я оставлю его, но отмечу, что он может быть избыточным.
        elif first_arg == "delay": 
            if len(args) < 2:
                await utils.answer(message, "Укажите задержку. Например: <code>.autodelete delay 5m</code> <emoji document_id=5778527486270770928>❌</emoji>")
                return
            delay_str = args[1]
            parsed_delay = self._parse_delay_string(delay_str)
            
            if parsed_delay is not None:
                self.set("delay_seconds", parsed_delay)
                formatted_delay = self._format_seconds_to_human_readable(parsed_delay)
                await utils.answer(message, f"Задержка перед удалением установлена на <code>{formatted_delay}</code>. <emoji document_id=5823396554345549784>✔️</emoji>")
            else:
                await utils.answer(message, f"Неверное значение задержки '<code>{delay_str}</code>'. Используйте числа с единицами: 's' (секунды), 'm' (минуты), 'h' (часы), 'd' (дни). Например: <code>10s</code>, <code>5m</code>. <emoji document_id=5778527486270770928>❌</emoji>")
        else: # Попытка распарсить первый аргумент как время (например, `.autodelete 5m`)
            parsed_delay = self._parse_delay_string(first_arg)
            
            if parsed_delay is not None:
                self.set("delay_seconds", parsed_delay)
                formatted_delay = self._format_seconds_to_human_readable(parsed_delay)
                await utils.answer(message, f"Задержка перед удалением установлена на <code>{formatted_delay}</code>. <emoji document_id=5823396554345549784>✔️</emoji>")
            else:
                await utils.answer(
                    message,
                    "Неверный аргумент. Используйте 'on', 'off', '<время>' или 'delay <время>'. "
                    "Примеры времени: <code>10s</code>, <code>5m</code>, <code>2h</code>, <code>1d</code>. "
                    "<emoji document_id=5778527486270770928>❌</emoji>"
                )
