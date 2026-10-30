# 🧽 DishWash Bot

Telegram-бот для беседы: каждый день в **10:00 МСК** пишет, чья очередь мыть посуду, а в **22:00 МСК** напоминает, если посуда ещё не помыта.

## Команды

| Команда | Что делает |
|---|---|
| `/queue` | показать очередь |
| `/add Имя` | добавить в конец (можно `@username`, тогда человек получит упоминание) |
| `/remove N` или `/remove Имя` | удалить |
| `/move N M` | переместить с позиции N на M |
| `/setturn N` или `/setturn Имя` | сделать текущим |
| `/done` | посуда помыта → очередь переходит к следующему |
| `/skip` | пропустить текущего |

Если человек не нажал `/done`, на следующий день очередь остаётся за ним.

## 1. Создать бота

1. В Telegram напишите [@BotFather](https://t.me/BotFather) → `/newbot` → получите токен.
2. Там же: `/setprivacy` → выберите бота → **Disable** (иначе в группе бот может не видеть команды без `@имя_бота`; команды со `/` обычно и так работают).
3. Добавьте бота в беседу и напишите `/start`.

## 2. Запуск на Windows Server

1. Установите Python 3.11+ с https://www.python.org/downloads/ (галочка **Add python.exe to PATH**).
2. Скопируйте папку с ботом, например в `C:\dishbot`, и в PowerShell:

```powershell
cd C:\dishbot
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

3. Положите токен в файл `token.txt` рядом с `bot.py` (одна строка).
4. Проверочный запуск:

```powershell
.\.venv\Scripts\python bot.py
```

### Автозапуск (чтобы работал после перезагрузки)

```powershell
schtasks /Create /TN "DishBot" /SC ONSTART /RU SYSTEM /RL HIGHEST /TR "C:\dishbot\.venv\Scripts\python.exe C:\dishbot\bot.py"
schtasks /Run /TN "DishBot"
```

Остановить: `schtasks /End /TN "DishBot"`.

## Linux (если понадобится)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo "ВАШ_ТОКЕН" > token.txt
.venv/bin/python bot.py
```

Данные очередей хранятся в `data.json` рядом с ботом.
