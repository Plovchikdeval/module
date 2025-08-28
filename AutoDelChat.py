from .. import loader, utils
from telethon.tl.types import Message

class AutoDelChat(loader.Module):
    """Автоматически удаляет исходящие сообщения после их отправки."""
    
    strings = {"name": "AutoDelChat"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                True,
                lambda: "Включить/выключить автоматическое удаление сообщений.",
            )
        )

    async def on_load(self):
        self.log.info(f"Модуль {self.strings['name']} v{self.__class__.__version__} загружен!")

    @loader.watcher(outgoing=True)
    async def watcher(self, message: Message):
        if self.config["enabled"]:
            try:
                await message.delete()
            except Exception:
                pass

    @loader.command(
        ru_doc=".autodelete on/off - Включить/выключить автоудаление"
    )
    async def autodelete(self, message: Message):
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

# Добавляем версию модуля в класс
AutoDelChat.__version__ = "1.1"
