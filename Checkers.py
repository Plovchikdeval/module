# meta developer: @Androfon_AI
# meta name: Шашки
# meta version: 1.0.8 # Обновляем версию после исправления ошибки

import asyncio, html, random
from .. import loader, utils

EMPTY = 0
WHITE_MAN = 1
BLACK_MAN = 2
WHITE_KING = 3
BLACK_KING = 4

PIECE_EMOJIS = {
    EMPTY: " ",
    "light": ".",
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
        self.mandatory_capture_from_pos = None
        self.mandatory_captures_enabled = mandatory_captures_enabled

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
            # Важно: здесь нужно использовать _get_moves_for_piece, так как get_all_possible_moves
            # вызывается рекурсивно, и _get_moves_for_piece не содержит логики mandatory_capture_from_pos
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
        piece = self.get_piece_at(start_r, start_c)
        
        self._execute_move(start_r, start_c, end_r, end_c, is_capture_move)
        
        # Превращение в дамки
        # Происходит после хода. Если шашка превратилась в дамку и может продолжить захват, она продолжит как дамка.
        if piece == WHITE_MAN and end_r == 0:
            self._set_piece_at(end_r, end_c, WHITE_KING)
            piece = WHITE_KING # Обновляем piece, чтобы check_for_further_captures использовал правильный тип
        elif piece == BLACK_MAN and end_r == 7:
            self._set_piece_at(end_r, end_c, BLACK_KING)
            piece = BLACK_KING # Обновляем piece

        if is_capture_move:
            # Проверяем, возможны ли дальнейшие захваты с новой позиции (мульти-прыжок)
            # Мульти-прыжок всегда обязателен, независимо от self.mandatory_captures_enabled
            # Важно: здесь мы должны использовать _get_moves_for_piece, а не get_all_possible_moves,
            # так как get_all_possible_moves уже учитывает mandatory_capture_from_pos,
            # и мы хотим проверить только для текущей фигуры.
            further_captures = [m for m in self._get_moves_for_piece(end_r, end_c) if m[4]]
            
            if further_captures:
                self.mandatory_capture_from_pos = (end_r, end_c)
                return True # Возвращаем True, если возможны дальнейшие захваты
            else:
                self.mandatory_capture_from_pos = None
                self.switch_turn()
                return False # Захваты закончились, ход переходит
        else:
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
                emoji = PIECE_EMOJIS[piece]

                if (r, c) == selected_pos:
                    emoji = PIECE_EMOJIS['selected']
                elif (r, c) in possible_move_targets_map:
                    is_capture_move = possible_move_targets_map[(r, c)]
                    emoji = PIECE_EMOJIS['capture_target'] if is_capture_move else PIECE_EMOJIS['move_target']
                elif (r + c) % 2 == 0: # Светлые клетки (если пустые и не являются целью/выбранной)
                    emoji = PIECE_EMOJIS['light']
                
                row_emojis.append(emoji)
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
        # Инициализация переменных состояния игры
        await self.purgeSelf() 
        # self.db уже доступен как атрибут от loader.Module, поэтому self.db = self.get_db() не требуется.

    async def purgeSelf(self):
        """Сбрасывает все переменные состояния игры."""
        self._board_obj = None
        self._game_message = None
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.colorName = "рандом" # Отображаемое имя цвета хоста
        self.host_color = None # Фактический цвет хоста (white/black)
        self.game_running = False
        self.game_reason_ended = None
        self.players_ids = []
        self.host_id = None
        self.opponent_id = None
        self.opponent_name = None
        self.player_white_id = None
        self.player_black_id = None
        self._game_board_call = None
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

        await call.edit(
            text=f"Настройки этой партии\n"
                 f"| - > Хост играет за {current_host_color_display} цвет\n"
                 f"| - > Обязательные взятия: {'Включены' if self.mandatory_captures_enabled else 'Отключены'}",
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
        opponent_name_display = "Оппонент"
        if self.opponent_id:
            try:
                opponent_entity = await self.client.get_entity(self.opponent_id)
                opponent_name_display = html.escape(opponent_entity.first_name)
            except Exception:
                pass # Fallback if entity not found

        # Обновляем текст для корректного отображения текущих настроек
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "белый"
        elif self.host_color == "black":
            current_host_color_display = "чёрный"
        else:
            current_host_color_display = "рандом"

        await call.edit(
            text=f"<a href='tg://user?id={self.opponent_id}'>{opponent_name_display}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
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
        """[reply/username/id] предложить человеку сыграть партию в чате"""
        if self._board_obj:
            await message.edit("Партия уже где-то запущена. Завершите или сбросьте её с <code>.stopgame</code>")
            return
        await self.purgeSelf()
        self._game_message = message
        self._game_chat_id = message.chat_id
        self.host_id = message.sender_id

        opponent = None
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
        
        current_host_color_display = self.colorName
        if self.host_color == "white":
            current_host_color_display = "белый"
        elif self.host_color == "black":
            current_host_color_display = "чёрный"
        else:
            current_host_color_display = "рандом"

        await self.inline.form(
            message = message,
            text = f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
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
        """Досрочное завершение партии"""
        if self._game_board_call and message.from_user.id not in self.players_ids and message.from_user.id != self.host_id:
            await message.edit("Вы не игрок этой партии.")
            return

        if self._game_board_call:
            try:
                await self._game_board_call.edit(text="Партия была остановлена.")
            except Exception:
                pass
        
        await self.purgeSelf()
        await message.edit("Данные очищены.")
        

    async def accept_game(self, call, data):
        if call.from_user.id == self.host_id:
            await call.answer("Дай человеку ответить!")
            return
        if call.from_user.id != self.opponent_id:
            await call.answer("Не тебе предлагают игру!")
            return
        
        if data == 'y':
            self._board_obj = CheckersBoard(mandatory_captures_enabled=self.mandatory_captures_enabled) 
            
            if not self.host_color:
                await call.edit(text="Выбираю стороны...")
                await asyncio.sleep(0.5)
                self.host_color = self.ranColor()
            
            if self.host_color == "white":
                self.player_white_id = self.host_id
                self.player_black_id = self.opponent_id
            else:
                self.player_white_id = self.opponent_id
                self.player_black_id = self.host_id

            text = await self.get_game_status_text()
            await call.edit(text="Загрузка доски...")
            await asyncio.sleep(0.5)
            
            self.game_running = True
            self._game_board_call = call
            
            await call.edit(text="Для лучшего различия фигур включите светлую тему!")
            await asyncio.sleep(2.5)
            await self.render_board(text, call)
        else:
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

        btns.append([{"text": "Остановить игру", "callback": self.stop_game_inline}])

        await call.edit(
            text = text,
            reply_markup = btns,
            disable_security = True
        )
    
    async def stop_game_inline(self, call):
        if call.from_user.id not in self.players_ids and call.from_user.id != self.host_id:
            await call.answer("Вы не игрок этой партии.")
            return
        
        await call.edit("Партия была остановлена игроком.")
        await self.purgeSelf()
        
    async def handle_click(self, call, r, c):
        # 1. Проверка на завершение игры в самом начале
        if not self._board_obj: # Если объект доски None, игра не активна или уже очищена
            await call.answer("Игра не активна или завершена. Начните новую игру.")
            await self.purgeSelf()
            return

        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            if self.game_running: # Если игра была активна, но только что завершилась
                self.game_running = False
                self.game_reason_ended = game_over_status
                # Обновляем доску в последний раз с финальным статусом
                await self.render_board(await self.get_game_status_text(), call)
                await self.purgeSelf() # ВАЖНО: Очищаем состояние ПОСЛЕ финального рендера
            await call.answer(f"Партия окончена: {game_over_status}. Для новой игры используйте .checkers")
            return
        
        # Проверки на активную игру и принадлежность игрока
        if not self.game_running: # Если game_running = False, но _board_obj существует (например, игра только что закончилась, но еще не очищена)
            await call.answer("Игра завершена. Начните новую игру.")
            await self.purgeSelf() # Гарантируем очистку, если состояние некорректно
            return
        
        if call.from_user.id not in self.players_ids and call.from_user.id != self.host_id:
            await call.answer("Партия не ваша!")
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
            for move_info in self._possible_moves_for_selected:
                if (move_info[0], move_info[1]) == (r, c):
                    target_move_info = move_info
                    break

            if target_move_info:
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
                    self.game_reason_ended = game_over_status_after_move
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
            # Флаги game_running и game_reason_ended устанавливаются в handle_click при первом обнаружении завершения игры.
            # Здесь мы просто отображаем статус.
            
            winner_name = ""
            if "Победа белых" in game_over_status:
                try:
                    winner_name = html.escape((await self.client.get_entity(self.player_white_id)).first_name)
                except Exception:
                    winner_name = "Белые"
                return f"Партия окончена: {game_over_status}\n\nПобедил(а) {winner_name} (белые)!"
            elif "Победа черных" in game_over_status:
                try:
                    winner_name = html.escape((await self.client.get_entity(self.player_black_id)).first_name)
                except Exception:
                    winner_name = "Черные"
                return f"Партия окончена: {game_over_status}\n\nПобедил(а) {winner_name} (черные)!"
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
        
        status_text = f"♔ Белые - {white_player_name}\n♚ Чёрные - {black_player_name}\n\n"
        
        if self._board_obj.current_player == "white":
            status_text += f"Ход белых ({current_player_name})"
        else:
            status_text += f"Ход чёрных ({current_player_name})"
        
        status_text += f"\nОбязательные взятия: {'Включены' if self.mandatory_captures_enabled else 'Отключены'}"

        if self._board_obj.mandatory_capture_from_pos:
            status_text += "\nОбязательный захват!"

        return status_text

    async def outdated_game(self):
        if self.game_running or self._board_obj:
            if self._game_board_call:
                try:
                    await self._game_board_call.edit(text="Партия устарела из-за отсутствия активности.")
                except Exception:
                    pass
            await self.purgeSelf()

    def ranColor(self):
        return "white" if random.randint(1,2) == 1 else "black"
