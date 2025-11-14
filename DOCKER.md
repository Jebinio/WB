# Docker Quick Reference

## Первый запуск

```bash
# 1. Создайте .env файл
cp .env.example .env
# Отредактируйте .env с вашим BOT_TOKEN и ADMIN_IDS

# 2. Запустите бот
docker-compose up -d

# 3. Проверьте логи
docker-compose logs -f bot
```

## Повседневные команды

```bash
# Запуск
docker-compose up -d

# Остановка (данные сохраняются!)
docker-compose down

# Просмотр логов
docker-compose logs -f bot

# Перестроение образа
docker-compose up -d --build

# Вход в контейнер
docker-compose exec bot bash

# Статус контейнеров
docker-compose ps
```

## Обновление бота

```bash
# 1. Остановите бот
docker-compose down

# 2. Обновите код
git pull

# 3. Перестройте и запустите
docker-compose up -d --build

# ✅ БД и файлы загрузок полностью сохраняются!
```

## ⚠️ ВАЖНО: Как НЕ потерять данные

❌ **НИКОГДА не используйте:**
```bash
docker-compose down -v  # Это удалит все volumes!
```

✅ **Используйте вместо этого:**
```bash
docker-compose down     # Безопасно - все данные сохраняются
```

## Backup и Restore

```bash
# Создать backup БД
docker run --rm -v telegram_bot_bot_data:/data -v $(pwd):/backup alpine \
  sh -c 'cp /data/database.db /backup/database.db.backup'

# Восстановить из backup
docker run --rm -v telegram_bot_bot_data:/data -v $(pwd):/backup alpine \
  sh -c 'cp /backup/database.db.backup /data/database.db'
```

## Управление Volumes

```bash
# Список всех volumes
docker volume ls

# Информация о volume
docker volume inspect telegram_bot_bot_data

# Удалить volume (⚠️ удалит данные!)
docker volume rm telegram_bot_bot_data
```

## Ошибки и решения

### ImportError при запуске

```bash
# Перестройте образ
docker-compose down
docker-compose up -d --build
```

### Проблемы с портами

```bash
# Проверьте используемые порты
docker-compose ps

# Удалите старые контейнеры
docker-compose down
```

### Файлы не сохраняются

```bash
# Проверьте что используется volume
docker-compose config | grep -A5 volumes

# Проверьте содержимое volume
docker run --rm -v telegram_bot_bot_data:/data alpine ls -la /data
```

