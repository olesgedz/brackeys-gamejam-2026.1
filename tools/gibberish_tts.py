#!/usr/bin/env python3
"""
Генератор белиберды с сохранением ритма английского текста.

Usage:
    python gibberish_tts.py "Hello, my name is John. How are you?" output.wav
    python gibberish_tts.py "text" output.wav --preset male1
    python gibberish_tts.py "text" output.wav --preset female2 --no-fx
    python gibberish_tts.py --list-presets
"""

import argparse
import random
import re
import subprocess
import tempfile
import os
from pathlib import Path

# Фонемы для генерации
CONSONANTS = ['b', 'd', 'g', 'k', 'm', 'n', 'p', 'r', 'l', 'v', 'ch', 'br', 'dr', 'gr', 'kr', 'pr', 'tr']
VOWELS = ['a', 'e', 'i', 'o', 'u', 'a', 'o', 'u']  # a, o, u чаще для "бубнящего" звука
ENDINGS = ['', 'n', 'm', 'k', 'r', 'l', 's', '']

# Пресеты голосов
PRESETS = {
    # Мужские голоса
    'male1': {
        'voice': 'en+m1', 'speed': 135, 'pitch': 20, 'gap': 2,
        'desc': 'Стандартный мужской'
    },
    'male2': {
        'voice': 'en+m2', 'speed': 135, 'pitch': 10, 'gap': 2,
        'desc': 'Резкий мужской'
    },
    'male3': {
        'voice': 'en+m3', 'speed': 135, 'pitch': 5, 'gap': 2,
        'desc': 'Глубокий мужской'
    },
    'male4': {
        'voice': 'en+m7', 'speed': 130, 'pitch': 1, 'gap': 2,
        'desc': 'Хриплый/старый мужской'
    },
    
    # Женские голоса
    'female1': {
        'voice': 'en+f1', 'speed': 140, 'pitch': 65, 'gap': 2,
        'desc': 'Стандартный женский'
    },
    'female2': {
        'voice': 'en+f2', 'speed': 140, 'pitch': 75, 'gap': 2,
        'desc': 'Мягкий женский'
    },
    'female3': {
        'voice': 'en+f3', 'speed': 135, 'pitch': 70, 'gap': 2,
        'desc': 'Низкий женский'
    },
    'female4': {
        'voice': 'en+f4', 'speed': 145, 'pitch': 80, 'gap': 2,
        'desc': 'Высокий женский'
    },
    
    # Детские голоса
    'child1': {
        'voice': 'en+f4', 'speed': 150, 'pitch': 99, 'gap': 2,
        'desc': 'Ребёнок (высокий)'
    },
    'child2': {
        'voice': 'en+f3', 'speed': 155, 'pitch': 95, 'gap': 2,
        'desc': 'Ребёнок (средний)'
    },
    'child3': {
        'voice': 'en+m1', 'speed': 150, 'pitch': 90, 'gap': 2,
        'desc': 'Мальчик'
    },
    'child4': {
        'voice': 'en+f5', 'speed': 160, 'pitch': 99, 'gap': 1,
        'desc': 'Маленький ребёнок'
    },
}

# Постобработка по умолчанию
DEFAULT_FX = {
    'noise': 0.1,
    'highpass': 300,
    'lowpass': 3000,
    'eq_freq': 1000,
    'eq_gain': 5,
    'echo_delays': '40|60',
    'echo_decays': '0.5|0.3',
}


def generate_syllable() -> str:
    """Генерирует один слог."""
    return random.choice(CONSONANTS) + random.choice(VOWELS) + random.choice(ENDINGS)


