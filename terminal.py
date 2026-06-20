import pygame
import sys
import os
import shlex
import random
import time
import socket
import struct
import math
import ctypes

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1)

NORMAL_SIZE = (1100, 620)
MAX_SIZE = pygame.display.Info()
MAX_SIZE = (MAX_SIZE.current_w, MAX_SIZE.current_h)

WIDTH, HEIGHT = NORMAL_SIZE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
is_maximized = False

clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20)
font_big = pygame.font.SysFont("consolas", 40, bold=True)
font_small = pygame.font.SysFont("consolas", 16)

# ---------------- Pasta de sistema (ao lado do script) ----------------
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_DIR = os.path.join(SCRIPT_DIR, "lunix_system")

# ---------------- Estados gerais ----------------
lines = []
input_text = ""
boot_finished = False
boot_stage = 0
last_update = pygame.time.get_ticks()
boot_start_time = time.time()

LINE_HEIGHT = 30
MAX_VISIBLE_LINES = 16
scroll_offset = 0  # quantas linhas roladas pra cima no historico

# mode: "terminal", "snake", "ttt", "nano"
mode = "terminal"

JOKES = [
    "Why did the shell get so grumpy? It had too many arguments.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "rm -rf /jokes/bad : Permission denied (thank god).",
    "A SQL query walks into a bar, sees two tables and asks: 'Can I join you?'",
    "Why was the kernel cold? It left its core open.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "I told a UDP joke, but I'm not sure if you got it.",
    "Why did the developer go broke? Because he used up all his cache.",
    "I would tell you a joke about TCP, but I'm not sure you'd get it... eventually.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "A programmer's wife says go buy a loaf of bread, if they have eggs buy a dozen. He came back with 12 loaves of bread.",
    "Why did the function break up with the loop? It felt like it kept going in circles.",
    "There's no place like 127.0.0.1.",
    "I'd tell a joke about recursion, but I'd have to tell it again to explain the punchline.",
    "Why was the computer cold? It left its Windows open.",
]


def add_log(text):
    lines.append(text)
    if len(lines) > 300:
        lines.pop(0)


def get_uptime():
    elapsed = int(time.time() - boot_start_time)
    h = elapsed // 3600
    m = (elapsed % 3600) // 60
    s = elapsed % 60
    return f"{h:02}:{m:02}:{s:02}"


def check_system_dir():
    """Chamado no boot: confere se a pasta de sistema existe, senao cria.
    Se ja existir, NAO cria de novo (nem sobrescreve nada)."""
    if os.path.isdir(SYSTEM_DIR):
        add_log(f"/system | System directory already exists at '{SYSTEM_DIR}'... [OK]")
    else:
        try:
            os.mkdir(SYSTEM_DIR)
            add_log(f"/system | System directory not found, created at '{SYSTEM_DIR}'... [OK]")
        except FileExistsError:
            add_log(f"/system | System directory already exists at '{SYSTEM_DIR}'... [OK]")
        except Exception as e:
            add_log(f"/system | Failed to create system directory: {e}")


def do_ping(host):
    if not host:
        add_log("Usage: ping <host>")
        return
    add_log(f"PING {host}:")
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        add_log(f"ping: cannot resolve {host}: Unknown host")
        return

    times = []
    for i in range(4):
        start = time.time()
        try:
            s = socket.create_connection((ip, 80), timeout=2)
            s.close()
            elapsed_ms = (time.time() - start) * 1000
            times.append(elapsed_ms)
            add_log(f"  reply from {ip}: time={elapsed_ms:.1f}ms")
        except Exception:
            add_log(f"  reply from {ip}: timeout")
    if times:
        avg = sum(times) / len(times)
        add_log(f"  --- {host} ping statistics: avg={avg:.1f}ms, sent=4, received={len(times)} ---")
    else:
        add_log("  --- 100% packet loss ---")


# ---------------- BEEP ----------------
def play_beep(hex_str):
    hex_str = hex_str.strip().lower().replace("0x", "")
    if not hex_str:
        add_log("Usage: beep <hex>  (ex: beep 1A2B)")
        return
    try:
        value = int(hex_str, 16)
    except ValueError:
        add_log(f"beep: '{hex_str}' is not a valid hexadecimal value")
        return

    freq = 200 + (value % 1800)
    duration_ms = 180
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    amplitude = 16000

    buf = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        sample = int(amplitude * math.sin(2 * math.pi * freq * t))
        buf += struct.pack('<h', sample)

    sound = pygame.mixer.Sound(buffer=bytes(buf))
    sound.play()
    add_log(f"BEEP! hex=0x{value:X} -> freq={freq}Hz")


