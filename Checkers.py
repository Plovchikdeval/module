# meta developer: @Androfon_AI
# meta name: Шашки
# meta version: 1.0.5

import asyncio, html, random
from .. import loader, utils

EMPTY = 0
WHITE_MAN = 1
BLACK_MAN = 2
WHITE_KING = 3
BLACK_KING = 4

PIECE_EMOJIS = {
    EMPTY: "▪️",
    "light": "▫️",
    WHITE_MAN: "⚪",
    BLACK_MAN: "⚫",
    WHITE_KING: "👑⚪",
    BLACK_KING: "👑⚫",
    'selected': "🔘",
    'move_target': "🟢",
    'capture_target': "🔴",
}

class CheckersBoard:
    def __init__(self):
        self._board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self._setup_initial_pieces()
        self.current_player = "white"
        self.mandatory_capture_from_pos = None

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
                    moves.append((r, c, new_r, new_c, False))

            # Ходы с захватом для шашек
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
                # Обычные ходы для королей
                current_r, current_c = r + dr, c + dc
                while self._is_valid_coord(current_r, current_c) and self.get_piece_at(current_r, current_c) == EMPTY:
                    moves.append((r, c, current_r, current_c, False))
                    current_r += dr
                    current_c += dc

                # Ходы с захватом для королей
                temp_r, temp_c = r + dr, c + dc
                found_opponent_piece = False
                while self._is_valid_coord(temp_r, temp_c):
                    piece_on_path = self.get_piece_at(temp_r, temp_c)
                    piece_on_path_color = self._get_player_color(piece_on_path)

                    if piece_on_path_color == player_color:
                        break # Blocked by own piece
                    elif piece_on_path_color == opponent_color:
                        if found_opponent_piece: # Already found an opponent piece, cannot capture another
                            break
                        found_opponent_piece = True # Mark that we found one
                        # Теперь проверяем пустые клетки *после* этой фигуры противника для приземления
                        jump_r, jump_c = temp_r + dr, temp_c + dc
                        while self._is_valid_coord(jump_r, jump_c) and self.get_piece_at(jump_r, jump_c) == EMPTY:
                            moves.append((r, c, jump_r, jump_c, True))
                            jump_r += dr
                            jump_c += dc
                        break # После нахождения фигуры и проверки мест приземления, этот диагональный сегмент завершен для захватов
                    elif piece_on_path == EMPTY:
                        # Продолжаем поиск фигуры противника для захвата
                        pass
                    
                    temp_r += dr
                    temp_c += dc

        return moves

    def get_all_possible_moves(self, player_color):
        all_moves = []
        all_captures = []

        if self.mandatory_capture_from_pos:
            r, c = self.mandatory_capture_from_pos
            # Если есть обязательный захват из конкретной позиции, возвращаем только захваты из этой позиции
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
        
        if all_captures: # Если есть хоть один возможный захват, они обязательны
            return all_captures
        return all_moves # Иначе возвращаем обычные ходы

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
        
        return is_capture_move

    def make_move(self, start_r, start_c, end_r, end_c, is_capture_move):
        piece = self.get_piece_at(start_r, start_c)
        
        self._execute_move(start_r, start_c, end_r, end_c, is_capture_move)
        
        # Превращение в дамки
        if piece == WHITE_MAN and end_r == 0:
            self._set_piece_at(end_r, end_c, WHITE_KING)
        elif piece == BLACK_MAN and end_r == 7:
            self._set_piece_at(end_r, end_c, BLACK_KING)
        
        if is_capture_move:
            # Проверяем, возможны ли дальнейшие захваты с новой позиции
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
        
        # Проверяем, есть ли у игроков доступные ходы
        if not self.get_all_possible_moves("white"):
            return "Победа черных (нет ходов у белых)"
        if not self.get_all_possible_moves("black"):
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
                elif (r + c) % 2 == 0: # Светлые клетки
                    emoji = PIECE_EMOJIS['light']
                
                row_emojis.append(emoji)
            board_emojis.append(row_emojis)
        return board_emojis
    
    def get_valid_moves_for_selection(self, current_r, current_c):
        piece_moves_full_info = self._get_moves_for_piece(current_r, current_c)
        
        all_game_moves_full_info = self.get_all_possible_moves(self.current_player)
        all_game_captures_full_info = [m for m in all_game_moves_full_info if m[4]]
        
        if all_game_captures_full_info:
            if self.mandatory_capture_from_pos:
                if (current_r, current_c) == self.mandatory_capture_from_pos:
                    # Только захваты из обязательной позиции
                    return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap]
                else:
                    # Если обязательный захват установлен, но не с этой фигуры, то ходов нет
                    return []
            else:
                # Если в целом есть захваты, возвращаем только захваты для этой фигуры,
                # которые также являются частью обязательных захватов для всего игрока.
                return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap and (s_r,s_c,e_r,e_c,is_cap) in all_game_captures_full_info]
        else:
            # Захватов нет, возвращаем обычные ходы для этой фигуры,
            # которые также являются частью всех возможных обычных ходов для всего игрока.
            # (all_game_moves_full_info в этом случае содержит только обычные ходы)
            return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if not is_cap and (s_r,s_c,e_r,e_c,is_cap) in all_game_moves_full_info]


