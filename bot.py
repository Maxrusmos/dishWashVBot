"""Telegram-бот очереди мытья посуды."""
import json
import logging
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TZ = ZoneInfo("Europe/Moscow")
DATA_FILE = Path(__file__).with_name("data.json")
MORNING = time(10, 0, tzinfo=TZ)
EVENING = time(22, 0, tzinfo=TZ)

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger("dishbot")


# ---------- хранилище ----------

def load() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {}


def save(data: dict) -> None:
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def chat_state(data: dict, chat_id: int) -> dict:
    return data.setdefault(str(chat_id), {"queue": [], "current": 0, "done_date": None})


def today() -> str:
    return datetime.now(TZ).date().isoformat()


def current_person(st: dict) -> str | None:
    if not st["queue"]:
        return None
    st["current"] %= len(st["queue"])
    return st["queue"][st["current"]]


def format_queue(st: dict) -> str:
    if not st["queue"]:
        return "Очередь пуста. Добавьте людей: /add Имя"
    cur = current_person(st)
    lines = [
        f"{'👉' if i == st['current'] else '  '} {i + 1}. {name}"
        for i, name in enumerate(st["queue"])
    ]
    status = "✅ сегодня уже помыто" if st["done_date"] == today() else f"🍽 сейчас очередь: {cur}"
    return "Очередь:\n" + "\n".join(lines) + "\n\n" + status


# ---------- команды ----------

HELP = (
    "🧽 Бот очереди мытья посуды\n\n"
    "Каждый день в 10:00 МСК пишу, чья очередь, в 22:00 напоминаю, если посуда не помыта.\n\n"
    "/queue — показать очередь\n"
    "/add Имя — добавить в конец (можно @username)\n"
    "/remove N|Имя — удалить\n"
    "/move N M — переместить человека с позиции N на M\n"
    "/setturn N|Имя — сделать текущим\n"
    "/done — посуда помыта (очередь переходит к следующему)\n"
    "/skip — пропустить текущего без мытья\n"
    "/help — справка"
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    chat_state(data, update.effective_chat.id)
    save(data)
    await update.message.reply_text(HELP)


async def cmd_queue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    st = chat_state(data, update.effective_chat.id)
    await update.message.reply_text(format_queue(st))


def resolve_index(st: dict, arg: str) -> int | None:
    if arg.isdigit():
        i = int(arg) - 1
        return i if 0 <= i < len(st["queue"]) else None
    low = [n.lower() for n in st["queue"]]
    return low.index(arg.lower()) if arg.lower() in low else None


async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = " ".join(ctx.args).strip()
    if not name:
        await update.message.reply_text("Использование: /add Имя")
        return
    data = load()
    st = chat_state(data, update.effective_chat.id)
    st["queue"].append(name)
    save(data)
    await update.message.reply_text(f"Добавлен(а): {name}\n\n{format_queue(st)}")


async def cmd_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    st = chat_state(data, update.effective_chat.id)
    i = resolve_index(st, " ".join(ctx.args).strip())
    if i is None:
        await update.message.reply_text("Не нашёл. Использование: /remove N или /remove Имя")
        return
    name = st["queue"].pop(i)
    if i < st["current"]:
        st["current"] -= 1
    if st["queue"]:
        st["current"] %= len(st["queue"])
    else:
        st["current"] = 0
    save(data)
    await update.message.reply_text(f"Удалён(а): {name}\n\n{format_queue(st)}")


async def cmd_move(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    st = chat_state(data, update.effective_chat.id)
    n = len(st["queue"])
    try:
        src, dst = int(ctx.args[0]) - 1, int(ctx.args[1]) - 1
        assert 0 <= src < n and 0 <= dst < n
    except (IndexError, ValueError, AssertionError):
        await update.message.reply_text("Использование: /move N M (номера из /queue)")
        return
    cur_name = current_person(st)
    st["queue"].insert(dst, st["queue"].pop(src))
    st["current"] = st["queue"].index(cur_name)  # текущий остаётся текущим
    save(data)
    await update.message.reply_text(format_queue(st))


async def cmd_setturn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    st = chat_state(data, update.effective_chat.id)
    i = resolve_index(st, " ".join(ctx.args).strip())
    if i is None:
        await update.message.reply_text("Не нашёл. Использование: /setturn N или /setturn Имя")
        return
    st["current"] = i
    st["done_date"] = None
    save(data)
    await update.message.reply_text(format_queue(st))


async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    st = chat_state(data, update.effective_chat.id)
    who = current_person(st)
    if who is None:
        await update.message.reply_text("Очередь пуста.")
        return
    if st["done_date"] == today():
        await update.message.reply_text("Сегодня уже отмечено как помытое 👍")
        return
    st["done_date"] = today()
    st["current"] = (st["current"] + 1) % len(st["queue"])
    save(data)
    await update.message.reply_text(
        f"✨ {who}, спасибо! Посуда помыта.\nСледующим будет: {current_person(st)}"
    )


async def cmd_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    st = chat_state(data, update.effective_chat.id)
    who = current_person(st)
    if who is None:
        await update.message.reply_text("Очередь пуста.")
        return
    st["current"] = (st["current"] + 1) % len(st["queue"])
    save(data)
    await update.message.reply_text(f"{who} пропущен(а). Теперь очередь: {current_person(st)}")


# ---------- расписание ----------

async def morning_job(ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    for chat_id, st in data.items():
        who = current_person(st)
        if who is None:
            continue
        try:
            await ctx.bot.send_message(int(chat_id), f"☀️ Доброе утро! Сегодня посуду моет: {who}")
        except Exception as e:  # бота могли удалить из чата
            log.warning("chat %s: %s", chat_id, e)
    save(data)


async def evening_job(ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    for chat_id, st in data.items():
        who = current_person(st)
        if who is None or st["done_date"] == today():
            continue
        try:
            await ctx.bot.send_message(
                int(chat_id),
                f"🌙 {who}, посуда всё ещё не помыта! Помой и напиши /done",
            )
        except Exception as e:
            log.warning("chat %s: %s", chat_id, e)


def main():
    token = os.environ.get("BOT_TOKEN")
    token_file = Path(__file__).with_name("token.txt")
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("Укажите токен в переменной BOT_TOKEN или в файле token.txt")

    app = Application.builder().token(token).build()
    for name, fn in [
        ("start", cmd_start), ("help", cmd_start), ("queue", cmd_queue),
        ("add", cmd_add), ("remove", cmd_remove), ("move", cmd_move),
        ("setturn", cmd_setturn), ("done", cmd_done), ("skip", cmd_skip),
    ]:
        app.add_handler(CommandHandler(name, fn))

    app.job_queue.run_daily(morning_job, MORNING, name="morning")
    app.job_queue.run_daily(evening_job, EVENING, name="evening")

    log.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