# ---------------- POPUP (MessageBox real do Windows) ----------------
def show_popup(category, title, message):
    category = (category or "null").lower()

    MB_OK = 0x0
    MB_ICONERROR = 0x10
    MB_ICONWARNING = 0x30
    MB_ICONINFORMATION = 0x40
    MB_SYSTEMMODAL = 0x1000

    if category in ("err", "error", "erro"):
        icon = MB_ICONERROR
        cat_label = "ERROR"
    elif category in ("aviso", "warning", "warn"):
        icon = MB_ICONWARNING
        cat_label = "WARNING"
    else:
        icon = MB_OK
        cat_label = "NULL"

    if not title:
        title = "Lunix"
    if not message:
        message = ""

    add_log(f"popup: spawning [{cat_label}] '{title}' -> {message}")

    if sys.platform.startswith("win"):
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, icon | MB_SYSTEMMODAL)
        except Exception as e:
            add_log(f"popup: failed to spawn native window: {e}")
    else:
        add_log("popup: native Windows popup only available on Windows. Showing in log instead:")
        add_log(f"[{cat_label}] {title}: {message}")


# ---------------- CREATE (cria arquivo na pasta de sistema) ----------------
def create_file(filename, content_parts):
    if not filename:
        add_log("Usage: create <filename> [content...]")
        return
    safe_name = os.path.basename(filename)
    if not safe_name:
        add_log("create: invalid filename")
        return

    # garante que a pasta de sistema existe, sem recriar se ja existir
    if not os.path.isdir(SYSTEM_DIR):
        try:
            os.mkdir(SYSTEM_DIR)
        except FileExistsError:
            pass
        except Exception as e:
            add_log(f"create: failed to prepare system directory: {e}")
            return

    target = os.path.join(SYSTEM_DIR, safe_name)
    content = " ".join(content_parts)

    if os.path.isfile(target):
        add_log(f"create: '{safe_name}' already exists at '{target}', not overwriting")
        return

    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        add_log(f"create: file '{safe_name}' created successfully at '{target}'")
    except Exception as e:
        add_log(f"create: failed to create file: {type(e).__name__}: {e}")


# ---------------- Comandos ----------------
def execute_command(cmd):
    global mode
    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()
    if not parts:
        return
    command, args = parts[0], parts[1:]

    if command == "help":
        add_log("Available commands:")
        add_log("  help              - shows this list")
        add_log("  clear             - clears the terminal log")
        add_log("  ls                - lists simulated directories")
        add_log("  echo <text>       - prints text back to the terminal")
        add_log("  calc <expr>       - basic math calculator (ex: calc 10+5)")
        add_log("  ping <host>       - pings a real host over the network")
        add_log("  beep <hex>        - plays a beep, pitch based on hex value")
        add_log("  nano <file>       - opens the text editor (Ctrl+X to exit)")
        add_log("  create <file> [text]  - creates a file in the system folder")
        add_log("  popup <err|aviso|null> <title> <msg> - spawns a real Windows popup")
        add_log("  game -snake       - launches Snake (arrows to move, ESC to quit)")
        add_log("  game -ttt         - launches Tic-Tac-Toe (click cells, ESC to quit)")
        add_log("  info              - shows instance information")
        add_log("  joke              - tells a random joke")
        add_log("  cat -logcli       - shows full session log since boot")
        add_log("  F1                - toggle maximized window")
    elif command == "clear":
        lines.clear()
    elif command == "ls":
        if os.path.isdir(SYSTEM_DIR):
            entries = os.listdir(SYSTEM_DIR)
            add_log("  ".join(entries) if entries else "(system folder is empty)")
        else:
            add_log("boot  home  usr  bin  extra")
    elif command == "echo":
        add_log(" ".join(args) if args else "")
    elif command == "ping":
        do_ping(args[0] if args else "")
    elif command == "beep":
        play_beep(args[0] if args else "")
    elif command == "nano":
        start_nano(args[0] if args else "untitled")
    elif command == "create":
        if args:
            create_file(args[0], args[1:])
        else:
            add_log("Usage: create <filename> [content...]")
    elif command == "popup":
        category = args[0] if len(args) > 0 else "null"
        title = args[1] if len(args) > 1 else "Lunix"
        message = args[2] if len(args) > 2 else ""
        show_popup(category, title, message)
    elif command == "game":
        if "-snake" in args:
            add_log("Launching Snake... (arrows to move, ESC to quit)")
            start_snake()
        elif "-ttt" in args:
            add_log("Launching Tic-Tac-Toe... (click cells, ESC to quit)")
            start_ttt()
        else:
            add_log("Usage: game -snake | -ttt")
    elif command == "calc":
        try:
            add_log(f"Result: {eval(''.join(args))}")
        except Exception:
            add_log("Error: Invalid calculation")
    elif command == "joke":
        add_log(random.choice(JOKES))
    elif command == "info":
        add_log("---- Instance Information ----")
        add_log("Lunix 1.0 PoC")
        add_log("Kernel Version 1.0 rev r5")
        add_log(f"Uptime: {get_uptime()}")
        add_log(f"System dir: {SYSTEM_DIR}")
        add_log("-------------------------------")
    elif command == "cat" and "-logcli" in args:
        add_log("---- FULL SESSION LOG ----")
        for entry in list(lines):
            add_log(entry)
        add_log("---- END OF LOG ----")
    else:
        add_log(f"'{command}': unknown command")


