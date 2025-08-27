# meta developer: @Androfon_AI
# meta name: Checkers
# meta version: 1.0.7
# А вы знали что лощадь может дожить до конца своей жизни?

import asyncio, html, random
from .. import loader, utils

EMPTY = 0
WHITE_MAN = 1
BLACK_MAN = 2
WHITE_KING = 3
BLACK_KING = 4

PIECE_EMOJIS = {
    EMPTY: ".", # Темная пустая клетка
    "light": " ", # Светлая пустая клетка
    WHITE_MAN: "⚪",
    BLACK_MAN: "⚫",
    WHITE_KING: "🌚",
    BLACK_KING: "🌝",
    'selected': "🔘",
    'move_target': "🟢",
    'capture_target': "🔴",
}

class CheckersBoard:
    def __init__(self, mandatory_capture_enabled=True):
        self._board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self._setup_initial_pieces()
        self.current_player = "white"
        self.mandatory_capture_from_pos = None # (r, c) если игрок обязан продолжить захват с этой позиции
        self.mandatory_capture_enabled = mandatory_capture_enabled # Настройка, включен ли обязательный захват

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
        """
        Возвращает список возможных ходов для фигуры в (r, c).
        Каждый ход - это кортеж: (start_r, start_c, end_r, end_c, is_capture_move).
        """
        moves = []
        piece = self.get_piece_at(r, c)
        player_color = self._get_player_color(piece)
        opponent_color = self._get_opponent_color(player_color)

        if piece == EMPTY:
            return []

        all_diagonal_directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        if piece in [WHITE_MAN, BLACK_MAN]:
            regular_move_directions = []
            if piece == WHITE_MAN:
                regular_move_directions = [(-1, -1), (-1, 1)] # Белые ходят вверх
            elif piece == BLACK_MAN:
                regular_move_directions = [(1, -1), (1, 1)] # Черные ходят вниз

            # Обычные ходы для шашек (на одну клетку вперед по диагонали на пустую клетку)
            for dr, dc in regular_move_directions:
                new_r, new_c = r + dr, c + dc
                if self._is_valid_coord(new_r, new_c) and self.get_piece_at(new_r, new_c) == EMPTY:
                    moves.append((r, c, new_r, new_c, False))

            # Ходы с захватом для шашек (через одну фигуру противника на пустую клетку)
            for dr, dc in all_diagonal_directions:
                captured_piece_r, captured_piece_c = r + dr, c + dc
                jump_r, jump_c = r + 2 * dr, c + 2 * dc
                
                captured_piece = self.get_piece_at(captured_piece_r, captured_piece_c)

                if (self._is_valid_coord(jump_r, jump_c) and
                    self.get_piece_at(jump_r, jump_c) == EMPTY and
                    self._get_player_color(captured_piece) == opponent_color):
                    
                    moves.append((r, c, jump_r, jump_c, True))

        elif piece in [WHITE_KING, BLACK_KING]:
            for dr, dc in all_diagonal_directions:
                # Обычные ходы для королей (скольжение по диагонали на любое количество пустых клеток)
                current_r, current_c = r + dr, c + dc
                while self._is_valid_coord(current_r, current_c) and self.get_piece_at(current_r, current_c) == EMPTY:
                    moves.append((r, c, current_r, current_c, False))
                    current_r += dr
                    current_c += dc

                # Ходы с захватом для королей (захват одной фигуры противника с возможностью приземлиться
                # на любую пустую клетку за ней по той же диагонали)
                temp_r, temp_c = r + dr, c + dc
                found_opponent_piece = False
                while self._is_valid_coord(temp_r, temp_c):
                    piece_on_path = self.get_piece_at(temp_r, temp_c)
                    piece_on_path_color = self._get_player_color(piece_on_path)

                    if piece_on_path_color == player_color:
                        break # Путь заблокирован своей фигурой
                    elif piece_on_path_color == opponent_color:
                        if found_opponent_piece: # Уже нашли одну фигуру противника, нельзя захватить вторую за один ход
                            break
                        found_opponent_piece = True # Отмечаем, что нашли фигуру для захвата
                        # Теперь проверяем пустые клетки *после* этой фигуры противника для приземления
                        jump_r, jump_c = temp_r + dr, temp_c + dc
                        while self._is_valid_coord(jump_r, jump_c) and self.get_piece_at(jump_r, jump_c) == EMPTY:
                            moves.append((r, c, jump_r, jump_c, True))
                            jump_r += dr
                            jump_c += dc
                        # После нахождения фигуры и проверки мест приземления, этот диагональный сегмент
                        # завершен для захватов, так как захватить можно только одну фигуру.
                        break 
                    elif piece_on_path == EMPTY:
                        # Продолжаем поиск фигуры противника для захвата
                        pass
                    
                    temp_r += dr
                    temp_c += dc

        return moves

    def get_all_possible_moves(self, player_color):
        """
        Возвращает все возможные ходы для данного игрока, учитывая правила обязательного захвата.
        """
        all_moves = []
        all_captures = []

        # Если включен обязательный захват и есть позиция для продолжения захвата
        if self.mandatory_capture_from_pos and self.mandatory_capture_enabled:
            r, c = self.mandatory_capture_from_pos
            # Возвращаем только захваты, возможные из этой конкретной позиции
            return [m for m in self._get_moves_for_piece(r, c) if m[4]]
            
        # Иначе ищем все возможные ходы
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
        
        # Логика для обязательного захвата: если есть хоть один возможный захват
        # и опция включена, то игрок обязан сделать захват.
        if all_captures and self.mandatory_capture_enabled:
            return all_captures
        
        # Иначе возвращаем все возможные ходы (обычные и, если обязательный захват выключен, захваты)
        return all_moves

    def _execute_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        """Перемещает фигуру и удаляет захваченную, если это был захват."""
        piece = self.get_piece_at(start_r, start_c)
        self._set_piece_at(end_r, end_c, piece)
        self._set_piece_at(start_r, start_c, EMPTY)

        if is_capture_move:
            # Вычисляем направление хода для удаления захваченной фигуры
            dr_norm = 0
            if end_r != start_r:
                dr_norm = (end_r - start_r) // abs(end_r - start_r)
            
            dc_norm = 0
            if end_c != start_c:
                dc_norm = (end_c - start_c) // abs(end_c - start_c)

            # Итерируем по пути, чтобы найти и удалить захваченную фигуру.
            # Начинаем поиск от клетки, следующей за стартовой позицией.
            current_r, current_c = start_r + dr_norm, start_c + dc_norm
            while self._is_valid_coord(current_r, current_c) and (current_r, current_c) != (end_r, end_c):
                if self.get_piece_at(current_r, current_c) != EMPTY:
                    # Найдена захваченная фигура (должна быть фигурой противника по логике _get_moves_for_piece)
                    self._set_piece_at(current_r, current_c, EMPTY)
                    break # За один прыжок захватывается только одна фигура
                current_r += dr_norm
                current_c += dc_norm
        
        return is_capture_move

    def make_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        """
        Выполняет ход, проверяет превращение в дамки и логику продолжения захвата.
        Возвращает True, если был захват и можно сделать еще один, иначе False.
        """
        piece = self.get_piece_at(start_r, start_c)
        
        self._execute_move(start_r, start_c, end_r, end_c, is_capture_move)
        
        # Превращение в дамки
        if piece == WHITE_MAN and end_r == 0: # Белая шашка дошла до последней горизонтали
            self._set_piece_at(end_r, end_c, WHITE_KING)
        elif piece == BLACK_MAN and end_r == 7: # Черная шашка дошла до последней горизонтали
            self._set_piece_at(end_r, end_c, BLACK_KING)
        
        if is_capture_move:
            if self.mandatory_capture_enabled:
                # Проверяем, возможны ли дальнейшие захваты с новой позиции
                further_captures = [m for m in self._get_moves_for_piece(end_r, end_c) if m[4]]
                if further_captures:
                    self.mandatory_capture_from_pos = (end_r, end_c)
                    return True # Возвращаем True, если возможны дальнейшие захваты (ход не переходит)
                else:
                    self.mandatory_capture_from_pos = None
                    self.switch_turn()
                    return False # Захваты закончились, ход переходит
            else: # Если обязательный захват выключен, ход всегда переходит после любого хода (даже захвата)
                self.mandatory_capture_from_pos = None
                self.switch_turn()
                return False
        else: # Обычный ход
            self.mandatory_capture_from_pos = None
            self.switch_turn()
            return False # Обычный ход, ход переходит

    def switch_turn(self):
        self.current_player = self._get_opponent_color(self.current_player)

    def is_game_over(self):
        """Проверяет условия окончания игры: нет фигур или нет ходов."""
        white_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "white")
        black_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "black")

        if white_pieces == 0:
            return "Победа черных (все белые фигуры захвачены)"
        if black_pieces == 0:
            return "Победа белых (все черные фигуры захвачены)"
        
        # Проверяем, есть ли у игроков доступные ходы
        if not self.get_all_possible_moves("white"):
            return "Победа черных (нет ходов у белых)"
        if not self.get_all_possible_moves("black"):
            return "Победа белых (нет ходов у черных)"

        return None # Игра не окончена

    def to_list_of_emojis(self, selected_pos=None, possible_moves_with_info=None):
        """
        Преобразует текущее состояние доски в список эмодзи для отображения.
        Подсвечивает выбранную фигуру и возможные ходы.
        """
        board_emojis = []
        possible_moves_with_info = possible_moves_with_info if possible_moves_with_info else []
        
        # Создаем карту целевых клеток для быстрых проверок: {(end_r, end_c): is_capture_move}
        possible_move_targets_map = {(move_info[0], move_info[1]): move_info[2] for move_info in possible_moves_with_info}

        for r in range(8):
            row_emojis = []
            for c in range(8):
                piece = self.get_piece_at(r, c)
                emoji = PIECE_EMOJIS[piece] # Эмодзи фигуры или темной пустой клетки

                if (r, c) == selected_pos:
                    emoji = PIECE_EMOJIS['selected']
                elif (r, c) in possible_move_targets_map:
                    is_capture_move = possible_move_targets_map[(r, c)]
                    emoji = PIECE_EMOJIS['capture_target'] if is_capture_move else PIECE_EMOJIS['move_target']
                elif (r + c) % 2 == 0: # Светлые клетки
                    emoji = PIECE_EMOJIS['light'] # Если это светлая клетка и не выбрана/не цель
                
                row_emojis.append(emoji)
            board_emojis.append(row_emojis)
        return board_emojis
    
    def get_valid_moves_for_selection(self, current_r, current_c):
        """
        Возвращает допустимые целевые клетки для выбранной фигуры (current_r, current_c),
        учитывая правила игры (например, обязательный захват).
        Возвращает список кортежей (end_r, end_c, is_capture_move).
        """
        piece_moves_full_info = self._get_moves_for_piece(current_r, current_c)
        
        all_game_moves_full_info = self.get_all_possible_moves(self.current_player)
        all_game_captures_full_info = [m for m in all_game_moves_full_info if m[4]] # Отфильтровываем только захваты

        # Если включен обязательный захват и есть хотя бы один захват
        if self.mandatory_capture_enabled and all_game_captures_full_info:
            if self.mandatory_capture_from_pos: # Если есть конкретная позиция, с которой нужно продолжить захват
                if (current_r, current_c) == self.mandatory_capture_from_pos:
                    # Разрешены только захваты из этой обязательной позиции
                    return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap]
                else:
                    # Если обязательный захват установлен, но не с этой фигуры, то ходов для этой фигуры нет
                    return []
            else: # Если обязательный захват есть, но не привязан к конкретной фигуре (начало цепочки или первый захват)
                # Возвращаем только захваты для этой фигуры, которые являются частью всех возможных захватов игрока
                return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap and (s_r,s_c,e_r,e_c,is_cap) in all_game_captures_full_info]
        else: # Если обязательный захват выключен или нет доступных захватов
            # Возвращаем все ходы для этой фигуры, которые также являются частью всех возможных ходов для всего игрока.
            return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if (s_r,s_c,e_r,e_c,is_cap) in all_game_moves_full_info]


