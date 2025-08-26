# meta developer: @yourhandle
# meta name: Шашки
# meta version: 1.0.3
#
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# 00000000000000000000000000000000
# H:Mods Team [💎]

from hikkatl.tl.types import PeerUser
import asyncio, html, random, time
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

class Timer:
    def __init__(self, scnds):
        self.timers = {"white": scnds, "black": scnds}
        self.running = {"white": False, "black": False}
        self.last_tick_time = None
        self.task = None

    async def _timer_loop(self):
        self.last_tick_time = time.monotonic()
        while True:
            await asyncio.sleep(0.1)
            now = time.monotonic()
            elapsed = now - self.last_tick_time
            self.last_tick_time = now

            for color in ("white", "black"):
                if self.running[color]:
                    self.timers[color] = max(0, self.timers[color] - elapsed)
                    if self.timers[color] == 0:
                        # Если таймер дошел до 0, останавливаем все таймеры и выходим из цикла
                        for c in ("white", "black"):
                            self.running[c] = False
                        # Не возвращаем здесь, чтобы внешний TimerLoop мог обнаружить 0 и обработать
                        return

    async def start(self):
        if self.task is None:
            self.task = asyncio.create_task(self._timer_loop())

    async def switch_player_turn(self, new_player_color):
        for color in ("white", "black"):
            self.running[color] = (color == new_player_color)

    async def get_time(self, color):
        # Возвращаем текущее значение, не проверяя task.done(), так как task может быть завершен, но время все равно актуально
        return int(max(0, self.timers[color]))

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        self.running = {"white": False, "black": False}
        self.last_tick_time = None

    async def clear(self):
        await self.stop()
        self.timers = {"white": 0, "black": 0}