def show_welcome():
    add_log("WELCOME TO LUNIX 1.0 (POC)")
    add_log("INFO: This is just the PoC, not the complete system.")
    add_log("WARNING: Source is on GitHub. NEVER download from elsewhere.")
    add_log("Type 'help' to see available commands.")


# ---------------- NANO ----------------
nano_state = {}


def start_nano(filename):
    global mode
    mode = "nano"
    nano_state.clear()
    nano_state["filename"] = filename
    nano_state["text_lines"] = [""]
    nano_state["cursor_row"] = 0
    nano_state["cursor_col"] = 0
    nano_state["saved"] = False

    # se ja existe um arquivo com esse nome na pasta de sistema, carrega o conteudo
    path = os.path.join(SYSTEM_DIR, os.path.basename(filename))
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            nano_state["text_lines"] = content.split("\n") if content else [""]
            nano_state["saved"] = True
        except Exception:
            pass


def nano_handle_key(event):
    tl = nano_state["text_lines"]
    row = nano_state["cursor_row"]
    col = nano_state["cursor_col"]
    mods = pygame.key.get_mods()
    ctrl_held = mods & pygame.KMOD_CTRL

    if ctrl_held and event.key == pygame.K_x:
        global mode
        add_log(f"nano: closed '{nano_state['filename']}'" +
                (" (saved)" if nano_state["saved"] else " (unsaved changes discarded)"))
        mode = "terminal"
        return
    if ctrl_held and event.key == pygame.K_o:
        path = os.path.join(SYSTEM_DIR, os.path.basename(nano_state["filename"]))
        try:
            os.makedirs(SYSTEM_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(tl))
            nano_state["saved"] = True
            add_log(f"nano: wrote '{nano_state['filename']}' to system folder")
        except Exception as e:
            add_log(f"nano: failed to save: {e}")
        return

    if event.key == pygame.K_RETURN:
        rest = tl[row][col:]
        tl[row] = tl[row][:col]
        tl.insert(row + 1, rest)
        nano_state["cursor_row"] += 1
        nano_state["cursor_col"] = 0
        nano_state["saved"] = False
    elif event.key == pygame.K_BACKSPACE:
        if col > 0:
            tl[row] = tl[row][:col - 1] + tl[row][col:]
            nano_state["cursor_col"] -= 1
        elif row > 0:
            prev_len = len(tl[row - 1])
            tl[row - 1] += tl[row]
            tl.pop(row)
            nano_state["cursor_row"] -= 1
            nano_state["cursor_col"] = prev_len
        nano_state["saved"] = False
    elif event.key == pygame.K_LEFT:
        if col > 0:
            nano_state["cursor_col"] -= 1
        elif row > 0:
            nano_state["cursor_row"] -= 1
            nano_state["cursor_col"] = len(tl[row - 1])
    elif event.key == pygame.K_RIGHT:
        if col < len(tl[row]):
            nano_state["cursor_col"] += 1
        elif row < len(tl) - 1:
            nano_state["cursor_row"] += 1
            nano_state["cursor_col"] = 0
    elif event.key == pygame.K_UP:
        if row > 0:
            nano_state["cursor_row"] -= 1
            nano_state["cursor_col"] = min(col, len(tl[row - 1]))
    elif event.key == pygame.K_DOWN:
        if row < len(tl) - 1:
            nano_state["cursor_row"] += 1
            nano_state["cursor_col"] = min(col, len(tl[row + 1]))
    elif event.unicode and event.unicode.isprintable() and not ctrl_held:
        tl[row] = tl[row][:col] + event.unicode + tl[row][col:]
        nano_state["cursor_col"] += 1
        nano_state["saved"] = False