def generate_word(length_hint: int) -> str:
    """Генерирует слово примерно заданной длины."""
    num_syllables = max(1, length_hint // 3)
    num_syllables = min(num_syllables, 4)
    return ''.join(generate_syllable() for _ in range(num_syllables))


def text_to_gibberish(text: str) -> str:
    """Конвертирует текст в белиберду, сохраняя паузы."""
    result = []
    tokens = re.findall(r"[a-zA-Z']+|[.,!?;:\-]+|\s+", text)
    
    for token in tokens:
        if re.match(r"[a-zA-Z']+", token):
            gibberish = generate_word(len(token))
            result.append(gibberish)
        elif re.match(r"[.,;:\-]", token):
            result.append(' ...')
        elif re.match(r"[!?]", token):
            result.append(' .....')
        elif token.strip() == '':
            result.append(' ')
    
    return ''.join(result)


def generate_audio(text: str, output_path: str, voice: str = 'en+m1', 
                   speed: int = 135, pitch: int = 15, gap: int = 2,
                   apply_fx: bool = True, fx: dict = None) -> None:
    """Генерирует аудио через espeak-ng + ffmpeg постобработка."""
    
    if fx is None:
        fx = DEFAULT_FX
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # espeak-ng генерация
        cmd_espeak = [
            'espeak-ng',
            '-v', voice,
            '-s', str(speed),
            '-p', str(pitch),
            '-g', str(gap),
            '-w', tmp_path,
            text
        ]
        subprocess.run(cmd_espeak, check=True, capture_output=True)
        
        if apply_fx:
            # Получаем длительность
            result = subprocess.run(
                ['ffprobe', '-i', tmp_path, '-show_entries', 'format=duration', 
                 '-v', 'quiet', '-of', 'csv=p=0'],
                capture_output=True, text=True
            )
            duration = float(result.stdout.strip())
            
            # Фильтр постобработки
            af_filter = (
                f"highpass=f={fx['highpass']},"
                f"lowpass=f={fx['lowpass']},"
                f"equalizer=f={fx['eq_freq']}:t=h:w=500:g={fx['eq_gain']},"
                f"aecho=0.8:0.75:{fx['echo_delays']}:{fx['echo_decays']}"
            )
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_noise:
                tmp_noise_path = tmp_noise.name
            
            # Генерируем шум и микшируем
            cmd_ffmpeg = [
                'ffmpeg', '-y',
                '-f', 'lavfi', '-i', f"anoisesrc=d={duration}:c=pink:a={fx['noise']}",
                '-i', tmp_path,
                '-filter_complex', f"[0][1]amix=inputs=2:duration=shortest,{af_filter}",
                output_path
            ]
            subprocess.run(cmd_ffmpeg, check=True, capture_output=True)
        else:
            # Без постобработки - просто копируем
            import shutil
            shutil.copy(tmp_path, output_path)
        
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def list_presets():
    """Выводит список пресетов."""
    print("\n📢 Доступные пресеты голосов:\n")
    
    print("👨 МУЖСКИЕ:")
    for name, p in PRESETS.items():
        if name.startswith('male'):
            print(f"  {name:10} - {p['desc']:25} (voice={p['voice']}, pitch={p['pitch']}, speed={p['speed']})")
    
    print("\n👩 ЖЕНСКИЕ:")
    for name, p in PRESETS.items():
        if name.startswith('female'):
            print(f"  {name:10} - {p['desc']:25} (voice={p['voice']}, pitch={p['pitch']}, speed={p['speed']})")
    
    print("\n👶 ДЕТСКИЕ:")
    for name, p in PRESETS.items():
        if name.startswith('child'):
            print(f"  {name:10} - {p['desc']:25} (voice={p['voice']}, pitch={p['pitch']}, speed={p['speed']})")
    
    print("\n🎛️  Постобработка по умолчанию:")
    print(f"  noise={DEFAULT_FX['noise']}, highpass={DEFAULT_FX['highpass']}Hz, "
          f"lowpass={DEFAULT_FX['lowpass']}Hz, echo={DEFAULT_FX['echo_delays']}ms")
    print()


def main():
    parser = argparse.ArgumentParser(description='Генератор белиберды с ритмом текста')
    parser.add_argument('input', nargs='?', help='Текст или путь к .txt файлу')
    parser.add_argument('output', nargs='?', help='Путь для выходного .wav файла')
    parser.add_argument('--preset', '-p', choices=list(PRESETS.keys()), help='Пресет голоса')
    parser.add_argument('--voice', help='espeak-ng голос (например en+m3)')
    parser.add_argument('--pitch', type=int, help='Pitch 0-99')
    parser.add_argument('--speed', type=int, help='Скорость слов/мин')
    parser.add_argument('--gap', type=int, help='Пауза между словами')
    parser.add_argument('--no-fx', action='store_true', help='Без постобработки')
    parser.add_argument('--noise', type=float, help='Уровень шума (0-1)')
    parser.add_argument('--lowpass', type=int, help='Lowpass фильтр Hz')
    parser.add_argument('--highpass', type=int, help='Highpass фильтр Hz')
    parser.add_argument('--show-gibberish', action='store_true', help='Показать текст')
    parser.add_argument('--list-presets', '-l', action='store_true', help='Список пресетов')
    
    args = parser.parse_args()
    
    if args.list_presets:
        list_presets()
        return
    
    if not args.input or not args.output:
        parser.print_help()
        return
    
    # Читаем входной текст
    if Path(args.input).exists():
        text = Path(args.input).read_text(encoding='utf-8')
    else:
        text = args.input
    
    # Базовые параметры из пресета или дефолтные
    if args.preset:
        preset = PRESETS[args.preset]
        voice = preset['voice']
        speed = preset['speed']
        pitch = preset['pitch']
        gap = preset['gap']
    else:
        voice = 'en+m1'
        speed = 135
        pitch = 15
        gap = 2
    
    # Переопределяем если указано явно
    if args.voice: voice = args.voice
    if args.speed: speed = args.speed
    if args.pitch: pitch = args.pitch
    if args.gap: gap = args.gap
    
    # FX параметры
    fx = DEFAULT_FX.copy()
    if args.noise: fx['noise'] = args.noise
    if args.lowpass: fx['lowpass'] = args.lowpass
    if args.highpass: fx['highpass'] = args.highpass
    
    # Генерируем белиберду
    gibberish = text_to_gibberish(text)
    
    if args.show_gibberish:
        print(f"Оригинал: {text}")
        print(f"Белиберда: {gibberish}")
    
    # Генерируем аудио
    generate_audio(
        gibberish, 
        args.output,
        voice=voice,
        speed=speed,
        pitch=pitch,
        gap=gap,
        apply_fx=not args.no_fx,
        fx=fx
    )
    
    print(f"✓ Сохранено: {args.output}")


if __name__ == '__main__':
    main()
