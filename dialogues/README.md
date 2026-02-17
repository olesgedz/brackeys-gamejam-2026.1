# Dialogue Audio Generation

Автоматическая генерация gibberish-озвучки для диалогов.

## Workflow

1. **Напиши диалоги** в `dialogues/*.json`:
```json
{
  "events": [
    {"character": "doctor", "text": "The patient needs treatment."},
    {"character": "nurse", "text": "I'll prepare everything."}
  ]
}
```

2. **Запусти генерацию**:
```bash
python tools/generate_dialogue_audio.py
```

3. **Результат**: 
   - Аудио в `sound/dialogues/<имя_диалога>/`
   - Формат: `<имя>_000.wav`, `<имя>_001.wav`, ...

## Персонажи и голоса

| Персонаж | Пресет | Описание |
|----------|--------|----------|
| `doctor` | male2 | Резкий мужской |
| `nurse` | female1 | Стандартный женский |
| `child` | child1 | Детский высокий |
| `old_man` | male4 | Хриплый старый |
| `woman` | female2 | Мягкий женский |
| `default` | male1 | Стандартный мужской |

## Команды

```bash
# Сгенерировать всё
python tools/generate_dialogue_audio.py

# Только посмотреть что будет (dry run)
python tools/generate_dialogue_audio.py --dry-run

# Один конкретный файл
python tools/generate_dialogue_audio.py --dialogue dialogues/intro.json

# Показать пресеты
python tools/generate_dialogue_audio.py --list-presets
```

## Требования

- Python 3.8+
- espeak-ng
- ffmpeg
- `tools/gibberish_tts.py` (уже в проекте)

## Интеграция с Dialogic

1. Включи плагин Dialogic в Godot (Project Settings → Plugins)
2. Создай Timeline в Dialogic
3. Для каждого Text Event укажи путь к аудио из `sound/dialogues/`

Или используй `.dtl` формат напрямую — скрипт понимает оба формата.
