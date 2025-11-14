#!/usr/bin/env python3
"""
Скрипт для проверки совместимости окружения
Убедитесь, что все требования выполнены перед запуском бота
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Проверить версию Python"""
    print("🐍 Проверка версии Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (требуется 3.9+)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro}")
        print("   Требуется Python 3.9 или выше")
        print("   Скачайте с https://www.python.org/downloads/")
        return False


def check_venv():
    """Проверить виртуальное окружение"""
    print("\n🔍 Проверка виртуального окружения...")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Виртуальное окружение активировано")
        return True
    else:
        print("⚠️  Виртуальное окружение НЕ активировано")
        print("   Выполните: source venv/bin/activate (Linux/Mac) или venv\\Scripts\\activate (Windows)")
        return False


def check_required_files():
    """Проверить наличие обязательных файлов"""
    print("\n📁 Проверка файлов проекта...")
    
    required_files = [
        'main.py',
        'config.py',
        '.env.example',
        'requirements.txt',
        'app/models.py',
        'app/handlers/user.py',
        'app/handlers/admin.py',
        'app/utils/db_utils.py',
        'app/utils/keyboards.py',
        'app/utils/helpers.py',
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} НЕ НАЙДЕН")
            all_exist = False
    
    return all_exist


def check_env_file():
    """Проверить файл .env"""
    print("\n⚙️  Проверка конфигурации...")
    
    if Path('.env').exists():
        print("✅ Файл .env существует")
        
        with open('.env', 'r') as f:
            content = f.read()
        
        if 'BOT_TOKEN' in content:
            if 'YOUR_BOT_TOKEN_HERE' in content:
                print("⚠️  BOT_TOKEN содержит значение по умолчанию")
                print("   Замените 'YOUR_BOT_TOKEN_HERE' на ваш реальный токен")
                return False
            else:
                print("✅ BOT_TOKEN установлен")
        else:
            print("❌ BOT_TOKEN не найден в файле .env")
            return False
        
        if 'ADMIN_IDS' in content:
            if '123456789' in content and ',' not in content.split('ADMIN_IDS=')[1].split('\n')[0]:
                print("⚠️  ADMIN_IDS содержит значение по умолчанию")
                print("   Замените на ваш реальный Telegram ID")
                return False
            else:
                print("✅ ADMIN_IDS установлен")
        else:
            print("❌ ADMIN_IDS не найден в файле .env")
            return False
        
        return True
    else:
        print("❌ Файл .env НЕ НАЙДЕН")
        print("   Выполните: cp .env.example .env")
        return False


def check_dependencies():
    """Проверить наличие зависимостей"""
    print("\n📦 Проверка установленных пакетов...")
    
    required_packages = {
        'aiogram': '3.2.0',
        'sqlalchemy': '2.0.23',
        'aiosqlite': '3.14.0',
        'dotenv': '1.0.0',
    }
    
    try:
        import pkg_resources
    except ImportError:
        print("❌ pkg_resources недоступен")
        return False
    
    all_installed = True
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    for package, version in required_packages.items():
        if package.lower() in installed_packages:
            installed_version = installed_packages[package.lower()]
            print(f"✅ {package} (установлена версия {installed_version})")
        else:
            print(f"❌ {package} НЕ УСТАНОВЛЕН")
            all_installed = False
    
    if not all_installed:
        print("\n📥 Установите зависимости:")
        print("   pip install -r requirements.txt")
    
    return all_installed


def check_directories():
    """Проверить директории"""
    print("\n📂 Проверка директорий...")
    
    directories = [
        'app',
        'app/handlers',
        'app/utils',
        'data',
        'data/uploads',
    ]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ НЕ НАЙДЕНА")
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✨ Директория создана")


def check_database():
    """Проверить базу данных"""
    print("\n💾 Проверка базы данных...")
    
    if Path('data/bot.db').exists():
        print("✅ База данных существует (data/bot.db)")
        return True
    else:
        print("⚠️  База данных еще не создана")
        print("   Она будет создана при первом запуске бота")
        return True


def main():
    """Главная функция проверки"""
    print("\n" + "="*60)
    print("🔍 ПРОВЕРКА СОВМЕСТИМОСТИ ОКРУЖЕНИЯ")
    print("="*60 + "\n")
    
    checks = [
        ("Python версия", check_python_version),
        ("Файлы проекта", check_required_files),
        ("Директории", check_directories),
        ("Конфигурация (.env)", check_env_file),
        ("Установленные пакеты", check_dependencies),
        ("База данных", check_database),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"⚠️  Ошибка при проверке {name}: {e}")
            results[name] = False
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ")
    print("="*60 + "\n")
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("\nВы можете запустить бота:")
        print("  python main.py")
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ")
        print("\nПожалуйста, выполните необходимые действия выше")
        print("и запустите эту проверку еще раз")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
