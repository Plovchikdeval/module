# meta developer: @yourhandle
# meta name: Менеджер Папок
# meta version: 1.5

import logging
from typing import Union

from telethon import types
from telethon.tl import types as tl_types
from telethon.functions.folders import CreateChatFolder, DeleteChatFolder, UpdateChatFolder
from telethon.tl.functions.account import GetChatFolders # GetChatFolders находится в telethon.tl.functions.account

from .. import loader, utils

logger = logging.getLogger(__name__)


# Определяем объединяющий тип для InputPeer
InputPeerType = Union[tl_types.InputPeerUser, tl_types.InputPeerChat, tl_types.InputPeerChannel]


@loader.tds
class FolderManagerMod(loader.Module):
    """
    Модуль для управления папками чатов в Telegram.
    Позволяет создавать, удалять, просматривать папки, а также добавлять и удалять чаты из папок.
    """

    def __init__(self):
        self.config = loader.ModuleConfig(
            {
                "default_handle": "@yourhandle",
            }
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def _get_folder_by_title(self, title: str) -> Union[types.Folder, None]:
        """Вспомогательная функция для получения объекта папки по ее названию."""
        folders_obj = await self.client(GetChatFolders()) # GetChatFolders возвращает объект Folders
        for folder in folders_obj.folders: # Итерируем по списку папок внутри объекта Folders
            # Учитываем только папки, созданные пользователем (id > 0)
            # и объекты типа Folder (не FolderPeer)
            if isinstance(folder, types.Folder) and folder.title == title and folder.id > 0:
                return folder
        return None

    async def _resolve_chat_entity(self, message, arg_string: str) -> Union[types.User, types.Chat, types.Channel, None]:
        """
        Вспомогательная функция для получения сущности чата из строки, ответа на сообщение
        или из текущего чата, если команда была отправлена в нем.
        """
        if arg_string:
            try:
                return await self.client.get_entity(arg_string)
            except ValueError:
                return None
        
        # Если arg_string не указан, пытаемся получить сущность из ответа на сообщение
        if message.is_reply:
            reply_msg = await message.get_reply_message()
            if reply_msg and reply_msg.peer_id:
                try:
                    return await self.client.get_entity(reply_msg.peer_id)
                except ValueError:
                    return None
        
        # Если arg_string не указан и нет ответа, пытаемся использовать текущий чат
        if message.chat: # Упрощенное условие
            try:
                return await self.client.get_entity(message.chat.id)
            except ValueError: # Исправлено: `except` должен быть после `try`
                return None
                
        return None

    def _is_peer_in_input_peers(self, target_peer_input: InputPeerType, peer_list: list[InputPeerType]) -> bool:
        """Вспомогательная функция для проверки наличия InputPeer в списке InputPeer объектов.
        Сравнивает по ID и типу, игнорируя access_hash для InputPeerUser/InputPeerChannel."""
        for p in peer_list:
            if isinstance(target_peer_input, tl_types.InputPeerUser) and isinstance(p, tl_types.InputPeerUser) and p.user_id == target_peer_input.user_id:
                return True
            elif isinstance(target_peer_input, tl_types.InputPeerChat) and isinstance(p, tl_types.InputPeerChat) and p.chat_id == target_peer_input.chat_id:
                return True
            elif isinstance(target_peer_input, tl_types.InputPeerChannel) and isinstance(p, tl_types.InputPeerChannel) and p.channel_id == target_peer_input.channel_id:
                return True
        return False

    def _remove_peer_from_input_peers(self, target_peer_input: InputPeerType, peer_list: list[InputPeerType]) -> tuple[list[InputPeerType], bool]:
        """Вспомогательная функция для удаления InputPeer из списка InputPeer объектов.
        Возвращает новый список и флаг, указывающий, был ли элемент удален."""
        new_list = []
        removed = False
        for p in peer_list:
            is_match = False
            if isinstance(target_peer_input, tl_types.InputPeerUser) and isinstance(p, tl_types.InputPeerUser) and p.user_id == target_peer_input.user_id:
                is_match = True
            elif isinstance(target_peer_input, tl_types.InputPeerChat) and isinstance(p, tl_types.InputPeerChat) and p.chat_id == target_peer_input.chat_id:
                is_match = True
            elif isinstance(target_peer_input, tl_types.InputPeerChannel) and isinstance(p, tl_types.InputPeerChannel) and p.channel_id == target_peer_input.channel_id:
                is_match = True
            
            if is_match:
                removed = True
            else:
                new_list.append(p)
        return new_list, removed

    async def mkfoldercmd(self, message):
        """
        Создает новую папку чатов.
        Использование: .mkfolder <Название папки>
        """
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Укажите название для папки.")
            return

        title = args

        try:
            await self.client(CreateChatFolder( # Используем напрямую импортированную функцию
                title=title,
                autofill_new_chats=False,
                peers=[], # Правильный аргумент для начальных чатов, пустой для новой папки
                order=0
            ))
            await message.edit(f"<emoji document_id=5825794181183836432>✔️</emoji> Папка <b>'{utils.escape_html(title)}'</b> успешно создана.")
        except Exception as e:
            logger.error("Ошибка при создании папки:", exc_info=True)
            await message.edit(f"<emoji document_id=5778527486270770928>❌</emoji> Ошибка при создании папки: <code>{utils.escape_html(str(e))}</code>")

    async def rmfoldercmd(self, message):
        """
        Удаляет папку чатов по названию.
        ВНИМАНИЕ: Все чаты из удаляемой папки будут перемещены в "Все чаты" или "Архив", если они там были.
        Использование: .rmfolder <Название папки>
        """
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Укажите название папки для удаления.")
            return

        folder_title = args
        folder_to_delete = await self._get_folder_by_title(folder_title)

        if not folder_to_delete:
            await message.edit(f"<emoji document_id=5879813604068298387>❗️</emoji> Папка с названием <b>'{utils.escape_html(folder_title)}'</b> не найдена или является системной.")
            return

        try:
            await self.client(DeleteChatFolder(folder_id=folder_to_delete.id)) # Используем напрямую импортированную функцию
            await message.edit(f"<emoji document_id=5825794181183836432>✔️</emoji> Папка <b>'{utils.escape_html(folder_title)}'</b> успешно удалена.")
        except Exception as e:
            logger.error("Ошибка при удалении папки:", exc_info=True)
            await message.edit(f"<emoji document_id=5778527486270770928>❌</emoji> Ошибка при удалении папки: <code>{utils.escape_html(str(e))}</code>")

    async def lsfolderscmd(self, message):
        """
        Показывает список всех ваших папок чатов.
        Использование: .lsfolders
        """
        try:
            folders_obj = await self.client(GetChatFolders()) # GetChatFolders возвращает объект Folders
            
            # Фильтруем только пользовательские папки (id > 0)
            user_folders = [folder for folder in folders_obj.folders if isinstance(folder, types.Folder) and folder.id > 0] # Итерируем по списку папок внутри объекта Folders

            if not user_folders:
                await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> У вас нет созданных пользовательских папок чатов.")
                return

            response = "<emoji document_id=5877316724830768997>🗃</emoji> <b>Ваши пользовательские папки чатов:</b>\n\n"
            for i, folder in enumerate(user_folders):
                response += f"  <emoji document_id=5843862283964390528>🔖</emoji> <b>{utils.escape_html(folder.title)}</b> (ID: <code>{folder.id}</code>)\n"

            await message.edit(response)
        except Exception as e:
            logger.error("Ошибка при получении списка папок:", exc_info=True)
            await message.edit(f"<emoji document_id=5778527486270770928>❌</emoji> Ошибка при получении списка папок: <code>{utils.escape_html(str(e))}</code>")

    async def addchattofoldercmd(self, message):
        """
        <emoji document_id=5877219383691972108>➕</emoji> Добавляет чат в существующую папку.
        Использование: .addchattofolder <Название папки> [ID/юзернейм чата или реплай]
        Если ID/юзернейм не указаны, будет использован чат, в котором была написана команда.
        """
        args = utils.get_args_raw(message).split(maxsplit=1)
        folder_title = args[0] if args else None
        chat_entity_str = args[1] if len(args) > 1 else None

        if not folder_title:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Укажите название папки.")
            return
        
        # Проверяем, есть ли способ определить целевой чат
        if not chat_entity_str and not message.is_reply and not message.chat:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Укажите чат для добавления (ID, юзернейм, ответьте на сообщение или отправьте команду в целевом чате).")
            return

        folder_to_update = await self._get_folder_by_title(folder_title)
        if not folder_to_update:
            await message.edit(f"<emoji document_id=5879813604068298387>❗️</emoji> Папка с названием <b>'{utils.escape_html(folder_title)}'</b> не найдена.")
            return

        chat_entity = await self._resolve_chat_entity(message, chat_entity_str)
        if not chat_entity:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Не удалось найти указанный чат или получить его из ответа/текущего чата.")
            return

        input_peer = await self.client.get_input_entity(chat_entity)

        if self._is_peer_in_input_peers(input_peer, folder_to_update.pinned_peers) or \
           self._is_peer_in_input_peers(input_peer, folder_to_update.unpinned_peers):
            await message.edit(f"<emoji document_id=5879813604068298387>❗️</emoji> Чат <b>'{utils.escape_html(utils.get_display_name(chat_entity))}'</b> уже находится в папке <b>'{utils.escape_html(folder_title)}'</b>.")
            return

        # Создаем копию списка unpinned_peers и добавляем в нее новый чат
        updated_unpinned_peers = list(folder_to_update.unpinned_peers)
        updated_unpinned_peers.append(input_peer)

        try:
            await self.client(UpdateChatFolder( # Используем напрямую импортированную функцию
                folder_id=folder_to_update.id,
                title=folder_to_update.title,
                autofill_new_chats=folder_to_update.autofill_new_chats,
                pinned_peers=list(folder_to_update.pinned_peers),  # Передаем копию текущих закрепленных
                unpinned_peers=updated_unpinned_peers,             # Передаем обновленный список незакрепленных
                order=folder_to_update.order
            ))
            await message.edit(f"<emoji document_id=5825794181183836432>✔️</emoji> Чат <b>'{utils.escape_html(utils.get_display_name(chat_entity))}'</b> успешно добавлен в папку <b>'{utils.escape_html(folder_title)}'</b>.")
        except Exception as e:
            logger.error("Ошибка при добавлении чата в папку:", exc_info=True)
            await message.edit(f"<emoji document_id=5778527486270770928>❌</emoji> Ошибка при добавлении чата в папку: <code>{utils.escape_html(str(e))}</code>")

    async def rmchatfromfoldercmd(self, message):
        """
        <emoji document_id=5879896690210639947>🗑</emoji> Удаляет чат из существующей папки.
        Использование: .rmchatfromfolder <Название папки> [ID/юзернейм чата или реплай]
        Если ID/юзернейм не указаны, будет использован чат, в котором была написана команда.
        """
        args = utils.get_args_raw(message).split(maxsplit=1)
        folder_title = args[0] if args else None
        chat_entity_str = args[1] if len(args) > 1 else None

        if not folder_title:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Укажите название папки.")
            return
        
        # Проверяем, есть ли способ определить целевой чат
        if not chat_entity_str and not message.is_reply and not message.chat:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Укажите чат для удаления (ID, юзернейм, ответьте на сообщение или отправьте команду в целевом чате).")
            return

        folder_to_update = await self._get_folder_by_title(folder_title)
        if not folder_to_update:
            await message.edit(f"<emoji document_id=5879813604068298387>❗️</emoji> Папка с названием <b>'{utils.escape_html(folder_title)}'</b> не найдена.")
            return

        chat_entity = await self._resolve_chat_entity(message, chat_entity_str)
        if not chat_entity:
            await message.edit("<emoji document_id=5879813604068298387>❗️</emoji> Не удалось найти указанный чат или получить его из ответа/текущего чата.")
            return

        input_peer = await self.client.get_input_entity(chat_entity)

        # Удаляем чат из обоих списков (pinned и unpinned), если он там есть
        updated_pinned_peers, removed_from_pinned = self._remove_peer_from_input_peers(input_peer, folder_to_update.pinned_peers)
        updated_unpinned_peers, removed_from_unpinned = self._remove_peer_from_input_peers(input_peer, folder_to_update.unpinned_peers)

        if not removed_from_pinned and not removed_from_unpinned:
            await message.edit(f"<emoji document_id=5879813604068298387>❗️</emoji> Чат <b>'{utils.escape_html(utils.get_display_name(chat_entity))}'</b> не найден в папке <b>'{utils.escape_html(folder_title)}'</b>.")
            return

        try:
            await self.client(UpdateChatFolder( # Используем напрямую импортированную функцию
                folder_id=folder_to_update.id,
                title=folder_to_update.title,
                autofill_new_chats=folder_to_update.autofill_new_chats,
                pinned_peers=updated_pinned_peers,
                unpinned_peers=updated_unpinned_peers,
                order=folder_to_update.order
            ))
            await message.edit(f"<emoji document_id=5825794181183836432>✔️</emoji> Чат <b>'{utils.escape_html(utils.get_display_name(chat_entity))}'</b> успешно удален из папки <b>'{utils.escape_html(folder_title)}'</b>.")
        except Exception as e:
            logger.error("Ошибка при удалении чата из папки:", exc_info=True)
            await message.edit(f"<emoji document_id=5778527486270770928>❌</emoji> Ошибка при удалении чата из папки: <code>{utils.escape_html(str(e))}</code>")
