# meta developer: @Androfon_AI
# meta name: Шашки
# meta version: 1.2.0 # Обновляем версию после добавления нового функционала

import asyncio, html, random
from .. import loader, utils

EMPTY = 0
WHITE_MAN = 1
BLACK_MAN = 2
WHITE_KING = 3
BLACK_KING = 4

PIECE_EMOJIS = {
    EMPTY: ".",
    "light": " ",
    WHITE_MAN: "⚪",
    BLACK_MAN: "⚫",
    WHITE_KING: "🌝",
    BLACK_KING: "🌚",
    'selected': "🔘",
    'move_target': "🟢",
    'capture_target': "🔴",
}

class CheckersBoard:
    def __init__(self, mandatory_captures_enabled=True):
        self._board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self._setup_initial_pieces()
        self.current_player = "white"
        self.mandatory_capture_from_pos = None # Позиция, с которой ОБЯЗАТЕЛЕН следующий захват (для мульти-прыжка)
        self.mandatory_captures_enabled = mandatory_captures_enabled # Глобальная настройка обязательных взятий

    def _setup_initial_pieces(self):
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 != 0: # Только по темным клеткам
                    if r < 3:
                        self._board[r][c] = BLACK_MAN
                    elif r > 4:
                        self._board[r][c] = WHITE_MAN

    def _is_valid_coord(self, r, c):
        return 0 <= r < 8 and 0 <= c < 8

    def get_piece_at(self, r, c):
        if not self._is_valid_coord(r, c):
            return None
        return self._board[r][c]

    def _set_piece_at(self, r, c, piece):
        if self._is_valid_coord(r, c):
            self._board[r][c] = piece

    def _get_player_color(self, piece):
        if piece in [WHITE_MAN, WHITE_KING]:
            return "white"
        if piece in [BLACK_MAN, BLACK_KING]:
            return "black"
        return None

    def _get_opponent_color(self, color):
        return "black" if color == "white" else "white"

    def _get_moves_for_piece(self, r, c):
        moves = [] # Список кортежей: (start_r, start_c, end_r, end_c, is_capture)
        piece = self.get_piece_at(r, c)
        player_color = self._get_player_color(piece)
        opponent_color = self._get_opponent_color(player_color)

        if piece == EMPTY:
            return []

        all_diagonal_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        if piece in [WHITE_MAN, BLACK_MAN]:
            regular_move_directions = []
            if piece == WHITE_MAN:
                regular_move_directions = [(-1, -1), (-1, 1)]
            elif piece == BLACK_MAN:
                regular_move_directions = [(1, -1), (1, 1)]

            # Обычные ходы для шашек
            for dr, dc in regular_move_directions:
                new_r, new_c = r + dr, c + dc
                if self._is_valid_coord(new_r, new_c) and self.get_piece_at(new_r, new_c) == EMPTY:
                    moves.append((r, c, new_r, new_c, False)) # False = не захват

            # Ходы с захватом для шашек
            for dr, dc in all_diagonal_directions:
                captured_piece_r, captured_piece_c = r + dr, c + dc
                jump_r, jump_c = r + 2 * dr, c + 2 * dc
                
                captured_piece = self.get_piece_at(captured_piece_r, captured_piece_c)

                if (self._is_valid_coord(jump_r, jump_c) and
                    self.get_piece_at(jump_r, jump_c) == EMPTY and
                    self._get_player_color(captured_piece) == opponent_color):
                    
                    moves.append((r, c, jump_r, jump_c, True)) # True = захват

        elif piece in [WHITE_KING, BLACK_KING]:
            for dr, dc in all_diagonal_directions:
                current_r, current_c = r + dr, c + dc
                captured_piece_pos = None # Хранит позицию (r,c) первой захваченной фигуры

                while self._is_valid_coord(current_r, current_c):
                    piece_on_path = self.get_piece_at(current_r, current_c)
                    piece_on_path_color = self._get_player_color(piece_on_path)

                    if piece_on_path == EMPTY:
                        if captured_piece_pos is None:
                            # Обычный ход для дамки (скольжение по пустым клеткам)
                            moves.append((r, c, current_r, current_c, False))
                        else:
                            # Клетка для приземления после захвата
                            moves.append((r, c, current_r, current_c, True)) # Это захват
                    elif piece_on_path_color == player_color:
                        # Заблокировано своей фигурой
                        break
                    elif piece_on_path_color == opponent_color:
                        if captured_piece_pos is None:
                            # Нашли первую фигуру противника для захвата
                            captured_piece_pos = (current_r, current_c)
                            # Продолжаем в этом направлении, чтобы найти места для приземления
                        else:
                            # Уже захватили фигуру на этой линии, нельзя захватить еще одну за один прыжок
                            break # Дамка не может перепрыгивать через две фигуры подряд
                    
                    current_r += dr
                    current_c += dc
        return moves

    def get_all_possible_moves(self, player_color):
        all_moves = [] # Обычные ходы
        all_captures = [] # Ходы с захватом

        # Если есть обязательный захват из конкретной позиции (для мульти-прыжка), он всегда обязателен
        if self.mandatory_capture_from_pos:
            r, c = self.mandatory_capture_from_pos
            # Возвращаем только захваты из этой конкретной позиции
            # Важно: _get_moves_for_piece(r,c) уже вернет только те ходы, которые возможны для данной фигуры.
            return [m for m in self._get_moves_for_piece(r, c) if m[4]]
            
        for r in range(8):
            for c in range(8):
                piece = self.get_piece_at(r, c)
                if self._get_player_color(piece) == player_color:
                    moves_for_piece = self._get_moves_for_piece(r, c)
                    for move in moves_for_piece:
                        if move[4]: # Если это захват
                            all_captures.append(move)
                        else:
                            all_moves.append(move)
        
        # Если обязательные взятия включены И есть хоть один возможный захват, они обязательны
        if self.mandatory_captures_enabled and all_captures: 
            return all_captures # Возвращаем только захваты
        
        # Иначе возвращаем все доступные ходы (обычные + захваты, если они есть, но не обязательны)
        return all_moves + all_captures

    def _execute_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        piece = self.get_piece_at(start_r, start_c)
        self._set_piece_at(end_r, end_c, piece)
        self._set_piece_at(start_r, start_c, EMPTY)

        if is_capture_move:
            # Вычисляем направление хода
            dr_diff = end_r - start_r
            dc_diff = end_c - start_c
            
            # Нормализуем направление для получения единичных шагов
            dr_norm = 0
            if dr_diff != 0:
                dr_norm = dr_diff // abs(dr_diff)
            
            dc_norm = 0
            if dc_diff != 0:
                dc_norm = dc_diff // abs(dc_diff)

            # Итерируем по пути, чтобы найти и удалить захваченную фигуру
            # Начинаем с клетки СРАЗУ ПОСЛЕ стартовой позиции
            current_r, current_c = start_r + dr_norm, start_c + dc_norm
            while self._is_valid_coord(current_r, current_c) and (current_r, current_c) != (end_r, end_c):
                if self.get_piece_at(current_r, current_c) != EMPTY:
                    # Найдена захваченная фигура
                    self._set_piece_at(current_r, current_c, EMPTY)
                    break # За один прыжок захватывается только одна фигура
                current_r += dr_norm
                current_c += dc_norm
        
        # Возвращаем информацию, был ли захват
        return is_capture_move

    def make_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        # piece_before_move = self.get_piece_at(start_r, start_c) # Эта переменная не используется, можно удалить

        self._execute_move(start_r, start_c, end_r, end_c, is_capture_move)
        
        # Проверяем и выполняем превращение в дамку
        # Важно: превращение происходит сразу после хода, и если шашка становится дамкой,
        # дальнейшие захваты (если есть) она будет выполнять уже как дамка.
        piece_after_move = self.get_piece_at(end_r, end_c) # Получаем фигуру на новой позиции
        if piece_after_move == WHITE_MAN and end_r == 0:
            self._set_piece_at(end_r, end_c, WHITE_KING)
            piece_after_move = WHITE_KING # Обновляем тип фигуры для дальнейших проверок
        elif piece_after_move == BLACK_MAN and end_r == 7:
            self._set_piece_at(end_r, end_c, BLACK_KING)
            piece_after_move = BLACK_KING # Обновляем тип фигуры

        if is_capture_move:
            # Проверяем, возможны ли дальнейшие захваты с новой позиции (мульти-прыжок)
            # При этом используем piece_after_move, чтобы учесть превращение в дамку
            self.mandatory_capture_from_pos = (end_r, end_c) # Временно устанавливаем, чтобы _get_moves_for_piece работала корректно
            further_captures = [m for m in self._get_moves_for_piece(end_r, end_c) if m[4]]
            
            if further_captures:
                # Если возможны дальнейшие захваты, фигура остается выбранной, и ход не переходит
                return True # Возвращаем True, если возможны дальнейшие захваты
            else:
                # Захваты закончились, сбрасываем обязательный захват и переключаем ход
                self.mandatory_capture_from_pos = None
                self.switch_turn()
                return False # Захваты закончились, ход переходит
        else:
            # Обычный ход, сбрасываем обязательный захват (если был) и переключаем ход
            self.mandatory_capture_from_pos = None
            self.switch_turn()
            return False # Обычный ход, ход переходит

    def switch_turn(self):
        self.current_player = self._get_opponent_color(self.current_player)

    def is_game_over(self):
        white_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "white")
        black_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "black")

        if white_pieces == 0:
            return "Победа черных"
        if black_pieces == 0:
            return "Победа белых"
        
        # Проверяем, есть ли у *текущего* игрока доступные ходы
        # Если get_all_possible_moves возвращает пустой список, значит ходов нет.
        if not self.get_all_possible_moves(self.current_player):
            if self.current_player == "white":
                return "Победа черных (нет ходов у белых)"
            else:
                return "Победа белых (нет ходов у черных)"

        return None

    def to_list_of_emojis(self, selected_pos=None, possible_moves_with_info=None):
        board_emojis = []
        possible_moves_with_info = possible_moves_with_info if possible_moves_with_info else []
        
        # Создаем карту целевых клеток для быстрых проверок
        # move_info is (end_r, end_c, is_capture)
        possible_move_targets_map = {(move_info[0], move_info[1]): move_info[2] for move_info in possible_moves_with_info}

        for r in range(8):
            row_emojis = []
            for c in range(8):
                piece = self.get_piece_at(r, c)
                
                # Базовый эмодзи для клетки
                # Если клетка светлая, используем эмодзи светлой клетки.
                # Если темная, используем эмодзи фигуры или пустого места.
                current_cell_emoji = PIECE_EMOJIS['light'] if (r + c) % 2 == 0 else PIECE_EMOJIS[piece]
                
                # Переопределяем, если клетка выбрана или является целью хода
                if (r, c) == selected_pos:
                    current_cell_emoji = PIECE_EMOJIS['selected']
                elif (r, c) in possible_move_targets_map:
                    is_capture_move = possible_move_targets_map[(r, c)]
                    current_cell_emoji = PIECE_EMOJIS['capture_target'] if is_capture_move else PIECE_EMOJIS['move_target']
                
                row_emojis.append(current_cell_emoji)
            board_emojis.append(row_emojis)
        return board_emojis
    
    def get_valid_moves_for_selection(self, current_r, current_c):
        piece = self.get_piece_at(current_r, current_c)
        if self._get_player_color(piece) != self.current_player:
            return [] # Нельзя выбрать чужую фигуру или пустую клетку

        piece_moves_full_info = self._get_moves_for_piece(current_r, current_c)
        
        all_game_moves_full_info = self.get_all_possible_moves(self.current_player)
        # all_game_moves_full_info уже учитывает обязательные взятия,
        # так что нам не нужно отдельно фильтровать all_game_captures_full_info.
        
        valid_moves_for_selection = []

        # Если есть обязательный захват из конкретной позиции (мульти-прыжок)
        if self.mandatory_capture_from_pos:
            if (current_r, current_c) == self.mandatory_capture_from_pos:
                # Для выбранной фигуры доступны только ее захваты
                valid_moves_for_selection = [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap]
            else:
                # Выбрана не та фигура, которая должна делать мульти-прыжок
                valid_moves_for_selection = []
        else:
            # В других случаях, фильтруем ходы выбранной фигуры, чтобы они были среди всех разрешенных ходов для игрока
            # (которые уже учли mandatory_captures_enabled).
            for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info:
                if (s_r, s_c, e_r, e_c, is_cap) in all_game_moves_full_info:
                    valid_moves_for_selection.append((e_r, e_c, is_cap))

        return valid_moves_for_selection


