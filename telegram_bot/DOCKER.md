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

# Остановка
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
docker-compose down -v
```

### Файлы не сохраняются

```bash
# Проверьте volumes
docker-compose ps
ls -la data/uploads/
```
