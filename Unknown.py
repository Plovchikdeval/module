# meta developer: @yourhandle
# meta name: AutoDelChat
# meta version: 1.1

from .. import loader, utils
from telethon.tl.types import Message


class AutoDelChat(loader.Module):
    """
    Автоматически удаляет исходящие сообщения после их отправки.
    """

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                True,
                lambda: "Включить/выключить автоматическое удаление сообщений.",
            )
        )

    @loader.watcher(outgoing=True)
    async def watcher(self, message: Message):
        """
        Отслеживает исходящие сообщения и удаляет их, если модуль включен.
        """
        if self.config["enabled"]:
            try:
                # Удаляем исходящее сообщение
                await message.delete()
            except Exception:
                # Пропускаем ошибки, например, если сообщение уже удалено или нет прав.
                pass

    @loader.command(
        ru_doc=".autodelete on / off Включает или отключает автоматическое удаление исходящих сообщений"
    )
    async def autodelete(self, message: Message):
        """
        Включает или отключает автоматическое удаление исходящих сообщений.
        Используйте `.autodelete on`, чтобы включить, или `.autodelete off`, чтобы выключить.
        """
        args = utils.get_args_raw(message)
        if args.lower() == "on":
            self.config["enabled"] = True
            await message.edit("Автоматическое удаление сообщений включено. <emoji document_id=5823396554345549784>✔️</emoji>")
        elif args.lower() == "off":
            self.config["enabled"] = False
            await message.edit("Автоматическое удаление сообщений выключено. <emoji document_id=5778527486270770928>❌</emoji>")
        else:
            status = "включено" if self.config["enabled"] else "выключено"
            await message.edit(f"Автоматическое удаление сообщений сейчас {status}. Используйте 'on' или 'off' для переключения. <emoji document_id=5879785854284599288>ℹ️</emoji>")