#!/usr/bin/env python3
"""
Комплексный тест всех компонентов Student Autocommiter
Запуск: python test_all.py
"""

import os
import sys
import tempfile
import shutil
import json
import yaml
import subprocess
import time
from datetime import datetime
import random

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestRunner:
    def __init__(self):
        self.test_dir = None
        self.repo_dir = None
        self.config_file = None
        self.passed = 0
        self.failed = 0
        self.start_time = datetime.now()
        
    def setup(self):
        """Подготовка тестового окружения"""
        print("=" * 60)
        print("СТУДЕНТ АВТОКОММИТЕР - ТЕСТИРОВАНИЕ")
        print("=" * 60)
        
        # Создаем тестовую директорию
        self.test_dir = tempfile.mkdtemp(prefix="autocommiter_test_")
        self.repo_dir = os.path.join(self.test_dir, "test_repo")
        
        print(f"📁 Тестовая директория: {self.test_dir}")
        
        # Создаем тестовый Git репозиторий
        self._create_test_repo()
        
        # Создаем конфигурацию
        self._create_test_config()
        
        print("\n✅ Тестовое окружение подготовлено\n")
        
    def _create_test_repo(self):
        """Создает тестовый Git репозиторий"""
        os.makedirs(self.repo_dir, exist_ok=True)
        
        # Инициализируем Git репозиторий
        subprocess.run(["git", "init"], cwd=self.repo_dir, 
                      capture_output=True, check=True)
        
        # Настраиваем пользователя
        subprocess.run(["git", "config", "user.name", "Test User"], 
                      cwd=self.repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], 
                      cwd=self.repo_dir, capture_output=True)
        
        # Создаем начальные файлы
        initial_files = {
            "README.md": "# Test Repository\n\nFor autocommiter testing.\n",
            "src/main.py": "print('Hello, Autocommiter!')\n",
            "config/settings.json": '{"test": true}\n'
        }
        
        for filepath, content in initial_files.items():
            full_path = os.path.join(self.repo_dir, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Делаем первый коммит
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, 
                      capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], 
                      cwd=self.repo_dir, capture_output=True, check=True)
        
        print(f"  ✓ Создан тестовый репозиторий: {self.repo_dir}")
    
    def _create_test_config(self):
        """Создает тестовую конфигурацию"""
        self.config_file = os.path.join(self.test_dir, "test_config.yaml")
        
        config = {
            "repository": {
                "local_path": self.repo_dir,
                "branch": "main",
                "auto_push": False,
                "auto_fetch": False
            },
            "commit_settings": {
                "enabled": True,
                "min_commits_per_day": 1,
                "max_commits_per_day": 3,
                "active_hours": {
                    "start": 0,  # Круглосуточно для тестов
                    "end": 23
                },
                "weekend_activity": True,
                "min_time_between_commits": 1,
                "max_time_between_commits": 2
            },
            "stealth_mode": {
                "enabled": False,  # Отключаем для предсказуемости тестов
                "random_delays": False
            },
            "logging": {
                "level": "DEBUG",
                "file": os.path.join(self.test_dir, "test.log")
            },
            "error_handling": {
                "retry_attempts": 1,
                "queue_failed_commits": True
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print(f"  ✓ Создана конфигурация: {self.config_file}")
    
    def run_test(self, test_name, test_func):
        """Запускает тест и обрабатывает результат"""
        print(f"\n▶️  Тест: {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            if result:
                print(f"✅ УСПЕХ: {test_name}")
                self.passed += 1
                return True
            else:
                print(f"❌ ПРОВАЛ: {test_name}")
                self.failed += 1
                return False
        except Exception as e:
            print(f"🔥 ОШИБКА: {test_name}")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
            self.failed += 1
            return False
    
    def test_1_config_manager(self):
        """Тест менеджера конфигурации"""
        from src.config_manager import ConfigManager
        
        config = ConfigManager(self.config_file)
        
        # Проверяем загрузку конфигурации
        repo_path = config.get("repository.local_path")
        assert repo_path == self.repo_dir, "Неверный путь к репозиторию"
        
        # Проверяем настройки
        min_commits = config.get("commit_settings.min_commits_per_day")
        assert min_commits == 1, "Неверное min_commits_per_day"
        
        # Проверяем установку значений
        config.set("test.value", 123, save=False)
        test_value = config.get("test.value")
        assert test_value == 123, "Не работает set/get"
        
        print(f"   Загружено настроек: {len(config.get_all())}")
        return True
    
    def test_2_git_operations(self):
        """Тест операций с Git"""
        from src.git_operations import GitOperations, is_git_installed
        from src.config_manager import ConfigManager
        
        if not is_git_installed():
            print("   ⚠️ Git не установлен, пропускаем тест")
            return True  # Пропускаем, а не проваливаем
        
        config = ConfigManager(self.config_file)
        git_ops = GitOperations(config)
        
        # Проверяем статус
        status = git_ops.get_status()
        assert status["is_repo"] == True, "Не является Git репозиторием"
        assert status["branch"] == "main", "Неверная ветка"
        
        # Создаем тестовый коммит
        test_changes = {
            "test_file.txt": "Test content\n" + datetime.now().isoformat()
        }
        
        commit_hash = git_ops.create_commit(test_changes, "Test commit from unit test")
        assert len(commit_hash) >= 7, "Неверный хэш коммита"
        
        # Проверяем историю
        history = git_ops.get_commit_history(limit=2)
        assert len(history) >= 2, "Недостаточно коммитов в истории"
        assert history[0]["message"] == "Test commit from unit test", "Неверное сообщение коммита"
        
        print(f"   Создан коммит: {commit_hash[:8]}")
        print(f"   История: {len(history)} коммитов")
        return True
    
    def test_3_commit_generator(self):
        """Тест генератора коммитов"""
        from src.config_manager import ConfigManager
        from src.commit_generator import CommitGenerator
        
        config = ConfigManager(self.config_file)
        commit_gen = CommitGenerator(config)
        
        # Генерируем сообщения
        messages = []
        for _ in range(5):
            message = commit_gen.generate_commit_message()
            messages.append(message)
            assert message, "Пустое сообщение коммита"
        
        # Генерируем изменения
        changes = commit_gen.generate_changes(self.repo_dir)
        assert isinstance(changes, dict), "Изменения не являются словарем"
        
        # Проверяем содержимое изменений
        if changes:
            for filename, content in changes.items():
                assert filename, "Пустое имя файла"
                assert content is not None, "Пустое содержимое файла"
        
        print(f"   Сгенерировано сообщений: {len(set(messages))} уникальных")
        print(f"   Сгенерировано изменений: {len(changes)} файлов")
        return True
    
    def test_4_cli_commands(self):
        """Тест CLI команд"""
        # Тестируем основные команды через subprocess
        
        commands = [
            ["python", "src/main.py", "--config", self.config_file, "status"],
            ["python", "src/main.py", "--config", self.config_file, "history", "--limit", "2"],
            ["python", "src/main.py", "--config", self.config_file, "config", "show"],
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   Команда не удалась: {' '.join(cmd)}")
                print(f"   Ошибка: {result.stderr[:100]}")
                return False
        
        print("   CLI команды работают корректно")
        return True
    
    def test_5_test_commit_command(self):
        """Тест команды test-commit"""
        # Запускаем в автоматическом режиме (неинтерактивно)
        from src.config_manager import ConfigManager
        from src.git_operations import GitOperations
        from src.commit_generator import CommitGenerator
        
        config = ConfigManager(self.config_file)
        git_ops = GitOperations(config)
        
        # Получаем начальное состояние
        initial_history = git_ops.get_commit_history(limit=1)
        
        # Создаем тестовый коммит напрямую
        commit_gen = CommitGenerator(config)
        changes = commit_gen.generate_changes(self.repo_dir)
        message = commit_gen.generate_commit_message()
        
        if changes:
            commit_hash = git_ops.create_commit(changes, message)
            
            # Проверяем, что коммит создан
            final_history = git_ops.get_commit_history(limit=1)
            assert final_history[0]["hash"] == commit_hash[:8], "Коммит не добавлен в историю"
            
            print(f"   Создан тестовый коммит: {commit_hash[:8]}")
            print(f"   Сообщение: {message}")
        
        return True
    
    def test_6_error_handling(self):
        """Тест обработки ошибок"""
        from src.config_manager import ConfigManager
        from src.error_handler import ErrorHandler
        
        config = ConfigManager(self.config_file)
        error_handler = ErrorHandler(config)
        
        # Тестируем обработку ошибки
        test_error = Exception("Test error")
        error_info = {
            "test": "data",
            "timestamp": datetime.now().isoformat()
        }
        
        result = error_handler.handle_commit_error(test_error, error_info)
        assert "handled" in result, "Нет ключа 'handled' в результате"
        
        # Проверяем статистику
        stats = error_handler.get_statistics()
        assert "total_commits" in stats, "Нет статистики"
        
        # Проверяем очередь
        pending = error_handler.get_pending_commits()
        assert isinstance(pending, list), "Очередь не является списком"
        
        print(f"   Ошибки обрабатываются, очередь: {len(pending)}")
        return True
    
    def test_7_stealth_mode(self):
        """Тест режима 'стелс'"""
        from src.config_manager import ConfigManager
        from src.commit_generator import CommitGenerator
        
        # Включаем stealth mode
        config = ConfigManager(self.config_file)
        config.set("stealth_mode.enabled", True, save=True)
        config.set("stealth_mode.realistic_messages", True, save=True)
        
        commit_gen = CommitGenerator(config)
        
        # Генерируем несколько сообщений
        messages = []
        for _ in range(10):
            message = commit_gen.generate_commit_message()
            messages.append(message)
        
        # Проверяем разнообразие сообщений
        unique_messages = len(set(messages))
        assert unique_messages > 1, "Сообщения недостаточно разнообразны"
        
        print(f"   Сгенерировано {unique_messages} уникальных сообщений из 10")
        return True
    
    def test_8_scheduler_basic(self):
        """Тест базового функционала планировщика"""
        from src.config_manager import ConfigManager
        from src.git_operations import GitOperations
        from src.commit_generator import CommitGenerator
        from src.scheduler import Scheduler
        
        config = ConfigManager(self.config_file)
        git_ops = GitOperations(config)
        commit_gen = CommitGenerator(config)
        
        # Создаем планировщик
        scheduler = Scheduler(config, git_ops, commit_gen)
        
        # Проверяем инициализацию
        assert scheduler.is_running == False, "Планировщик не должен быть запущен"
        
        # Проверяем создание тестового коммита через планировщик
        success = scheduler.create_test_commit()
        assert success == True, "Не удалось создать тестовый коммит"
        
        print("   Планировщик инициализирован, тестовый коммит создан")
        return True
    
    def cleanup(self):
        """Очистка тестового окружения"""
        print("\n" + "=" * 60)
        print("ЗАВЕРШЕНИЕ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        
        execution_time = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"   Успешных тестов: {self.passed}")
        print(f"   Проваленных тестов: {self.failed}")
        print(f"   Всего тестов: {self.passed + self.failed}")
        print(f"   Время выполнения: {execution_time:.2f} сек")
        
        if self.failed == 0:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            print(f"\n⚠️  {self.failed} ТЕСТОВ ПРОВАЛЕНО")
        
        # Очистка тестовой директории
        if os.path.exists(self.test_dir):
            keep_test_data = input("\nСохранить тестовые данные? (y/N): ").lower() == 'y'
            if not keep_test_data:
                shutil.rmtree(self.test_dir)
                print(f"🗑️  Тестовая директория удалена: {self.test_dir}")
            else:
                print(f"💾 Тестовые данные сохранены: {self.test_dir}")
        
        return self.failed == 0
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        self.setup()
        
        tests = [
            ("Конфигурация", self.test_1_config_manager),
            ("Git операции", self.test_2_git_operations),
            ("Генератор коммитов", self.test_3_commit_generator),
            ("CLI команды", self.test_4_cli_commands),
            ("Тестовый коммит", self.test_5_test_commit_command),
            ("Обработка ошибок", self.test_6_error_handling),
            ("Режим 'стелс'", self.test_7_stealth_mode),
            ("Планировщик", self.test_8_scheduler_basic),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        return self.cleanup()


def main():
    """Основная функция"""
    runner = TestRunner()
    
    try:
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
        runner.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n🔥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()