@loader.tds
class Checkers(loader.Module):
    """Шашки для игры вдвоём."""
    strings = {
        "name": "Шашки"
    }

    async def client_ready(self):
        # Инициализация переменных состояния игры при загрузке/перезагрузке модуля
        # self.db уже доступен как атрибут от loader.Module, поэтому self.db = self.get_db() не требуется.
        await self.purgeSelf() # Очистка состояния при запуске модуля

    async def purgeSelf(self):
        """Сбрасывает все переменные состояния игры."""
        self._board_obj = None
        self._game_message = None # Изначальное сообщение с командой, которое может быть отредактировано в инлайн-форму.
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.colorName = "рандом" # Отображаемое имя цвета хоста
        self.host_color = None # Фактический цвет хоста (white/black)
        self.game_running = False
        self.game_reason_ended = None # Добавляем поле для причины завершения игры
        self.players_ids = []
        self.host_id = None
        self.opponent_id = None # Может быть None, если игра "любой желающий"
        self.opponent_name = None # Может быть "любой желающий", если игра "любой желающий"
        self.player_white_id = None
        self.player_black_id = None
        self._game_board_call = None # Сохраняем 'call' объект от inline.form/accept_game для редактирования доски
        # Загружаем настройку обязательных взятий из базы данных или используем значение по умолчанию
        self.mandatory_captures_enabled = self.db.get("checkers_module", "mandatory_captures_enabled", True)

    async def settings_menu(self, call):
        # Проверка, что только хост может менять настройки
        if call.from_user.id != self.host_id:
            await call.answer("Только владелец бота может менять настройки этой партии!")
            return  
        
        # Обновляем текст для корректного отображения текущих настроек
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "белый"
        elif self.host_color == "black":
            current_host_color_display = "чёрный"
        else:
            current_host_color_display = "рандом"

        # Формируем текст приглашения, учитывая, есть ли конкретный оппонент или "любой желающий"
        opponent_name_display_for_settings = "любой желающий"
        invite_text_prefix_for_settings = "Вас приглашают сыграть партию в шашки, примите?"
        if self.opponent_id: # Если конкретный оппонент уже выбран или изначально указан
            try:
                opponent_entity = await self.client.get_entity(self.opponent_id)
                opponent_name_display_for_settings = html.escape(opponent_entity.first_name)
            except Exception:
                pass # Fallback if entity not found
            invite_text_prefix_for_settings = f"<a href='tg://user?id={self.opponent_id}'>{opponent_name_display_for_settings}</a>, вас пригласили сыграть партию в шашки, примите?"

        await call.edit(
            text=f"{invite_text_prefix_for_settings}\n-- --\n"
                 f"Текущие настройки:\n"
                 f"| - > • Хост играет за {current_host_color_display} цвет\n"
                 f"| - > • Обязательные взятия: {'Включены' if self.mandatory_captures_enabled else 'Отключены'}",
            reply_markup=[
                [
                    {"text":f"Цвет (хоста): {current_host_color_display}","callback":self.set_color}
                ],
                [
                    {"text":f"Обязательные взятия: {'Вкл' if self.mandatory_captures_enabled else 'Выкл'}","callback":self.toggle_mandatory_captures}
                ],
                [
                    {"text":"Вернуться","callback":self.back_to_invite}
                ]
            ]
        )

    async def toggle_mandatory_captures(self, call):
        if call.from_user.id != self.host_id:
            await call.answer("Только владелец бота может менять настройки этой партии!")
            return
        self.mandatory_captures_enabled = not self.mandatory_captures_enabled
        # Сохраняем настройку в базу данных
        self.db.set("checkers_module", "mandatory_captures_enabled", self.mandatory_captures_enabled)
        await self.settings_menu(call)

    async def back_to_invite(self, call):
        # Проверка, что только хост может управлять настройками, даже при возврате
        if call.from_user.id != self.host_id:
            await call.answer("Это не для вас!")
            return
        
        # Обновляем имя оппонента, если оно могло измениться или не было установлено
        opponent_name_display = "любой желающий"
        invite_text_prefix = "Вас приглашают сыграть партию в шашки, примите?"

        if self.opponent_id:
            try:
                opponent_entity = await self.client.get_entity(self.opponent_id)
                opponent_name_display = html.escape(opponent_entity.first_name)
            except Exception:
                pass # Fallback if entity not found
            invite_text_prefix = f"<a href='tg://user?id={self.opponent_id}'>{opponent_name_display}</a>, вас пригласили сыграть партию в шашки, примите?"

        # Обновляем текст для корректного отображения текущих настроек
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "белый"
        elif self.host_color == "black":
            current_host_color_display = "чёрный"
        else:
            current_host_color_display = "рандом"

        await call.edit(
            text=f"{invite_text_prefix}\n-- --\n"
                 f"Текущие настройки:\n"
                 f"| - > • Хост играет за {current_host_color_display} цвет\n"
                 f"| - > • Обязательные взятия: {'Включены' if self.mandatory_captures_enabled else 'Отключены'}",
            reply_markup = [
                [
                    {"text": "Принимаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Нет", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "Изменить настройки", "callback": self.settings_menu}
                ]
            ]
        )

    async def set_color(self, call):
        # Проверка, что только хост может менять настройки
        if call.from_user.id != self.host_id:
            await call.answer("Только владелец бота может менять настройки цвета!")
            return
        
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "белый"
        elif self.host_color == "black":
            current_host_color_display = "чёрный"
        else:
            current_host_color_display = "рандом"

        await call.edit(
            text=f"• Настройки этой партии.\n"
                 f"| - > Хост играет за: {current_host_color_display} цвет.\nВыберите цвет его фигур",
            reply_markup=[
                [
                    {"text":"Белые","callback":self.handle_color_choice,"args":("white","белый",)},
                    {"text":"Чёрные","callback":self.handle_color_choice,"args":("black","чёрный",)}
                ],
                [
                    {"text":"Рандом", "callback":self.handle_color_choice,"args":(None,"рандом")}
                ],
                [
                    {"text":"Обратно к настройкам", "callback":self.settings_menu}
                ]
            ]
        )

    async def handle_color_choice(self, call, color, txt):
        # Проверка, что только хост может менять настройки
        if call.from_user.id != self.host_id:
            await call.answer("Только владелец бота может выбирать цвет!")
            return
        self.colorName = txt
        self.host_color = color
        await self.set_color(call)

    @loader.command() 
    async def checkers(self, message):
        """[reply/username/id] предложить человеку сыграть партию в чате. Без аргументов - любой желающий."""
        if self._board_obj: # Проверяем, не запущена ли уже игра
            await message.edit("Партия уже где-то запущена. Завершите или сбросьте её с <code>.stopgame</code>")
            return
        await self.purgeSelf() # Сбрасываем состояние перед началом новой игры
        self._game_message = message
        self._game_chat_id = message.chat_id
        self.host_id = message.sender_id

        opponent_found = False
        invite_text_prefix = ""

        if message.is_reply:
            r = await message.get_reply_message()
            opponent = r.sender
            self.opponent_id = opponent.id
            self.opponent_name = html.escape(opponent.first_name)
            opponent_found = True
        else:
            args = utils.get_args(message)
            if len(args) > 0:
                opponent_str = args[0]
                try:
                    if opponent_str.isdigit():
                        self.opponent_id = int(opponent_str)
                        opponent = await self.client.get_entity(self.opponent_id)
                        self.opponent_name = html.escape(opponent.first_name)
                    else:
                        opponent = await self.client.get_entity(opponent_str)
                        self.opponent_name = html.escape(opponent.first_name)
                        self.opponent_id = opponent.id
                    opponent_found = True
                except Exception:
                    await message.edit("Я не нахожу такого пользователя")
                    return
            # Если args пустой, opponent_found остается False, self.opponent_id и self.opponent_name остаются None
        
        if opponent_found:
            if self.opponent_id == self._game_message.sender_id:
                await message.edit("Одиночные шашки? Простите, нет.")
                return
            self.players_ids = [self.opponent_id, self._game_message.sender_id]
            invite_text_prefix = f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?"
        else: # Если оппонент не был указан, игра для "любого желающего"
            self.opponent_id = None # Явно устанавливаем None для "любой желающий"
            self.opponent_name = "любой желающий"
            # players_ids пока не заполняем, так как оппонент не определен
            invite_text_prefix = "Вас приглашают сыграть партию в шашки, примите?"
        
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "белый"
        elif self.host_color == "black":
            current_host_color_display = "чёрный"
        else:
            current_host_color_display = "рандом"

        await self.inline.form(
            message = message,
            text = f"{invite_text_prefix}\n-- --\n"
                   f"Текущие настройки:\n"
                   f"| - > • Хост играет за {current_host_color_display} цвет\n"
                   f"| - > • Обязательные взятия: {'Включены' if self.mandatory_captures_enabled else 'Отключены'}",
            reply_markup = [
                [
                    {"text": "Принимаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Нет", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "Изменить настройки", "callback": self.settings_menu}
                ]
            ], 
            disable_security = True,
            on_unload=self.outdated_game
        )

    @loader.command() 
    async def stopgame(self, message):
        """Досрочное завершение партии (для хоста или любого игрока)"""
        # Разрешаем остановку хосту или любому из игроков, если игра уже началась
        # Если игра еще не началась (opponent_id is None), только хост может остановить
        if not self.game_running and self.opponent_id is None: # Игра "любой желающий" еще не началась
            if message.from_user.id != self.host_id:
                await message.edit("Вы не организатор этой партии и не можете её остановить до начала.")
                return
        elif message.from_user.id != self.host_id and message.from_user.id not in self.players_ids:
            await message.edit("Вы не игрок этой партии и не её организатор.")
            return

        if self._game_board_call: # Проверяем, есть ли активная инлайн-форма
            try:
                await self._game_board_call.edit(text="Партия была остановлена.")
            except Exception:
                pass # Игнорируем ошибку, если сообщение уже удалено или недоступно
        elif self._game_message: # Если инлайн-форма не была создана, но есть исходное сообщение
            try:
                await self._game_message.edit(text="Партия была остановлена.")
            except Exception:
                pass
        
        await self.purgeSelf()
        await message.edit("Данные очищены.")
        

    async def accept_game(self, call, data):
        if call.from_user.id == self.host_id:
            if self.opponent_id is None and data == 'n': # Хост отклоняет игру "любой желающий"
                await call.edit(text="Партия отменена.")
                await self.purgeSelf()
                return
            await call.answer("Дай человеку ответить!")
            return
        
        if data == 'y':
            if self.opponent_id is None: # Если игра для "любого желающего" и это первый, кто принял
                self.opponent_id = call.from_user.id
                try:
                    opponent_entity = await self.client.get_entity(self.opponent_id)
                    self.opponent_name = html.escape(opponent_entity.first_name)
                except Exception:
                    self.opponent_name = "Неизвестный игрок"
                await call.answer(f"Вы присоединились к игре как {self.opponent_name}!")
                self.players_ids = [self.opponent_id, self.host_id] # Теперь заполняем players_ids
            elif call.from_user.id != self.opponent_id: # Конкретное приглашение, но принял не тот пользователь
                await call.answer("Не тебе предлагают игру!")
                return
            
            # Если дошли сюда, значит игрок, принявший вызов, является либо назначенным оппонентом,
            # либо первым, кто принял вызов в игре "любой желающий".
            
            self._board_obj = CheckersBoard(mandatory_captures_enabled=self.mandatory_captures_enabled) 
            
            if not self.host_color: # Если хост выбрал "рандом"
                await call.edit(text="Выбираю стороны...")
                await asyncio.sleep(0.5)
                self.host_color = self.ranColor()
            
            if self.host_color == "white":
                self.player_white_id = self.host_id
                self.player_black_id = self.opponent_id
            else: # host_color == "black"
                self.player_white_id = self.opponent_id
                self.player_black_id = self.host_id

            text = await self.get_game_status_text()
            await call.edit(text="Загрузка доски...")
            await asyncio.sleep(0.5)
            
            self.game_running = True
            self._game_board_call = call # Сохраняем объект 'call' для дальнейшего редактирования сообщения
            
            await call.edit(text="Для лучшего различия фигур включите светлую тему!")
            await asyncio.sleep(2.5)
            await self.render_board(text, call)
        else: # data == 'n' (отклонено)
            if self.opponent_id is None: # Если игра "любой желающий", и не хост отклоняет
                await call.answer("Только организатор может отменить игру, к которой может присоединиться любой желающий.")
                return
            elif call.from_user.id != self.opponent_id: # Конкретное приглашение, но отклонил не тот пользователь
                await call.answer("Не тебе предлагают игру!")
                return
            
            await call.edit(text="Отклонено.")
            await self.purgeSelf()

    async def render_board(self, text, call):
        if not self._board_obj:
            await call.edit(text="Ошибка: Доска игры не инициализирована. Игра завершена.")
            await self.purgeSelf()
            return

        board_emojis = self._board_obj.to_list_of_emojis(self._selected_piece_pos, self._possible_moves_for_selected)
        
        btns = []
        for r in range(8):
            row_btns = []
            for c in range(8):
                row_btns.append({"text": board_emojis[r][c], "callback": self.handle_click, "args":(r, c,)})
            btns.append(row_btns)

        # Добавлена кнопка "Сдаться"
        btns.append([{"text": "Сдаться", "callback": self.surrender_game}])

        await call.edit(
            text = text,
            reply_markup = btns,
            disable_security = True
        )
    
    async def surrender_game(self, call):
        user_id = call.from_user.id
        
        # Только игроки (белые или черные) могут сдаться.
        # Хост может использовать .stopgame, если он не играет за одну из сторон.
        if user_id not in [self.player_white_id, self.player_black_id]:
            await call.answer("Вы не игрок этой партии и не можете сдаться. Используйте .stopgame для принудительной остановки.")
            return

        surrendering_player_name = "Неизвестный игрок"
        try:
            surrendering_player_entity = await self.client.get_entity(user_id)
            surrendering_player_name = html.escape(surrendering_player_entity.first_name)
        except Exception:
            pass

        winner_id = None
        winner_color_text = ""
        if user_id == self.player_white_id:
            winner_id = self.player_black_id
            winner_color_text = "черных"
        elif user_id == self.player_black_id:
            winner_id = self.player_white_id
            winner_color_text = "белых"
        
        winner_name = "Оппонент"
        if winner_id:
            try:
                winner_entity = await self.client.get_entity(winner_id)
                winner_name = html.escape(winner_entity.first_name)
            except Exception:
                pass

        surrender_message = (
            f"Партия завершена: <a href='tg://user?id={user_id}'>{surrendering_player_name}</a> сдался(лась).\n"
            f"Победил(а) <a href='tg://user?id={winner_id}'>{winner_name}</a> ({winner_color_text})!"
        )

        self.game_running = False
        self.game_reason_ended = surrender_message # Сохраняем причину завершения игры
        
        await call.edit(surrender_message)
        await self.purgeSelf() # Очищаем состояние после завершения игры
        
    async def handle_click(self, call, r, c):
        # 1. Проверка на завершение игры в самом начале
        # Это предотвращает любые действия, если игра уже завершена, но сообщение еще активно.
        if not self._board_obj or not self.game_running:
            # Если _board_obj None, игра неактивна. Если game_running False, игра завершена.
            await call.answer("Игра не активна или завершена. Начните новую игру.")
            if self._board_obj: # Если _board_obj существует, но game_running False, значит игра завершилась, но состояние не очищено.
                await self.purgeSelf() # Гарантируем очистку, если состояние некорректно
            return

        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            if self.game_running: # Если игра была активна, но только что завершилась
                self.game_running = False
                self.game_reason_ended = game_over_status # Сохраняем причину
                await self.render_board(await self.get_game_status_text(), call) # Обновляем доску в последний раз с финальным статусом
                await self.purgeSelf() # ВАЖНО: Очищаем состояние ПОСЛЕ финального рендера
            await call.answer(f"Партия окончена: {game_over_status}. Для новой игры используйте .checkers")
            return # Выходим, так как игра завершена
        
        # 2. Проверки на принадлежность игрока и текущий ход
        if call.from_user.id not in self.players_ids: 
            await call.answer("Партия не ваша!")
            return
        
        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        if call.from_user.id != current_player_id:
            await call.answer("Сейчас ход оппонента!")
            return

        piece_at_click = self._board_obj.get_piece_at(r, c)
        player_color_at_click = self._board_obj._get_player_color(piece_at_click)

        if self._selected_piece_pos is None:
            # Сценарий 1: Выбор фигуры
            if player_color_at_click == self._board_obj.current_player:
                # Проверка на обязательный мульти-захват
                if self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_from_pos != (r, c):
                    await call.answer("Вы должны продолжить захват с предыдущей позиции!")
                    return

                possible_moves_with_info = self._board_obj.get_valid_moves_for_selection(r, c)
                
                if possible_moves_with_info:
                    self._selected_piece_pos = (r, c)
                    self._possible_moves_for_selected = possible_moves_with_info
                    await call.answer("Шашка выбрана. Выберите куда ходить.")
                    await self.render_board(await self.get_game_status_text(), call)
                else:
                    await call.answer("Для этой шашки нет доступных ходов (включая обязательные захваты)!")
            else:
                await call.answer("Тут нет вашей шашки или это светлая клетка!")
        else:
            # Сценарий 2: Попытка хода или отмена выбора
            start_r, start_c = self._selected_piece_pos
            
            if (r, c) == (start_r, start_c):
                # Отмена выбора текущей фигуры
                self._selected_piece_pos = None
                self._possible_moves_for_selected = []
                await call.answer("Выбор отменен.")
                await self.render_board(await self.get_game_status_text(), call)
                return

            # Ищем, является ли выбранная клетка допустимой целью для хода
            target_move_info = None
            for move_info in self._possible_moves_for_selected:
                if (move_info[0], move_info[1]) == (r, c):
                    target_move_info = move_info
                    break

            if target_move_info:
                # Выполняем ход
                end_r, end_c, is_capture_move = target_move_info
                made_capture_and_can_jump_again = self._board_obj.make_move(start_r, start_c, end_r, end_c, is_capture_move)
                
                if made_capture_and_can_jump_again:
                    # Если был захват и можно сделать еще один (мульти-прыжок), фигура остается выбранной
                    self._selected_piece_pos = (end_r, end_c)
                    self._possible_moves_for_selected = self._board_obj.get_valid_moves_for_selection(end_r, end_c)
                    await call.answer("Захват! Сделайте следующий захват.")
                else:
                    # Ход завершен, сбрасываем выбор
                    self._selected_piece_pos = None
                    self._possible_moves_for_selected = []
                    await call.answer("Ход сделан.")
                
                # Проверяем, не закончилась ли игра после хода
                game_over_status_after_move = self._board_obj.is_game_over()
                if game_over_status_after_move:
                    self.game_running = False
                    self.game_reason_ended = game_over_status_after_move # Сохраняем причину
                    await call.answer(f"Партия окончена: {game_over_status_after_move}")
                    await self.render_board(await self.get_game_status_text(), call) # Обновляем доску с финальным статусом
                    await self.purgeSelf() # Очищаем данные ПОСЛЕ окончания игры
                    return
                
                await self.render_board(await self.get_game_status_text(), call)
            else:
                # Если выбранная клетка не является целью для хода, возможно, игрок хочет выбрать другую свою шашку
                if player_color_at_click == self._board_obj.current_player:
                    # Проверка на обязательный мульти-захват
                    if self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_from_pos != (r, c):
                        await call.answer("Вы должны продолжить захват с предыдущей позиции!")
                        return
                    
                    possible_moves_with_info = self._board_obj.get_valid_moves_for_selection(r, c)
                    
                    if possible_moves_with_info:
                        self._selected_piece_pos = (r, c)
                        self._possible_moves_for_selected = possible_moves_with_info
                        await call.answer("Выбрана другая шашка.")
                        await self.render_board(await self.get_game_status_text(), call)
                    else:
                        await call.answer("Для этой шашки нет доступных ходов (включая обязательные захваты)!")
                else:
                    await call.answer("Неверный ход или цель не является вашей шашкой!")

    async def get_game_status_text(self):
        # Если доска не инициализирована, возвращаем базовый текст
        if not self._board_obj:
            return "Игра не активна или завершена."

        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            # Если причина завершения уже установлена (например, из-за сдачи), используем ее
            if self.game_reason_ended:
                return self.game_reason_ended
            
            # Иначе формируем сообщение о завершении по правилам
            winner_name = ""
            if "Победа белых" in game_over_status:
                try:
                    winner_name = html.escape((await self.client.get_entity(self.player_white_id)).first_name)
                    return f"Партия окончена: {game_over_status}\n\nПобедил(а) <a href='tg://user?id={self.player_white_id}'>{winner_name}</a> (белые)!"
                except Exception:
                    return f"Партия окончена: {game_over_status}\n\nПобедил(а) Белые!"
            elif "Победа черных" in game_over_status:
                try:
                    winner_name = html.escape((await self.client.get_entity(self.player_black_id)).first_name)
                    return f"Партия окончена: {game_over_status}\n\nПобедил(а) <a href='tg://user?id={self.player_black_id}'>{winner_name}</a> (черные)!"
                except Exception:
                    return f"Партия окончена: {game_over_status}\n\nПобедил(а) Черные!"
            return f"Партия окончена: {game_over_status}"

        white_player_name = "Белые"
        black_player_name = "Чёрные"
        try:
            white_player_entity = await self.client.get_entity(self.player_white_id)
            white_player_name = html.escape(white_player_entity.first_name)
        except Exception:
            pass
        
        try:
            black_player_entity = await self.client.get_entity(self.player_black_id)
            black_player_name = html.escape(black_player_entity.first_name)
        except Exception:
            pass

        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        current_player_name = "Неизвестный игрок"
        try:
            current_player_name_entity = await self.client.get_entity(current_player_id)
            current_player_name = html.escape(current_player_name_entity.first_name)
        except Exception:
            pass
        
        status_text = f"♔ Белые - <a href='tg://user?id={self.player_white_id}'>{white_player_name}</a>\n♚ Чёрные - <a href='tg://user?id={self.player_black_id}'>{black_player_name}</a>\n\n"
        
        if self._board_obj.current_player == "white":
            status_text += f"Ход белых (<a href='tg://user?id={current_player_id}'>{current_player_name}</a>)"
        else:
            status_text += f"Ход чёрных (<a href='tg://user?id={current_player_id}'>{current_player_name}</a>)"
        
        status_text += f"\nОбязательные взятия: {'Включены' if self.mandatory_captures_enabled else 'Отключены'}"

        if self._board_obj.mandatory_capture_from_pos:
            status_text += "\nОбязательный захват!"

        return status_text

    async def outdated_game(self):
        # Эта функция вызывается, когда инлайн-форма становится неактивной (например, бот перезагрузился или сообщение было слишком старым).
        if self.game_running or self._board_obj: # Если игра была запущена или состояние доски существовало
            if self._game_board_call: # Если есть ссылка на инлайн-сообщение
                try:
                    await self._game_board_call.edit(text="Партия устарела из-за отсутствия активности.")
                except Exception:
                    pass # Игнорируем ошибку, если сообщение уже удалено/недоступно
            elif self._game_message: # Если инлайн-форма не была создана, но есть исходное сообщение
                try:
                    await self._game_message.edit(text="Партия устарела из-за отсутствия активности.")
                except Exception:
                    pass
            await self.purgeSelf() # Очищаем состояние игры

    def ranColor(self):
        return "white" if random.randint(1,2) == 1 else "black"