class CheckersBoard:
    def __init__(self):
        self._board = [[EMPTY for _ in range(8)] for _ in range(8)]
        self._setup_initial_pieces()
        self.current_player = "white"
        self.mandatory_capture_from_pos = None

    def _setup_initial_pieces(self):
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 != 0:
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

            for dr, dc in regular_move_directions:
                new_r, new_c = r + dr, c + dc
                if self._is_valid_coord(new_r, new_c) and self.get_piece_at(new_r, new_c) == EMPTY:
                    moves.append((r, c, new_r, new_c, False))

            for dr, dc in all_diagonal_directions:
                jump_r, jump_c = r + 2 * dr, c + 2 * dc
                captured_piece_r, captured_piece_c = r + dr, c + dc
                captured_piece = self.get_piece_at(captured_piece_r, captured_piece_c)

                if (self._is_valid_coord(jump_r, jump_c) and
                    self.get_piece_at(jump_r, jump_c) == EMPTY and
                    self._get_player_color(captured_piece) == opponent_color):
                    
                    moves.append((r, c, jump_r, jump_c, True))

        elif piece in [WHITE_KING, BLACK_KING]:
            for dr, dc in all_diagonal_directions:
                current_r, current_c = r + dr, c + dc
                while self._is_valid_coord(current_r, current_c) and self.get_piece_at(current_r, current_c) == EMPTY:
                    moves.append((r, c, current_r, current_c, False))
                    current_r += dr
                    current_c += dc

                current_r, current_c = r + dr, c + dc
                found_opponent = False
                while self._is_valid_coord(current_r, current_c):
                    target_piece = self.get_piece_at(current_r, current_c)
                    
                    if not found_opponent:
                        if self._get_player_color(target_piece) == opponent_color:
                            found_opponent = True
                            after_capture_r, after_capture_c = current_r + dr, current_c + dc
                            if self._is_valid_coord(after_capture_r, after_capture_c) and self.get_piece_at(after_capture_r, after_capture_c) == EMPTY:
                                landing_r, landing_c = after_capture_r, after_capture_c
                                while self._is_valid_coord(landing_r, landing_c) and self.get_piece_at(landing_r, landing_c) == EMPTY:
                                    moves.append((r, c, landing_r, landing_c, True))
                                    landing_r += dr
                                    landing_c += dc
                                break
                            else:
                                break
                        elif self._get_player_color(target_piece) == player_color:
                            break
                        elif target_piece == EMPTY:
                            current_r += dr
                            current_c += dc
                        else:
                            break
                    else:
                        break

        return moves

    def get_all_possible_moves(self, player_color):
        all_moves = []
        all_captures = []

        if self.mandatory_capture_from_pos:
            r, c = self.mandatory_capture_from_pos
            # Если есть обязательный захват с определенной позиции, возвращаем только захваты с этой позиции
            return [m for m in self._get_moves_for_piece(r, c) if m[4]]
            
        for r in range(8):
            for c in range(8):
                piece = self.get_piece_at(r, c)
                if self._get_player_color(piece) == player_color:
                    moves_for_piece = self._get_moves_for_piece(r, c)
                    for move in moves_for_piece:
                        if move[4]:
                            all_captures.append(move)
                        else:
                            all_moves.append(move)
        
        if all_captures:
            return all_captures
        return all_moves

    def _execute_move(self, start_r, start_c, end_r, end_c):
        piece = self.get_piece_at(start_r, start_c)
        self._set_piece_at(end_r, end_c, piece)
        self._set_piece_at(start_r, start_c, EMPTY)

        is_capture = False
        if abs(start_r - end_r) > 1: # Это означает, что это был прыжок/захват
            dr = 1 if end_r > start_r else -1
            dc = 1 if end_c > start_c else -1

            current_r, current_c = start_r + dr, start_c + dc
            while (current_r, current_c) != (end_r, end_c):
                if self.get_piece_at(current_r, current_c) != EMPTY:
                    # Найдена захваченная фигура
                    self._set_piece_at(current_r, current_c, EMPTY)
                    is_capture = True
                    break # За один прыжок захватывается только одна фигура
                current_r += dr
                current_c += dc
        
        return is_capture

    def make_move(self, start_r, start_c, end_r, end_c):
        piece = self.get_piece_at(start_r, start_c)
        
        is_capture = self._execute_move(start_r, start_c, end_r, end_c)
        
        if piece == WHITE_MAN and end_r == 0:
            self._set_piece_at(end_r, end_c, WHITE_KING)
        elif piece == BLACK_MAN and end_r == 7:
            self._set_piece_at(end_r, end_c, BLACK_KING)
        
        if is_capture:
            # Проверяем, есть ли дальнейшие захваты с новой позиции
            further_captures = [m for m in self._get_moves_for_piece(end_r, end_c) if m[4]]
            if further_captures:
                self.mandatory_capture_from_pos = (end_r, end_c)
                return True # Да, был захват и можно сделать еще один
            else:
                self.mandatory_capture_from_pos = None
                self.switch_turn()
                return False # Был захват, но дальнейших нет, ход переходит
        else:
            self.mandatory_capture_from_pos = None
            self.switch_turn()
            return False # Не было захвата, ход переходит

    def switch_turn(self):
        self.current_player = self._get_opponent_color(self.current_player)

    def is_game_over(self):
        white_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "white")
        black_pieces = sum(1 for r in range(8) for c in range(8) if self._get_player_color(self.get_piece_at(r, c)) == "black")

        if white_pieces == 0:
            return "Победа черных"
        if black_pieces == 0:
            return "Победа белых"
        
        if not self.get_all_possible_moves("white"):
            return "Победа черных (нет ходов у белых)"
        if not self.get_all_possible_moves("black"):
            return "Победа белых (нет ходов у черных)"

        return None

    def to_list_of_emojis(self, selected_pos=None, possible_moves_with_info=None):
        board_emojis = []
        possible_moves_with_info = possible_moves_with_info if possible_moves_with_info else []
        
        # possible_moves_with_info ожидается в формате [(end_r, end_c, is_capture), ...]
        possible_move_targets_map = {(end_r, end_c): is_capture for end_r, end_c, is_capture in possible_moves_with_info}

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
                elif (r + c) % 2 == 0:
                    emoji = PIECE_EMOJIS['light']
                
                row_emojis.append(emoji)
            board_emojis.append(row_emojis)
        return board_emojis