def draw_nano():
    screen.fill((30, 30, 40))
    header = f"  GNU nano 7.2     {nano_state['filename']}" + ("" if nano_state["saved"] else " (modified)")
    pygame.draw.rect(screen, (40, 40, 60), (0, 0, WIDTH, 28))
    screen.blit(font.render(header, True, (230, 230, 230)), (4, 4))

    y0 = 40
    for i, line in enumerate(nano_state["text_lines"]):
        screen.blit(font.render(line, True, (220, 220, 220)), (10, y0 + i * 24))

    cur_row, cur_col = nano_state["cursor_row"], nano_state["cursor_col"]
    prefix = nano_state["text_lines"][cur_row][:cur_col]
    cur_x = 10 + font.size(prefix)[0]
    cur_y = y0 + cur_row * 24
    if (pygame.time.get_ticks() // 500) % 2 == 0:
        pygame.draw.rect(screen, (255, 255, 255), (cur_x, cur_y, 2, 20))

    bar_y = HEIGHT - 50
    pygame.draw.rect(screen, (40, 40, 60), (0, bar_y, WIDTH, 50))
    shortcuts = "^X Exit      ^O Write Out      Arrows: move      Enter: new line"
    screen.blit(font.render(shortcuts, True, (220, 220, 220)), (10, bar_y + 14))


# ---------------- SNAKE ----------------
snake_state = {}


def start_snake():
    global mode
    mode = "snake"
    cell = 20
    cols = WIDTH // cell
    rows = (HEIGHT - 40) // cell
    snake_state.clear()
    snake_state["body"] = [(cols // 2, rows // 2)]
    snake_state["dir"] = (1, 0)
    snake_state["food"] = (random.randint(0, cols - 1), random.randint(0, rows - 1))
    snake_state["cell"] = cell
    snake_state["cols"] = cols
    snake_state["rows"] = rows
    snake_state["last_move"] = pygame.time.get_ticks()
    snake_state["speed"] = 110
    snake_state["score"] = 0
    snake_state["dead"] = False


def update_snake_input(event):
    d = snake_state["dir"]
    if event.key in (pygame.K_UP, pygame.K_w) and d != (0, 1):
        snake_state["dir"] = (0, -1)
    elif event.key in (pygame.K_DOWN, pygame.K_s) and d != (0, -1):
        snake_state["dir"] = (0, 1)
    elif event.key in (pygame.K_LEFT, pygame.K_a) and d != (1, 0):
        snake_state["dir"] = (-1, 0)
    elif event.key in (pygame.K_RIGHT, pygame.K_d) and d != (-1, 0):
        snake_state["dir"] = (1, 0)


def update_snake():
    if snake_state["dead"]:
        return
    now = pygame.time.get_ticks()
    if now - snake_state["last_move"] < snake_state["speed"]:
        return
    snake_state["last_move"] = now

    cols, rows = snake_state["cols"], snake_state["rows"]
    head = snake_state["body"][0]
    dx, dy = snake_state["dir"]
    new_head = (head[0] + dx, head[1] + dy)

    if (new_head[0] < 0 or new_head[0] >= cols or
            new_head[1] < 0 or new_head[1] >= rows or
            new_head in snake_state["body"]):
        snake_state["dead"] = True
        return

    snake_state["body"].insert(0, new_head)
    if new_head == snake_state["food"]:
        snake_state["score"] += 1
        while True:
            f = (random.randint(0, cols - 1), random.randint(0, rows - 1))
            if f not in snake_state["body"]:
                break
        snake_state["food"] = f
    else:
        snake_state["body"].pop()


def draw_snake():
    screen.fill((0, 0, 0))
    cell = snake_state["cell"]
    for (x, y) in snake_state["body"]:
        pygame.draw.rect(screen, (0, 255, 0), (x * cell, y * cell + 40, cell - 2, cell - 2))
    fx, fy = snake_state["food"]
    pygame.draw.rect(screen, (255, 0, 0), (fx * cell, fy * cell + 40, cell - 2, cell - 2))

    hud = font.render(f"SNAKE  score: {snake_state['score']}   ESC: quit to terminal", True, (200, 200, 200))
    screen.blit(hud, (10, 8))

    if snake_state["dead"]:
        over = font_big.render("GAME OVER", True, (255, 60, 60))
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 20))
        sub = font.render("Press ESC to return to terminal", True, (200, 200, 200))
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 30))