@loader.tds
class Checkers(loader.Module):
    """Шашки для игры вдвоём."""
    strings = {
        "name": "Шашки"
    }

    async def client_ready(self):
        self._board_obj = None
        self._game_message = None
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.saymyname = html.escape((await self.client.get_me()).first_name)
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

    async def purgeSelf(self):
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

    async def settings_menu(self, call):
        # Проверка, что только игроки могут менять настройки
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
            return  
        await call.edit(
            text=f"Настройки этой партии\n"
                 f"| - > Хост играет за {self.colorName} цвет",
            reply_markup=[
                [
                    {"text":f"Цвет (хоста): {self.colorName}","callback":self.set_color}
                ],
                [
                    {"text":"Вернуться","callback":self.back_to_invite}
                ]
            ]
        )

    async def back_to_invite(self, call):
        # Проверка, что только игроки могут взаимодействовать
        if call.from_user.id not in self.players_ids:
            await call.answer("Это не для вас!")
            return
        await call.edit(
            text=f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
                 f"Текущие настройки:\n"
                 f"| - > • Хост играет за {self.colorName} цвет",
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
        # Проверка, что только игроки могут менять настройки
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
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
        # Проверка, что только игроки могут менять настройки
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
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
                   f"| - > • Хост играет за {self.colorName} цвет",
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
        # Проверяем, что игру может остановить только один из игроков
        if self._game_board_call and message.from_user.id not in self.players_ids:
            await message.edit("Вы не игрок этой партии.")
            return

        await self.purgeSelf()
        await message.edit("Данные очищены")
        # Если игра была активна и сообщение с доской существовало, возможно, стоит обновить его
        if self._game_board_call:
            try:
                await self._game_board_call.edit(text="Партия была остановлена.")
            except Exception:
                pass # Сообщение могло быть удалено или недоступно

    async def accept_game(self, call, data):
        # Проверка, что хост не может принять свою же игру, и что только приглашенные игроки могут взаимодействовать
        if call.from_user.id == self._game_message.sender_id:
            await call.answer("Дай человеку ответить!")
            return
        if call.from_user.id not in self.players_ids:
            await call.answer("Не тебе предлагают игру!")
            return
        
        if data == 'y':
            self._board_obj = CheckersBoard()
            if not self.host_color:
                await call.edit(text="Выбираю стороны...")
                await asyncio.sleep(0.5)
                self.host_color = self.ranColor()
            
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
            await asyncio.sleep(2.5)
            await self.render_board(text, call)
        else:
            await call.edit(text="Отклонено.")
            await self.purgeSelf()

    async def render_board(self, text, call):
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
            disable_security = True
        )
    
    async def stop_game_inline(self, call):
        # Проверяем, что игру может остановить только один из игроков
        if call.from_user.id not in self.players_ids:
            await call.answer("Вы не игрок этой партии.")
            return
        
        await self.purgeSelf()
        await call.edit("Партия была остановлена игроком.")
        
    async def handle_click(self, call, r, c):
        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            await call.answer(f"Партия окончена: {game_over_status}. Для новой игры используйте .checkers")
            # Если игра окончена, но purgeSelf еще не был вызван (например, если call.edit в get_game_status_text не сработал), то вызываем его.
            if self.game_running: # game_running будет False, если get_game_status_text уже обработал окончание
                 self.game_running = False
                 await self.purgeSelf()
            return
        
        if call.from_user.id not in self.players_ids:
            await call.answer("Партия не ваша или уже сброшена!")
            return
        
        if not self.game_running:
            await call.answer("Игра еще не началась (не принята) или уже завершена.")
            # Если игра не запущена, очищаем состояние на всякий случай
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
                    # Если был захват и можно сделать еще один, фигура остается выбранной
                    self._selected_piece_pos = (end_r, end_c)
                    self._possible_moves_for_selected = self._board_obj.get_valid_moves_for_selection(end_r, end_c)
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
        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            self.game_running = False
            self.game_reason_ended = game_over_status
            
            # Determine winner's name
            winner_name = ""
            if "Победа белых" in game_over_status:
                winner_name = html.escape((await self.client.get_entity(self.player_white_id)).first_name)
                return f"Партия окончена: {game_over_status}\n\nПобедил(а) {winner_name} (белые)!"
            elif "Победа черных" in game_over_status:
                winner_name = html.escape((await self.client.get_entity(self.player_black_id)).first_name)
                return f"Партия окончена: {game_over_status}\n\nПобедил(а) {winner_name} (черные)!"
            return f"Партия окончена: {game_over_status}"

        # Нужно получить актуальные имена игроков, так как self.saymyname и self.opponent_name могут быть не теми
        # кто играет белыми/черными, если хост выбрал другой цвет.
        white_player_entity = await self.client.get_entity(self.player_white_id)
        black_player_entity = await self.client.get_entity(self.player_black_id)
        
        white_player_name = html.escape(white_player_entity.first_name)
        black_player_name = html.escape(black_player_entity.first_name)

        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        current_player_name = html.escape((await self.client.get_entity(current_player_id)).first_name)
        
        status_text = f"♔ Белые - {white_player_name}\n♚ Чёрные - {black_player_name}\n\n"
        
        if self._board_obj.current_player == "white":
            status_text += f"Ход белых ({current_player_name})"
        else:
            status_text += f"Ход чёрных ({current_player_name})"
        
        if self._board_obj.mandatory_capture_from_pos:
            status_text += "\nОбязательный захват!"

        return status_text

    async def outdated_game(self):
        # Эта функция вызывается, когда инлайн-форма становится устаревшей (например, по таймауту)
        # Если игра все еще активна, очищаем ее состояние
        if self.game_running or self._board_obj:
            await self.purgeSelf()
            # Если _game_board_call существует, пытаемся обновить сообщение, чтобы показать, что игра устарела
            if self._game_board_call:
                try:
                    await self._game_board_call.edit(text="Партия устарела из-за отсутствия активности.")
                except Exception:
                    pass # Сообщение могло быть удалено или недоступно

    def ranColor(self):
        return "white" if random.randint(1,2) == 1 else "black"
