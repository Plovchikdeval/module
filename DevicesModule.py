# meta developer: @Androfon_AI
# meta name: Устройства
# meta version: 1.0

# 01001000 01101001 01101011 01101011 01100001 00100000 01010101 01110011 01100101 01110010 01000010 01101111 01110100
# 00100000 01001101 01101111 01100100 01110101 01101100 01100101 01110011 00100000 01000111 01100101 01101110 01100101 01110010 01100001 01110100 01101111 01110010

from telethon import functions
from datetime import datetime
from .. import loader, utils


class DevicesModule(loader.Module):
    """
    Модуль для просмотра активных сессий и зарегистрированных устройств на аккаунте.
    """

    strings = {
        "name": "Устройства",
        "no_devices": "У вас нет активных сессий.",
        "device_info": (
            "<b><emoji document_id=5877318502947229960>💻</emoji> Устройство:</b> <code>{device_model}</code>\n"
            "<b><emoji document_id=5877482652302315100>📁</emoji> Платформа:</b> <code>{platform}</code>\n"
            "<b><emoji document_id=5877680341057015789>📁</emoji> ОС:</b> <code>{system_version}</code>\n"
            "<b><emoji document_id=5877307202888273539>📥</emoji> Приложение:</b> <code>{app_name}</code> (v<code>{app_version}</code>)\n"
            "<b><emoji document_id=5967432491684860012>🛜</emoji> IP-адрес:</b> <code>{ip}</code>\n"
            "<b><emoji document_id=5883955653348692941>🗺</emoji> Страна:</b> <code>{country}</code>\n"
            "<b><emoji document_id=5884365569322390150>🗺</emoji> Регион:</b> <code>{region}</code>\n"
            "<b><emoji document_id=5877301185639091664>📄</emoji> Создано:</b> <code>{date_created}</code>\n"
            "<b><emoji document_id=5877410604225924969>🔄</emoji> Активно:</b> <code>{date_active}</code>\n"
            "{current_session}"
        ),
        "current_session_marker": "<b><emoji document_id=5825794181183836432>✔️</emoji> (Текущая сессия)</b>",
        "error_fetching": "Произошла ошибка при получении информации об устройствах.",
        "cmd_devices_desc": "Показывает активные сессии и зарегистрированные устройства.",
        "fetching_message": "<b><emoji document_id=5900104897885376843>🕓</emoji> Получаю информацию об устройствах...</b>",
        "header": "<b><emoji document_id=5877318502947229960>💻</emoji> Ваши активные сессии:</b>\n",
        "separator": "—" * 20 + "\n",
    }

    async def devicescmd(self, message):
        """
        Показывает активные сессии и зарегистрированные устройства на аккаунте.
        """
        await message.edit(self.strings("fetching_message", message))
        try:
            devices = await self.client(functions.account.GetAuthorizationsRequest())

            if not devices.authorizations:
                await message.edit(self.strings("no_devices", message))
                return

            response_parts = [self.strings("header", message)]

            for i, device in enumerate(devices.authorizations):
                date_created = device.date_created.strftime("%Y-%m-%d %H:%M:%S")
                date_active = device.date_active.strftime("%Y-%m-%d %H:%M:%S")

                current_session_marker = ""
                if device.current:
                    current_session_marker = self.strings("current_session_marker", message)

                response_parts.append(
                    self.strings("device_info", message).format(
                        device_model=utils.escape_html(device.device_model or "Неизвестно"),
                        platform=utils.escape_html(device.platform or "Неизвестно"),
                        system_version=utils.escape_html(device.system_version or "Неизвестно"),
                        app_name=utils.escape_html(device.app_name or "Неизвестно"),
                        app_version=utils.escape_html(device.app_version or "Неизвестно"),
                        ip=utils.escape_html(device.ip or "Неизвестно"),
                        country=utils.escape_html(device.country or "Неизвестно"),
                        region=utils.escape_html(device.region or "Неизвестно"),
                        date_created=date_created,
                        date_active=date_active,
                        current_session=current_session_marker,
                    )
                )
                if i < len(devices.authorizations) - 1:
                    response_parts.append(self.strings("separator", message))

            await message.edit("\n".join(response_parts))

        except Exception as e:
            await message.edit(self.strings("error_fetching", message) + f" <code>{utils.escape_html(str(e))}</code>")