@loader.tds
class Checkers(loader.Module):
    """Шашки для игры вдвоём."""
    strings = {
        "name": "Шашки"
    }

    async def client_ready(self):
        self._board_obj = None # Объект доски CheckersBoard
        self._game_message = None # Исходное сообщение с командой .checkers
        self._game_chat_id = None # ID чата, где идет игра
        self._selected_piece_pos = None # (r, c) выбранной фигуры
        self._possible_moves_for_selected = [] # Список (end_r, end_c, is_capture_move) для выбранной фигуры
        self.saymyname = html.escape((await self.client.get_me()).first_name)
        self.owner_id = (await self.client.get_me()).id # Сохраняем ID владельца юзербота для настроек
        self.colorName = "рандом" # Отображаемое название цвета хоста
        self.host_color = None # Фактический цвет хоста ("white", "black" или None для рандома)
        self.game_running = False # Флаг активной игры
        self.game_reason_ended = None # Причина завершения игры
        self.players_ids = [] # Список ID обоих игроков
        self.opponent_id = None # ID оппонента
        self.opponent_name = None # Имя оппонента
        self.player_white_id = None # ID игрока, играющего белыми
        self.player_black_id = None # ID игрока, играющего черными
        self._game_board_call = None # Объект call, используемый для редактирования сообщения с доской
        self.mandatory_capture_enabled = True # По умолчанию обязательный захват включен

    async def purgeSelf(self):
        """Сбрасывает все переменные состояния игры."""
        self._board_obj = None
        self._game_message = None
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.colorName = "рандом"
        self.host_color = None
        self.game_running = False
        self.game_reason_ended = None
        self.players_ids = []
        self.opponent_id = None
        self.opponent_name = None
        self.player_white_id = None
        self.player_black_id = None
        self._game_board_call = None
        self.mandatory_capture_enabled = True # Сброс до значения по умолчанию
        # self.owner_id не сбрасываем, он остается постоянным

    async def settings_menu(self, call):
        """Меню настроек игры."""
        # Только владелец юзербота может менять настройки
        if call.from_user.id != self.owner_id:
            await call.answer("Только владелец юзербота может менять настройки этой партии!")
            return  
        
        await call.edit(
            text=f"Настройки этой партии\n"
                 f"| - > Хост играет за {self.colorName} цвет\n"
                 f"| - > Обязательный захват: {'Включен' if self.mandatory_capture_enabled else 'Выключен'}",
            reply_markup=[
                [
                    {"text":f"Цвет (хоста): {self.colorName}","callback":self.set_color}
                ],
                [
                    {"text":f"Обязательный захват: {'Включен' if self.mandatory_capture_enabled else 'Выключен'}","callback":self.toggle_mandatory_capture}
                ],
                [
                    {"text":"Вернуться","callback":self.back_to_invite}
                ]
            ]
        )

    async def toggle_mandatory_capture(self, call):
        """Переключает состояние обязательного захвата."""
        if call.from_user.id != self.owner_id:
            await call.answer("Только владелец юзербота может менять настройки!")
            return
        self.mandatory_capture_enabled = not self.mandatory_capture_enabled
        await call.answer(f"Обязательный захват теперь {'Включен' if self.mandatory_capture_enabled else 'Выключен'}")
        await self.settings_menu(call) # Обновляем меню настроек

    async def back_to_invite(self, call):
        """Возвращает к приглашению после настроек."""
        # Только владелец юзербота может взаимодействовать с этим меню настроек
        if call.from_user.id != self.owner_id:
            await call.answer("Это не для вас!")
            return
        
        await call.edit(
            text=f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
                 f"Текущие настройки:\n"
                 f"| - > • Хост играет за {self.colorName} цвет\n"
                 f"| - > • Обязательный захват: {'Включен' if self.mandatory_capture_enabled else 'Выключен'}",
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
        """Меню выбора цвета для хоста."""
        # Только владелец юзербота может менять настройки
        if call.from_user.id != self.owner_id:
            await call.answer("Только владелец юзербота может менять настройки!")
            return
        
        await call.edit(
            text=f"• Настройки этой партии.\n"
                 f"| - > Хост играет за: {self.colorName} цвет.\nВыберите цвет его фигур",
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
        """Обрабатывает выбор цвета хостом."""
        # Только владелец юзербота может менять настройки
        if call.from_user.id != self.owner_id:
            await call.answer("Только владелец юзербота может менять настройки!")
            return
        
        self.colorName = txt
        self.host_color = color
        await self.set_color(call) # Обновляем меню выбора цвета

    @loader.command() 
    async def checkers(self, message):
        """[reply/username/id] предложить человеку сыграть партию в чате"""
        if self._board_obj:
            await message.edit("Партия уже где-то запущена. Завершите или сбросьте её с <code>.stopgame</code>")
            return
        
        await self.purgeSelf() # Очищаем предыдущее состояние игры
        self._game_message = message
        self._game_chat_id = message.chat_id

        if message.is_reply:
            r = await message.get_reply_message()
            opponent = r.sender
            self.opponent_id = opponent.id
            self.opponent_name = html.escape(opponent.first_name)
        else:
            args = utils.get_args(message)
            if len(args) == 0:
                await message.edit("Вы не указали с кем играть")
                return
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
            except Exception:
                await message.edit("Я не нахожу такого пользователя")
                return
        
        if self.opponent_id == self._game_message.sender_id:
            await message.edit("Одиночные шашки? Простите, нет.")
            return

        self.players_ids = [self.opponent_id, self._game_message.sender_id]
        
        await self.inline.form(
            message = message,
            text = f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
                   f"Текущие настройки:\n"
                   f"| - > • Хост играет за {self.colorName} цвет\n"
                   f"| - > • Обязательный захват: {'Включен' if self.mandatory_capture_enabled else 'Выключен'}",
            reply_markup = [
                [
                    {"text": "Принимаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Нет", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "Изменить настройки", "callback": self.settings_menu}
                ]
            ], 
            disable_security = True, # Разрешить всем взаимодействовать с кнопками приглашения
            on_unload=self.outdated_game # Функция, вызываемая при "устаревании" формы
        )

    @loader.command() 
    async def stopgame(self, message):
        """Досрочное завершение партии"""
        # Проверяем, что игру может остановить только один из игроков, если игра активна.
        # Если игра неактивна (_board_obj is None), любой может "остановить" ее, чтобы очистить потенциально зависшее состояние.
        if self._board_obj and message.from_user.id not in self.players_ids:
            await message.edit("Вы не игрок этой партии.")
            return

        # Если игра была активна и сообщение с доской существовало, пытаемся обновить его
        if self._game_board_call:
            try:
                await self._game_board_call.edit(text="Партия была остановлена.")
            except Exception:
                pass # Сообщение могло быть удалено или недоступно
        
        await self.purgeSelf()
        await message.edit("Данные игры очищены.")

    async def accept_game(self, call, data):
        """Обрабатывает принятие/отклонение приглашения в игру."""
        # Проверка, что хост не может принять свою же игру, и что только приглашенные игроки могут взаимодействовать
        if call.from_user.id == self._game_message.sender_id:
            await call.answer("Дай человеку ответить!")
            return
        if call.from_user.id not in self.players_ids:
            await call.answer("Не тебе предлагают игру!")
            return
        
        if data == 'y':
            self._board_obj = CheckersBoard(mandatory_capture_enabled=self.mandatory_capture_enabled) # Передаем настройку обязательного захвата
            if not self.host_color: # Если цвет не был выбран, выбираем рандомно
                await call.edit(text="Выбираю стороны...")
                await asyncio.sleep(0.5)
                self.host_color = self.ranColor()
            
            # Назначаем ID игроков белым и черным
            if self.host_color == "white":
                self.player_white_id = self._game_message.sender_id
                self.player_black_id = self.opponent_id
            else:
                self.player_white_id = self.opponent_id
                self.player_black_id = self._game_message.sender_id

            text = await self.get_game_status_text()
            await call.edit(text="Загрузка доски...")
            await asyncio.sleep(0.5)
            
            self.game_running = True
            self._game_board_call = call # Сохраняем call объект, чтобы можно было редактировать доску
            
            await call.edit(text="Для лучшего различия фигур включите светлую тему!")
            await asyncio.sleep(2.5) # Даем время прочитать сообщение
            await self.render_board(text, call) # Отображаем доску
        else:
            await call.edit(text="Приглашение отклонено.")
            await self.purgeSelf()

    async def render_board(self, text, call):
        """Отображает доску шашек с кнопками."""
        board_emojis = self._board_obj.to_list_of_emojis(self._selected_piece_pos, self._possible_moves_for_selected)
        
        btns = []
        for r in range(8):
            row_btns = []
            for c in range(8):
                row_btns.append({"text": board_emojis[r][c], "callback": self.handle_click, "args":(r, c,)})
            btns.append(row_btns)

        # Добавляем кнопку "Остановить игру"
        btns.append([{"text": "Остановить игру", "callback": self.stop_game_inline}])

        await call.edit(
            text = text,
            reply_markup = btns,
            disable_security = True # Разрешить всем взаимодействовать (проверки внутри handle_click)
        )
    
    async def stop_game_inline(self, call):
        """Обрабатывает нажатие кнопки "Остановить игру" на доске."""
        # Проверяем, что игру может остановить только один из игроков
        if call.from_user.id not in self.players_ids:
            await call.answer("Вы не игрок этой партии.")
            return
        
        await self.purgeSelf()
        await call.edit("Партия была остановлена игроком.")
        
    async def handle_click(self, call, r, c):
        """Обрабатывает нажатие на клетку доски."""
        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            await call.answer(f"Партия окончена: {game_over_status}. Для новой игры используйте .checkers")
            if self.game_running:
                 self.game_running = False
                 await self.purgeSelf() # Очищаем данные после окончания игры
            return
        
        if call.from_user.id not in self.players_ids:
            await call.answer("Партия не ваша или уже сброшена!")
            return
        
        if not self.game_running:
            await call.answer("Игра еще не началась (не принята) или уже завершена.")
            await self.purgeSelf()
            return
        
        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        if call.from_user.id != current_player_id:
            await call.answer("Сейчас ход оппонента!")
            return

        piece_at_click = self._board_obj.get_piece_at(r, c)
        player_color_at_click = self._board_obj._get_player_color(piece_at_click)

        if self._selected_piece_pos is None:
            # Выбор фигуры
            if player_color_at_click == self._board_obj.current_player:
                # Проверяем обязательный захват только если он включен
                if self._board_obj.mandatory_capture_enabled and self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_from_pos != (r, c):
                    await call.answer("Вы должны продолжить захват с предыдущей позиции!")
                    return

                possible_moves_with_info = self._board_obj.get_valid_moves_for_selection(r, c)
                
                if possible_moves_with_info:
                    self._selected_piece_pos = (r, c)
                    # possible_moves_for_selected содержит (end_r, end_c, is_capture_move)
                    self._possible_moves_for_selected = [(m[2], m[3], m[4]) for m in possible_moves_with_info] 
                    await call.answer("Шашка выбрана. Выберите куда ходить.")
                    await self.render_board(await self.get_game_status_text(), call)
                else:
                    await call.answer("Для этой шашки нет доступных ходов (включая обязательные захваты)!")
            else:
                await call.answer("Тут нет вашей шашки или это светлая клетка!")
        else:
            # Попытка хода или отмена выбора
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
            for move_info in self._possible_moves_for_selected: # move_info: (end_r, end_c, is_capture)
                if (move_info[0], move_info[1]) == (r, c):
                    target_move_info = move_info
                    break

            if target_move_info:
                end_r, end_c, is_capture_move = target_move_info
                made_capture_and_can_jump_again = self._board_obj.make_move(start_r, start_c, end_r, end_c, is_capture_move)
                
                # Логика продолжения захвата применяется только если mandatory_capture_enabled
                if made_capture_and_can_jump_again and self._board_obj.mandatory_capture_enabled:
                    # Если был захват и можно сделать еще один, фигура остается выбранной
                    self._selected_piece_pos = (end_r, end_c)
                    # Обновляем возможные ходы для новой позиции (продолжение захвата)
                    self._possible_moves_for_selected = [(m[2], m[3], m[4]) for m in self._board_obj.get_valid_moves_for_selection(end_r, end_c)]
                    await call.answer("Захват! Сделайте следующий захват.")
                else:
                    # Ход завершен, сбрасываем выбор
                    self._selected_piece_pos = None
                    self._possible_moves_for_selected = []
                    await call.answer("Ход сделан.")
                
                game_over_status = self._board_obj.is_game_over()
                if game_over_status:
                    self.game_running = False
                    self.game_reason_ended = game_over_status
                    await call.answer(f"Партия окончена: {game_over_status}")
                    await self.render_board(await self.get_game_status_text(), call) # Обновляем доску с финальным статусом
                    await self.purgeSelf() # Очищаем данные после окончания игры
                    return
                
                await self.render_board(await self.get_game_status_text(), call)
            else:
                # Если выбранная клетка не является целью для хода, возможно, игрок хочет выбрать другую свою шашку
                if player_color_at_click == self._board_obj.current_player:
                    # Проверяем обязательный захват только если он включен
                    if self._board_obj.mandatory_capture_enabled and self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_from_pos != (r, c):
                        await call.answer("Вы должны продолжить захват с предыдущей позиции!")
                        return
                    
                    possible_moves_with_info = self._board_obj.get_valid_moves_for_selection(r, c)
                    
                    if possible_moves_with_info:
                        self._selected_piece_pos = (r, c)
                        self._possible_moves_for_selected = [(m[2], m[3], m[4]) for m in possible_moves_with_info]
                        await call.answer("Выбрана другая шашка.")
                        await self.render_board(await self.get_game_status_text(), call)
                    else:
                        await call.answer("Для этой шашки нет доступных ходов (включая обязательные захваты)!")
                else:
                    await call.answer("Неверный ход или цель не является вашей шашкой!")

    async def get_game_status_text(self):
        """Формирует текстовый статус игры (чей ход, кто играет, статус завершения)."""
        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            self.game_running = False
            self.game_reason_ended = game_over_status
            
            # Определяем имя победителя для отображения
            winner_name = ""
            if "Победа белых" in game_over_status:
                if self.player_white_id:
                    winner_name = html.escape((await self.client.get_entity(self.player_white_id)).first_name)
                    return f"Партия окончена: {game_over_status}\n\nПобедил(а) {winner_name} (белые)!"
            elif "Победа черных" in game_over_status:
                if self.player_black_id:
                    winner_name = html.escape((await self.client.get_entity(self.player_black_id)).first_name)
                    return f"Партия окончена: {game_over_status}\n\nПобедил(а) {winner_name} (черные)!"
            return f"Партия окончена: {game_over_status}"

        # Получаем актуальные имена игроков для отображения
        white_player_entity = await self.client.get_entity(self.player_white_id)
        black_player_entity = await self.client.get_entity(self.player_black_id)
        
        white_player_name = html.escape(white_player_entity.first_name)
        black_player_name = html.escape(black_player_entity.first_name)

        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        current_player_name = html.escape((await self.client.get_entity(current_player_id)).first_name)
        
        status_text = f"⚪ Белые - {white_player_name}\n⚫ Чёрные - {black_player_name}\n\n"
        
        if self._board_obj.current_player == "white":
            status_text += f"Ход белых ({current_player_name})"
        else:
            status_text += f"Ход чёрных ({current_player_name})"
        
        if self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_enabled:
            status_text += "\nОбязательный захват!"
        elif not self._board_obj.mandatory_capture_enabled:
            status_text += "\n(Обязательный захват выключен)"

        return status_text

    async def outdated_game(self):
        """
        Эта функция вызывается, когда инлайн-форма становится устаревшей (например, по таймауту).
        Если игра все еще активна, очищаем ее состояние.
        """
        if self.game_running or self._board_obj:
            await self.purgeSelf()
            # Если _game_board_call существует, пытаемся обновить сообщение, чтобы показать, что игра устарела
            if self._game_board_call:
                try:
                    await self._game_board_call.edit(text="Партия устарела из-за отсутствия активности.")
                except Exception:
                    pass # Сообщение могло быть удалено или недоступно

    def ranColor(self):
        """Возвращает случайный цвет: "white" или "black"."""
        return "white" if random.randint(1,2) == 1 else "black"
