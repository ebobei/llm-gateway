# llm-gateway

Простой локальный сервис для работы с LLM через Ollama.

Сервис запускается на твоём ПК, принимает HTTP-запросы и проксирует их в локальную модель.
Снаружи доступ идёт только через HTTPS (Cloudflare Tunnel).

---

## Что делает сервис

* принимает текст задачи или MR
* отправляет его в локальную модель (Ollama)
* возвращает результат в виде JSON
* защищён API-ключом

---

## Чего здесь нет

* нет базы данных
* нет пользователей и ролей
* нет UI
* нет сложной логики
* нет универсальности

Это просто API для одного сценария.

---

## Как это устроено

```text
клиент → HTTPS → Cloudflare Tunnel → FastAPI → Ollama → модель
```

* Ollama доступна только внутри Docker
* FastAPI доступен только локально (`127.0.0.1`)
* наружу выходит только через туннель

---

## Файлы

```text
llm-gateway/
  .env.example
  docker-compose.yml
  README.md
  api/
    Dockerfile
    requirements.txt
    main.py
    prompt.txt
```

---

## Подготовка

```powershell
cd C:\AI\llm-gateway
copy .env.example .env
notepad .env
```

Пример `.env`:

```env
AI_API_KEY=your-secret-key
OLLAMA_MODEL=deepseek-r1:7b
OLLAMA_URL=http://ollama:11434
REVIEW_TIMEOUT_SECONDS=300
```

Поменяй `AI_API_KEY` на свой.

---

## Запуск

```powershell
docker compose up -d --build
```

---

## Скачать модель

```powershell
docker exec -it llm-gateway-ollama ollama pull deepseek-r1:7b
```

Проверить:

```powershell
docker exec -it llm-gateway-ollama ollama list
```

---

## Проверка

```powershell
Invoke-RestMethod http://localhost:8000/health
```

---

## Пример запроса

Важно: поле `text` обязательно.

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    text = @"
Нужно доработать проведение документа "Реализация товаров и услуг".
Проверять лимит контрагента и уведомлять пользователя при превышении.
"@
} | ConvertTo-Json -Depth 10

$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/review-task" `
  -Headers @{ "X-API-Key" = "your-secret-key" } `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes
```

---

## Доступ извне

Посмотреть адрес:

```powershell
docker logs llm-gateway-cloudflared
```

Будет что-то вроде:

```text
https://something.trycloudflare.com
```

Запрос такой же, только меняешь URL:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "https://something.trycloudflare.com/review-task" `
  -Headers @{ "X-API-Key" = "your-secret-key" } `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes
```

---

## Остановка

```powershell
docker compose down
```

---

## Логи

```powershell
docker compose logs -f api
docker compose logs -f ollama
docker compose logs -f cloudflared
```

---

## Автор

Aleksandr Geints  
GitHub: https://github.com/your-username