# Бот с Mini App

## Запуск
1. @BotFather → /newbot → получи токен.
2. Залей папку `webapp/` на любой HTTPS-хостинг (GitHub Pages, Vercel, Netlify)
   или для теста: `cd webapp && python -m http.server 8000` + `ngrok http 8000`.
3. `cp .env.example .env` и впиши BOT_TOKEN и WEBAPP_URL (https!).
4. `pip install -r requirements.txt && python bot.py`
5. Напиши боту /start и жми кнопку.

Важно: sendData работает только если мини-апп открыт через кнопку reply-клавиатуры (так и сделано).
