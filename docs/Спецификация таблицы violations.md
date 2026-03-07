## Спецификация таблицы `violations`

### Назначение

Таблица `violations` предназначена для хранения всех зафиксированных системой нарушений правил ношения средств индивидуальной защиты (СИЗ).  
Каждая запись соответствует одному подтверждённому нарушению одного человека на одной камере.

## Схема таблицы

```sql
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    time TIME NOT NULL,
    camera_id TEXT NOT NULL,
    human_id INTEGER NOT NULL,
    violation_type TEXT NOT NULL CHECK (
        violation_type IN ('no_helmet', 'no_vest', 'no_gloves')
    ),
    confidence REAL NOT NULL CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    ),
    screenshot_path TEXT
);
```

---

## Описание полей

| Поле | Тип | Обязательное | Описание |
|-----|-----|-----|-----|
| id | INTEGER | Да | Уникальный автоинкрементный идентификатор записи. Первичный ключ. |
| date | DATE | Да | Дата фиксации нарушения в формате `YYYY-MM-DD`. |
| time | TIME | Да | Время фиксации нарушения в формате `HH:MM:SS`. |
| camera_id | TEXT | Да | Идентификатор источника видеопотока: IP-адрес (`192.168.1.101`) или логическое имя (`entrance`, `workshop`). |
| human_id | INTEGER | Да | Уникальный ID трека человека, присвоенный системой трекинга. Позволяет связывать события одного и того же человека. |
| violation_type | TEXT | Да | Тип нарушения. Возможные значения: `no_helmet`, `no_vest`, `no_gloves`. |
| confidence | REAL | Да | Уверенность модели в детекции (значение от `0.0` до `1.0`). Используется для анализа качества и фильтрации. |
| screenshot_path | TEXT | Нет | Относительный путь к файлу скриншота (например, `violations/frame_001234.jpg`). Может быть `NULL`, если файл удалён. |

---

## Ограничения (Constraints)

- `violation_type` ограничен списком допустимых значений через `CHECK`.
- `confidence` ограничен диапазоном `[0.0, 1.0]`.
- Все поля, кроме `screenshot_path`, обязательны (`NOT NULL`).

---
## Пример записи

```json
{
  "id": 1543,
  "date": "2026-03-07",
  "time": "14:25:31",
  "camera_id": "rtsp://localhost:8554/stream1",
  "human_id": 12,
  "violation_type": "no_helmet",
  "confidence": 0.92,
  "screenshot_path": "violations/frame_001234.jpg"
}
```

---

## Политика хранения

- Записи в таблице хранятся **не менее 1 года**.
- Файлы по пути `screenshot_path` автоматически удаляются **через 30 дней после создания**.
- При отсутствии файла `screenshot_path` может содержать `NULL`