# ---------------- TIC TAC TOE ----------------
ttt_state = {}


def start_ttt():
    global mode
    mode = "ttt"
    ttt_state.clear()
    ttt_state["board"] = [""] * 9
    ttt_state["turn"] = "X"
    ttt_state["winner"] = None


def ttt_check_winner(board):
    wins = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)]
    for a, b, c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None


def ttt_click(pos):
    if ttt_state["winner"]:
        return
    mx, my = pos
    size = 150
    ox, oy = WIDTH // 2 - (size * 3) // 2, 80
    if not (ox <= mx <= ox + size * 3 and oy <= my <= oy + size * 3):
        return
    col = (mx - ox) // size
    row = (my - oy) // size
    idx = row * 3 + col
    if ttt_state["board"][idx] == "":
        ttt_state["board"][idx] = ttt_state["turn"]
        w = ttt_check_winner(ttt_state["board"])
        if w:
            ttt_state["winner"] = w
        else:
            ttt_state["turn"] = "O" if ttt_state["turn"] == "X" else "X"


def draw_ttt():
    screen.fill((0, 0, 0))
    size = 150
    ox, oy = WIDTH // 2 - (size * 3) // 2, 80

    hud = font.render("TIC-TAC-TOE   click a cell   ESC: quit to terminal", True, (200, 200, 200))
    screen.blit(hud, (10, 8))

    for i in range(1, 3):
        pygame.draw.line(screen, (90, 90, 90), (ox + i * size, oy), (ox + i * size, oy + size * 3), 2)
        pygame.draw.line(screen, (90, 90, 90), (ox, oy + i * size), (ox + size * 3, oy + i * size), 2)
    pygame.draw.rect(screen, (90, 90, 90), (ox, oy, size * 3, size * 3), 2)

    for idx, val in enumerate(ttt_state["board"]):
        if not val:
            continue
        row, col = divmod(idx, 3)
        cx = ox + col * size + size // 2
        cy = oy + row * size + size // 2
        color = (0, 255, 0) if val == "X" else (255, 80, 80)
        glyph = font_big.render(val, True, color)
        screen.blit(glyph, (cx - glyph.get_width() // 2, cy - glyph.get_height() // 2))

    if ttt_state["winner"]:
        if ttt_state["winner"] == "draw":
            msg = "DRAW!"
        else:
            msg = f"{ttt_state['winner']} WINS!"
        over = font_big.render(msg, True, (255, 220, 0))
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, oy + size * 3 + 20))
        sub = font.render("Press ESC to return to terminal", True, (200, 200, 200))
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, oy + size * 3 + 70))
    else:
        turn_txt = font.render(f"Turn: {ttt_state['turn']}", True, (200, 200, 200))
        screen.blit(turn_txt, (WIDTH // 2 - turn_txt.get_width() // 2, oy + size * 3 + 20))


# ---------------- LOOP PRINCIPAL ----------------
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            is_maximized = not is_maximized
            if is_maximized:
                WIDTH, HEIGHT = MAX_SIZE
            else:
                WIDTH, HEIGHT = NORMAL_SIZE
            screen = pygame.display.set_mode((WIDTH, HEIGHT))
            continue

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and mode in ("snake", "ttt"):
            mode = "terminal"
            add_log("Returned to terminal.")
            continue

        if mode == "terminal" and boot_finished and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                add_log(f"r00t@lunix$ {input_text}")
                execute_command(input_text)
                input_text = ""
                scroll_offset = 0
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_UP:
                scroll_offset = min(scroll_offset + 1, max(0, len(lines) - MAX_VISIBLE_LINES))
            elif event.key == pygame.K_DOWN:
                scroll_offset = max(scroll_offset - 1, 0)
            elif event.key == pygame.K_PAGEUP:
                scroll_offset = min(scroll_offset + MAX_VISIBLE_LINES, max(0, len(lines) - MAX_VISIBLE_LINES))
            elif event.key == pygame.K_PAGEDOWN:
                scroll_offset = max(scroll_offset - MAX_VISIBLE_LINES, 0)
            else:
                input_text += event.unicode

        elif mode == "nano" and event.type == pygame.KEYDOWN:
            nano_handle_key(event)

        elif mode == "snake" and event.type == pygame.KEYDOWN:
            update_snake_input(event)

        elif mode == "ttt" and event.type == pygame.MOUSEBUTTONDOWN:
            ttt_click(event.pos)

    if mode == "snake":
        update_snake()
        draw_snake()
        fps = int(clock.get_fps())
        pygame.display.set_caption(f"Lunix instance - fps {fps} - playing snake - [tty1]")
        pygame.display.flip()
        clock.tick(60)
        continue

    if mode == "ttt":
        draw_ttt()
        fps = int(clock.get_fps())
        pygame.display.set_caption(f"Lunix instance - fps {fps} - playing tic-tac-toe - [tty1]")
        pygame.display.flip()
        clock.tick(60)
        continue

    if mode == "nano":
        draw_nano()
        fps = int(clock.get_fps())
        pygame.display.set_caption(f"Lunix instance - fps {fps} - editing {nano_state['filename']} - [tty1]")
        pygame.display.flip()
        clock.tick(60)
        continue

    # ---- modo terminal ----
    screen.fill((0, 0, 0))

    if not boot_finished:
        if pygame.time.get_ticks() - last_update > 500:
            boot_stage += 1
            if boot_stage == 1:
                add_log("/sys | Mounting system kernel... [OK]")
            if boot_stage == 2:
                add_log("/usr | Mounting user binaries... [OK]")
            if boot_stage == 3:
                add_log("/confg | Loading system configurations... [OK]")
            if boot_stage == 4:
                check_system_dir()
            if boot_stage == 5:
                add_log("/extra | Initializing extra modules... [OK]")
            if boot_stage == 6:
                lines.clear()
                show_welcome()
                boot_finished = True
                boot_start_time = time.time()
            last_update = pygame.time.get_ticks()

    if scroll_offset > 0:
        end = len(lines) - scroll_offset
        start = max(0, end - MAX_VISIBLE_LINES)
        visible_lines = lines[start:end]
    else:
        visible_lines = lines[-MAX_VISIBLE_LINES:]

    y = 20
    for line in visible_lines:
        if "[OK]" in line:
            color = (0, 255, 0)
        elif line.startswith("WELCOME"):
            color = (255, 0, 0)
        elif line.startswith("WARNING"):
            color = (255, 255, 0)
        elif line.startswith("INFO"):
            color = (150, 150, 150)
        elif line.startswith("BEEP"):
            color = (0, 255, 255)
        else:
            color = (255, 255, 255)
        screen.blit(font.render(line, True, color), (20, y))
        y += LINE_HEIGHT

    if scroll_offset > 0:
        hint = font_small.render(f"-- scrolled up ({scroll_offset} lines) | DOWN to return --", True, (120, 120, 120))
        screen.blit(hint, (WIDTH - hint.get_width() - 15, 10))

    if boot_finished:
        prompt_y = HEIGHT - 50
        r_surf = font.render("r00t", True, (255, 0, 0))
        p_surf = font.render(f"@lunix$ {input_text}_", True, (255, 255, 255))
        screen.blit(r_surf, (20, prompt_y))
        screen.blit(p_surf, (20 + r_surf.get_width(), prompt_y))

    fps = int(clock.get_fps())
    state = "waiting for command" if boot_finished else "booting"
    pygame.display.set_caption(f"Lunix instance - fps {fps} - {state} - [tty1]")

    pygame.display.flip()
    clock.tick(60)