@loader.tds
class Checkers(loader.Module):
    """Шашки для игры вдвоём."""
    strings = {
        "name": "Checkers"
    }

    async def client_ready(self):
        self._board_obj = None
        self._game_message = None
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.saymyname = html.escape((await self.client.get_me()).first_name)
        self.timeName = "❌ Без часов"
        self.pTime = None
        self.colorName = "рандом"
        self.host_color = None
        self.timer_active = False
        self.Timer = None
        self.timer_loop_active = False
        self.game_running = False
        self.game_reason_ended = None
        self.players_ids = []
        self.opponent_id = None
        self.opponent_name = None
        self.time_message_obj = None
        self.player_white_id = None
        self.player_black_id = None
        self._game_board_call = None

    async def purgeSelf(self):
        self._board_obj = None
        self._game_message = None
        self._game_chat_id = None
        self._selected_piece_pos = None
        self._possible_moves_for_selected = []
        self.timeName = "❌ Без часов"
        self.pTime = None
        self.colorName = "рандом"
        self.host_color = None
        if self.Timer:
            await self.Timer.clear()
            self.Timer = None
        self.timer_active = False
        if self.time_message_obj:
            try:
                await self.time_message_obj.delete()
            except Exception:
                pass
            self.time_message_obj = None
        self.timer_loop_active = False
        self.game_running = False
        self.game_reason_ended = None
        self.players_ids = []
        self.opponent_id = None
        self.opponent_name = None
        self.player_white_id = None
        self.player_black_id = None
        self._game_board_call = None # Сброс _game_board_call

    async def settings_menu(self, call, no_timer_in_group):
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
            return  
        await call.edit(
            text=f"<emoji document_id=5877260593903177342>⚙</emoji> Настройки этой партии\n"
                 f"| - > Хост играет за {self.colorName} цвет\n"
                 f"| - > Время: {self.timeName}",
            reply_markup=[
                [
                    {"text":f"<emoji document_id=5778550614669660455>⏲</emoji> Время: {self.timeName}","callback":self.set_time, "args":(no_timer_in_group,)} if not no_timer_in_group else {"text":f"❌ Время: ...","action":"answer","show_alert":True,"message":"Приглашение находится в чате.\n\nИз-за ограничений для ботов, партии на время могут проводиться только в лс"}
                ],
                [
                    {"text":f"<emoji document_id=5875271289605722323>🍔</emoji> Цвет (хоста): {self.colorName}","callback":self.set_color, "args":(no_timer_in_group,)}
                ],
                [
                    {"text":"<emoji document_id=5886455371559604605>➡️</emoji> Вернуться","callback":self.back_to_invite, "args":(no_timer_in_group,)}
                ]
            ]
        )

    async def back_to_invite(self, call, no_timer_in_group):
        if call.from_user.id not in self.players_ids:
            await call.answer("Это не для вас!")
            return
        await call.edit(
            text=f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
                 f"<emoji document_id=5877260593903177342>⚙</emoji> Текущие настройки:\n"
                 f"| - > • Хост играет за {self.colorName} цвет\n"
                 f"| - > • Время: {self.timeName}",
            reply_markup = [
                [
                    {"text": "Принимаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Нет", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "<emoji document_id=5877260593903177342>⚙</emoji> Настройки", "callback": self.settings_menu, "args":(no_timer_in_group,)}
                ]
            ]
        )

    async def set_time(self, call, no_timer_in_group):
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
            return
        await call.edit(
            text=f"• Настройки этой партии.\n"
                 f"| - > <emoji document_id=5778550614669660455>⏲</emoji> Время: {self.timeName}",
            reply_markup=[
                [
                    {"text":"<emoji document_id=5845677551892042113>⚡</emoji> Блиц","action":"answer","message":"Блиц-Блиц - скорость без границ"}
                ],
                [
                    {"text":"3 минуты","callback":self.handle_time_choice,"args":(3,"3 минуты",no_timer_in_group,)},
                    {"text":"5 минут","callback":self.handle_time_choice,"args":(5,"5 минут",no_timer_in_group,)}
                ],
                [
                    {"text":"<emoji document_id=5778550614669660455>⏲</emoji> Рапид","action":"answer","message":"Обдумай своё поражение"}
                ],
                [
                    {"text":"10 минут","callback":self.handle_time_choice,"args":(10,"10 минут",no_timer_in_group,)},
                    {"text":"15 минут","callback":self.handle_time_choice,"args":(15,"15 минут",no_timer_in_group,)},
                    {"text":"30 минут","callback":self.handle_time_choice,"args":(30,"30 минут",no_timer_in_group,)},
                    {"text":"60 минут","callback":self.handle_time_choice,"args":(60,"60 минут",no_timer_in_group,)}
                ],
                [
                    {"text":"❌ Нет часов", "callback":self.handle_time_choice,"args":(None,"❌ Нет часов",no_timer_in_group,)}
                ],
                [
                    {"text":"<emoji document_id=5886455371559604605>➡️</emoji> Обратно к настройкам", "callback":self.settings_menu, "args":(no_timer_in_group,)}
                ]
            ]
        )

    async def handle_time_choice(self, call, minutes, txt, no_timer_in_group):
        self.timeName = txt
        self.pTime = minutes * 60 if minutes else None
        await self.set_time(call, no_timer_in_group)

    async def set_color(self, call, no_timer_in_group):
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
            return
        await call.edit(
            text=f"• Настройки этой партии.\n"
                 f"| - > <emoji document_id=5875271289605722323>🍔</emoji> Хост играет за: {self.colorName} цвет.\nВыберите цвет его фигур",
            reply_markup=[
                [
                    {"text":("✅ " if self.host_color == "white" else "❌ ") + "Белые","callback":self.handle_color_choice,"args":("white","белый",no_timer_in_group,)},
                    {"text":("✅ " if self.host_color == "black" else "❌ ") + "Чёрные","callback":self.handle_color_choice,"args":("black","чёрный",no_timer_in_group,)}
                ],
                [
                    {"text":"<emoji document_id=5960608239623082921>🎲</emoji> Рандом" if self.host_color is None else "❌ Рандом", "callback":self.handle_color_choice,"args":(None,"рандом",no_timer_in_group)}
                ],
                [
                    {"text":"<emoji document_id=5886455371559604605>➡️</emoji> Обратно к настройкам", "callback":self.settings_menu, "args":(no_timer_in_group,)}
                ]
            ]
        )

    async def handle_color_choice(self, call, color, txt, no_timer_in_group):
        if call.from_user.id not in self.players_ids:
            await call.answer("Настройки не для вас!")
            return
        self.colorName = txt
        self.host_color = color
        await self.set_color(call, no_timer_in_group)

    @loader.command() 
    async def checkers(self, message):
        """[reply/username/id] предложить человеку сыграть партию в чате"""
        if self._board_obj:
            await message.edit("<emoji document_id=5370724846936267183>🤔</emoji> Партия уже где-то запущена. Завершите или сбросьте её с <code>.stopgame</code>")
            return
        await self.purgeSelf()
        self._game_message = message
        self._game_chat_id = message.chat_id
        no_timer_in_group = not isinstance(message.peer_id, PeerUser)

        if message.is_reply:
            r = await message.get_reply_message()
            opponent = r.sender
            self.opponent_id = opponent.id
            self.opponent_name = html.escape(opponent.first_name)
        else:
            args = utils.get_args(message)
            if len(args) == 0:
                await message.edit("<emoji document_id=5370724846936267183>🤔</emoji> Вы не указали с кем играть")
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
                await message.edit("❌ Я не нахожу такого пользователя")
                return
        
        if self.opponent_id == self._game_message.sender_id:
            await message.edit("<emoji document_id=5384398004172102616>😈</emoji> Одиночные шашки? Простите, нет.")
            return

        self.players_ids = [self.opponent_id, self._game_message.sender_id]
        
        await self.inline.form(
            message = message,
            text = f"<a href='tg://user?id={self.opponent_id}'>{self.opponent_name}</a>, вас пригласили сыграть партию в шашки, примите?\n-- --\n"
                   f"<emoji document_id=5877260593903177342>⚙</emoji> Текущие настройки:\n"
                   f"| - > • Хост играет за {self.colorName} цвет\n"
                   f"| - > • Время: {self.timeName}",
            reply_markup = [
                [
                    {"text": "Принимаю", "callback": self.accept_game, "args":("y",)},
                    {"text": "Нет", "callback": self.accept_game, "args":("n",)}
                ],
                [
                    {"text": "<emoji document_id=5877260593903177342>⚙</emoji> Настройки", "callback": self.settings_menu, "args":(no_timer_in_group,)}
                ]
            ], 
            disable_security = True,
            on_unload=self.outdated_game
        )

    @loader.command() 
    async def stopgame(self, message):
        """Грубо завершить партию, очистив ВСЕ связанные с ней данные"""
        await self.purgeSelf()
        await message.edit("Данные очищены <emoji document_id=5879896690210639947>🗑</emoji>")

    async def accept_game(self, call, data):
        if call.from_user.id == self._game_message.sender_id:
            await call.answer("Дай человеку ответить!")
            return
        if call.from_user.id not in self.players_ids:
            await call.answer("Не тебе предлагают игру!")
            return
        
        if data == 'y':
            self._board_obj = CheckersBoard()
            if not self.host_color:
                await call.edit(text="Выбираю стороны... <emoji document_id=5960608239623082921>🎲</emoji>")
                await asyncio.sleep(0.5)
                self.host_color = self.ranColor()
            
            if self.host_color == "white":
                self.player_white_id = self._game_message.sender_id
                self.player_black_id = self.opponent_id
            else:
                self.player_white_id = self.opponent_id
                self.player_black_id = self._game_message.sender_id

            text = await self.get_game_status_text()
            await call.edit(text="Загрузка доски... <emoji document_id=5875431869842985304>🎛</emoji>")
            await asyncio.sleep(0.5)
            
            if self.pTime:
                await call.edit(text="Ставлю таймеры... <emoji document_id=5778550614669660455>⏲</emoji>")
                self.Timer = Timer(self.pTime)
                self.timer_active = True
                self._game_board_call = call # Сохраняем call объект основной доски
                await asyncio.sleep(0.5)
                self.time_message_obj = await self.inline.form(
                    message=await self.client.send_message(self._game_chat_id, "Настройка таймера..."), 
                    text=f"♔ Белые: {await self.Timer.get_time('white')}\n♚ Чёрные: {await self.Timer.get_time('black')}\n<emoji document_id=5886366951067883092>💤</emoji> Начнём?",
                    reply_markup=[{"text":"Начать партию", "callback":self.start_timer_game, "args":(call,)}], # Передаем call, чтобы потом использовать для основной доски
                    disable_security=True
                )
                return
            else:
                self.game_running = True
                self._game_board_call = call # Сохраняем call объект основной доски и для игр без таймера
            
            await call.edit(text="<emoji document_id=5879813604068298387>❗️</emoji> Для лучшего различия фигур включите светлую тему!")
            await asyncio.sleep(2.5)
            await self.render_board(text, call)
        else:
            await call.edit(text="Отклонено. <emoji document_id=5778527486270770928>❌</emoji>")
            await self.purgeSelf()

    async def start_timer_game(self, original_board_call):
        if original_board_call.from_user.id not in self.players_ids:
            if self.time_message_obj:
                await self.time_message_obj.edit("Партия не ваша!")
            return
        await self.Timer.start()
        await self.Timer.switch_player_turn(self._board_obj.current_player)
        self.timer_loop_active = True
        self.game_running = True
        if self.time_message_obj:
            await self.time_message_obj.edit(text=f"♔ Белые: {await self.Timer.get_time('white')}\n♚ Чёрные: {await self.Timer.get_time('black')}", reply_markup=None)
        await self.render_board(await self.get_game_status_text(), original_board_call)

    @loader.loop(interval=1)
    async def TimerLoop(self):
        if self.timer_loop_active and self.game_running and self.Timer:
            white_time = await self.Timer.get_time('white')
            black_time = await self.Timer.get_time('black')

            if self.time_message_obj:
                await self.time_message_obj.edit(text=f"♔ Белые: {white_time}\n♚ Чёрные: {black_time}")
            
            if white_time == 0:
                self.game_reason_ended = "Истекло время у белых"
                self.game_running = False
                self.timer_loop_active = False # Останавливаем цикл
                await self.Timer.stop() # Останавливаем внутренний таймер
                await self.render_board(await self.get_game_status_text(), self._game_board_call)
                await self.purgeSelf()
            elif black_time == 0:
                self.game_reason_ended = "Истекло время у чёрных"
                self.game_running = False
                self.timer_loop_active = False # Останавливаем цикл
                await self.Timer.stop() # Останавливаем внутренний таймер
                await self.render_board(await self.get_game_status_text(), self._game_board_call)
                await self.purgeSelf()
        elif not self.game_running and self.timer_loop_active:
            self.timer_loop_active = False
            if self.time_message_obj:
                # Обновляем сообщение таймера с причиной остановки
                current_white_time = await self.Timer.get_time('white') if self.Timer else 0
                current_black_time = await self.Timer.get_time('black') if self.Timer else 0
                await self.time_message_obj.edit(text=f"♔ Белые: {current_white_time}\n♚ Чёрные: {current_black_time}\n❌ Остановлен по причине: {self.game_reason_ended}", reply_markup=None)
            if self.Timer:
                await self.Timer.stop() # Гарантируем остановку внутреннего таймера

    async def render_board(self, text, call):
        # Если таймер активен, игра не запущена и цикл таймера неактивен (т.е. игра еще не началась или уже закончилась через TimerLoop), не рендерим
        if self.timer_active and not self.game_running and not self.timer_loop_active:
            return

        board_emojis = self._board_obj.to_list_of_emojis(self._selected_piece_pos, self._possible_moves_for_selected)
        
        btns = []
        for r in range(8):
            row_btns = []
            for c in range(8):
                row_btns.append({"text": board_emojis[r][c], "callback": self.handle_click, "args":(r, c,)})
            btns.append(row_btns)

        await call.edit(
            text = text,
            reply_markup = btns,
            disable_security = True
        )

    async def handle_click(self, call, r, c):
        game_over_status = self._board_obj.is_game_over()
        if game_over_status:
            await call.answer(f"Партия окончена: {game_over_status}. Для новой игры используйте .checkers")
            await self.purgeSelf()
            return
        
        if call.from_user.id not in self.players_ids:
            await call.answer("Партия не ваша или уже сброшена!")
            return
        
        if not self.game_running:
            await call.answer("Игра еще не началась (не запущен таймер или не принята).")
            return
        
        current_player_id = self.player_white_id if self._board_obj.current_player == "white" else self.player_black_id
        if call.from_user.id != current_player_id:
            await call.answer("Сейчас ход оппонента!")
            return

        piece_at_click = self._board_obj.get_piece_at(r, c)
        player_color_at_click = self._board_obj._get_player_color(piece_at_click)

        def get_valid_moves_for_selection(current_r, current_c):
            piece_moves_full_info = self._board_obj._get_moves_for_piece(current_r, current_c)
            
            all_game_moves_full_info = self._board_obj.get_all_possible_moves(self._board_obj.current_player)
            all_game_captures_full_info = [m for m in all_game_moves_full_info if m[4]]
            
            if all_game_captures_full_info:
                if self._board_obj.mandatory_capture_from_pos:
                    if (current_r, current_c) == self._board_obj.mandatory_capture_from_pos:
                        return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap]
                    else:
                        # Если есть обязательный захват, но не с этой шашки
                        return []
                else:
                    return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if is_cap]
            else:
                return [(e_r, e_c, is_cap) for s_r, s_c, e_r, e_c, is_cap in piece_moves_full_info if not is_cap]

        if self._selected_piece_pos is None:
            if player_color_at_click == self._board_obj.current_player:
                if self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_from_pos != (r, c):
                    await call.answer("Вы должны продолжить захват с предыдущей позиции!")
                    return

                possible_moves_with_info = get_valid_moves_for_selection(r, c)
                
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
            start_r, start_c = self._selected_piece_pos
            
            if (r, c) == (start_r, start_c):
                self._selected_piece_pos = None
                self._possible_moves_for_selected = []
                await call.answer("Выбор отменен.")
                await self.render_board(await self.get_game_status_text(), call)
                return

            target_move_info = next(
                (move_info for move_info in self._possible_moves_for_selected if (move_info[0], move_info[1]) == (r, c)),
                None
            )

            if target_move_info:
                end_r, end_c, _ = target_move_info
                made_capture_and_can_jump_again = self._board_obj.make_move(start_r, start_c, end_r, end_c)
                
                if made_capture_and_can_jump_again:
                    self._selected_piece_pos = (end_r, end_c)
                    self._possible_moves_for_selected = get_valid_moves_for_selection(end_r, end_c)
                    await call.answer("Захват! Сделайте следующий захват.")
                else:
                    self._selected_piece_pos = None
                    self._possible_moves_for_selected = []
                    await call.answer("Ход сделан.")
                
                game_over_status = self._board_obj.is_game_over()
                if game_over_status:
                    self.game_running = False
                    self.game_reason_ended = game_over_status
                    if self.timer_active and self.Timer:
                        await self.Timer.stop()
                    await call.answer(f"Партия окончена: {game_over_status}")
                    await self.render_board(await self.get_game_status_text(), call)
                    await self.purgeSelf()
                    return
                
                if not made_capture_and_can_jump_again and self.timer_active and self.Timer:
                    await self.Timer.switch_player_turn(self._board_obj.current_player)

                await self.render_board(await self.get_game_status_text(), call)
            else:
                if player_color_at_click == self._board_obj.current_player:
                    if self._board_obj.mandatory_capture_from_pos and self._board_obj.mandatory_capture_from_pos != (r, c):
                        await call.answer("Вы должны продолжить захват с предыдущей позиции!")
                        return
                    
                    possible_moves_with_info = get_valid_moves_for_selection(r, c)
                    
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
            if self.timer_active and self.Timer:
                await self.Timer.stop()
            
            if "Победа белых" in game_over_status:
                winner_name = self.saymyname if self.player_white_id == self._game_message.sender_id else self.opponent_name
                return f"Партия окончена: {game_over_status}\n\n<emoji document_id=5994502837327892086>🎉</emoji> Победил(а) {winner_name} (белые)!"
            elif "Победа черных" in game_over_status:
                winner_name = self.saymyname if self.player_black_id == self._game_message.sender_id else self.opponent_name
                return f"Партия окончена: {game_over_status}\n\n<emoji document_id=5994502837327892086>🎉</emoji> Победил(а) {winner_name} (черные)!"
            return f"Партия окончена: {game_over_status}"

        current_player_name = self.saymyname if (self._board_obj.current_player == "white" and self.player_white_id == self._game_message.sender_id) or \
                                                 (self._board_obj.current_player == "black" and self.player_black_id == self._game_message.sender_id) else self.opponent_name
        
        white_player_name = self.saymyname if self.player_white_id == self._game_message.sender_id else self.opponent_name
        black_player_name = self.saymyname if self.player_black_id == self._game_message.sender_id else self.opponent_name

        status_text = f"♔ Белые - {white_player_name}\n♚ Чёрные - {black_player_name}\n\n"
        
        if self._board_obj.current_player == "white":
            status_text += f"<emoji document_id=5830060857530257978>➡️</emoji> Ход белых ({current_player_name})"
        else:
            status_text += f"<emoji document_id=5830060857530257978>➡️</emoji> Ход чёрных ({current_player_name})"
        
        if self._board_obj.mandatory_capture_from_pos:
            status_text += "\n<emoji document_id=5879813604068298387>❗️</emoji> Обязательный захват!"

        return status_text

    async def outdated_game(self):
        if self.game_running or self._board_obj:
            await self.purgeSelf()

    def ranColor(self):
        return "white" if random.randint(1,2) == 1 else "black"