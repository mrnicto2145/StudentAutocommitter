#!/usr/bin/env python3
# src/main.py

import os
import sys
import argparse
import logging
import time

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Добавляем родительскую директорию в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Импортируем наши модули
try:
    from src.config_manager import ConfigManager, create_sample_config
    from src.config_manager import get_config_dir as get_config_dir_func
    from src.git_operations import GitOperations, is_git_installed, get_git_version
    from src.commit_generator import CommitGenerator
    from src.scheduler import Scheduler
    from src.error_handler import ErrorHandler
    from src.system_integration import SystemIntegration

except ImportError:
    # Альтернативный импорт, если запускаем напрямую
    from config_manager import ConfigManager, create_sample_config
    from config_manager import get_config_dir as get_config_dir_func
    from git_operations import GitOperations, is_git_installed, get_git_version
    from commit_generator import CommitGenerator
    from scheduler import Scheduler
    from error_handler import ErrorHandler
    from system_integration import SystemIntegration


def show_ethical_warning():
    """Отображение этического предупреждения"""
    warning = """
    ⚠️  ETHICAL WARNING ⚠️
    
    STUDENT AUTOCOMMITER - EDUCATIONAL PURPOSES ONLY
    
    This tool demonstrates automation concepts and should NOT be used to:
    - Deceive teachers or professors
    - Falsify academic work
    - Misrepresent your contributions
    
    By using this tool, you agree to use it responsibly and ethically.
    You are solely responsible for your actions.
    
    Press Enter to continue or Ctrl+C to exit...
    """
    print(warning)
    try:
        input()
        return True
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return False


def init_command(config_path):
    """Команда инициализации"""
    print("Initializing Student Autocommiter...")
    
    # Создаем менеджер конфигурации (он сам создаст файлы по умолчанию)
    try:
        config = ConfigManager(config_path)
        print(f"✓ Configuration initialized at: {config.user_config_path}")
        print("\nPlease edit the configuration file with your settings:")
        print(f"  {config.user_config_path}")
        print("\nRequired settings to configure:")
        print("  1. repository.local_path - path to your Git repository")
        print("  2. commit_settings - adjust commit frequency as needed")
        return config
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return None


def config_command(config_path, action, key=None, value=None):
    """Команда работы с конфигурацией"""
    try:
        config = ConfigManager(config_path)
        
        if action == "show":
            if key:
                config.print_config(key)
            else:
                config.print_config()
        
        elif action == "get" and key:
            val = config.get(key)
            if val is not None:
                print(f"{key} = {val}")
            else:
                print(f"Key '{key}' not found")
        
        elif action == "set" and key and value is not None:
            # Парсим значение
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                value = float(value)
            
            config.set(key, value, save=True)
            print(f"✓ Updated {key} = {value}")
        
        elif action == "reset":
            confirm = input("Reset configuration to default? (y/N): ")
            if confirm.lower() == 'y':
                config.reset_to_default()
                print("✓ Configuration reset to default")
        
        elif action == "reload":
            config.reload()
            print("✓ Configuration reloaded")
        
        elif action == "validate":
            print("✓ Configuration is valid")
        
        elif action == "path":
            print(f"Config directory: {config.config_dir}")
            print(f"Default config: {config.default_config_path}")
            print(f"User config: {config.user_config_path}")
        
        else:
            print(f"Unknown config action: {action}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Config command failed: {e}")
        return False


def sample_command(output_path):
    """Создание примера конфигурации"""
    try:
        create_sample_config(output_path)
        print(f"✓ Sample configuration created at: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to create sample: {e}")
        return False


def start_command(config_path, background=False, test_mode=False):
    """Команда запуска автокоммиттера"""
    print("Starting Student Autocommiter...")
    
    try:
        # Загружаем конфигурацию
        config = ConfigManager(config_path)
        
        # Проверяем обязательные настройки
        repo_path = config.get("repository.local_path")
        if not repo_path or repo_path == "./workspace":
            print("✗ Please configure repository.local_path first")
            print("  Run: python main.py config set repository.local_path /path/to/your/repo")
            return False
        
        # Инициализируем компоненты
        print("Initializing components...")
        
        git_ops = GitOperations(config)
        commit_gen = CommitGenerator(config)
        error_handler = ErrorHandler(config)
        scheduler = Scheduler(config, git_ops, commit_gen)
        
        # Проверяем репозиторий
        print("Checking repository...")
        status = git_ops.get_status()
        
        if not status["is_repo"]:
            print("✗ Not a Git repository")
            return False
        
        print(f"✓ Repository: {status['path']}")
        print(f"✓ Branch: {status['branch']}")
        
        if status["last_commit"]:
            print(f"✓ Last commit: {status['last_commit']['hash']} - {status['last_commit']['message'][:50]}...")
        
        # Тестовый режим
        if test_mode:
            print("\n🔄 Test mode: Creating test commit...")
            success = scheduler.create_test_commit()
            if success:
                print("✓ Test commit created successfully")
                return True
            else:
                print("✗ Test commit failed")
                return False
        
        # Запуск планировщика
        print("\n🚀 Starting scheduler...")
        
        if background:
            print("Running in background mode...")
            print("Press Ctrl+C to stop")
        
        success = scheduler.start()
        
        if not success:
            print("✗ Failed to start scheduler")
            return False
        
        print("✓ Scheduler started successfully")
        print("\n📊 Current schedule:")
        
        # Показываем запланированные задачи
        scheduler_status = scheduler.get_status()
        print(f"  Commits created: {scheduler_status['stats']['commits_created']}")
        print(f"  Errors: {scheduler_status['stats']['errors']}")
        
        if scheduler_status['next_run']:
            print(f"  Next run: {scheduler_status['next_run']}")
        
        print(f"  Jobs scheduled: {scheduler_status['jobs_count']}")
        
        # Если не в фоновом режиме, ждем завершения
        if not background:
            print("\n⏳ Running... Press Ctrl+C to stop\n")
            
            try:
                # Бесконечный цикл ожидания
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n🛑 Stopping scheduler...")
                scheduler.stop()
                print("✓ Scheduler stopped")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to start: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def install_service_command(config_path, method='auto'):
    """Команда установки службы автозапуска"""
    print("Installing autocommiter service...")
    
    try:
        config = ConfigManager(config_path)
        sys_integration = SystemIntegration(config)
        
        if method == 'auto':
            # Автоматически определяем метод
            result = sys_integration.install_autostart()
        else:
            # Устанавливаем конкретный метод
            if method == 'registry':
                result = sys_integration._install_windows_registry()
            elif method == 'task_scheduler':
                result = sys_integration._install_windows_task_scheduler()
            else:
                print(f"✗ Unknown method: {method}")
                return False
        
        if result.get('success', False):
            print(f"✓ Service installed successfully using {result.get('method', 'unknown')}")
            
            # Сохраняем метод в конфигурации
            config.set("auto_start.startup_method", result.get('method'), save=True)
            config.set("auto_start.enabled", True, save=True)
            
            print("✓ Configuration updated")
            return True
        else:
            print(f"✗ Installation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to install service: {e}")
        return False

def uninstall_service_command(config_path):
    """Команда удаления службы"""
    print("Uninstalling autocommiter service...")
    
    try:
        config = ConfigManager(config_path)
        sys_integration = SystemIntegration(config)
        
        result = sys_integration.remove_autostart()
        
        if result.get('success', False):
            print(f"✓ Service uninstalled successfully")
            
            # Обновляем конфигурацию
            config.set("auto_start.enabled", False, save=True)
            print("✓ Configuration updated")
            
            return True
        else:
            print(f"✗ Uninstallation failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to uninstall service: {e}")
        return False

def test_commit_command(config_path):
    """Команда создания тестового коммита"""
    print("Creating test commit...")
    
    try:
        config = ConfigManager(config_path)
        
        # Проверяем репозиторий
        repo_path = config.get("repository.local_path")
        if not repo_path or repo_path == "./workspace":
            print("✗ Repository not configured")
            return False
        
        git_ops = GitOperations(config)
        commit_gen = CommitGenerator(config)
        
        # Генерируем изменения
        changes = commit_gen.generate_changes(repo_path)
        
        if not changes:
            print("✗ Failed to generate changes")
            return False
        
        # Генерируем сообщение
        message = commit_gen.generate_commit_message()
        
        print(f"Changes to be made ({len(changes)} files):")
        for filepath in changes.keys():
            print(f"  - {filepath}")
        
        print(f"\nCommit message: {message}")
        
        # Подтверждение
        confirm = input("\nCreate commit? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled")
            return False
        
        # Создаем коммит
        commit_hash = git_ops.create_commit(changes, message)
        
        print(f"\n✓ Commit created successfully!")
        print(f"  Hash: {commit_hash[:8]}")
        print(f"  Message: {message}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create test commit: {e}")
        return False

def stats_command(config_path):
    """Команда показа статистики"""
    print("Statistics:\n")
    
    try:
        config = ConfigManager(config_path)
        error_handler = ErrorHandler(config)
        
        stats = error_handler.get_statistics()
        
        if not stats:
            print("No statistics available")
            return True
        
        print(f"Total commits: {stats.get('total_commits', 0)}")
        print(f"Successful: {stats.get('successful_commits', 0)}")
        print(f"Failed: {stats.get('failed_commits', 0)}")
        print(f"Pending: {stats.get('pending_commits', 0)}")
        
        if stats.get('success_rate_percent'):
            print(f"Success rate: {stats['success_rate_percent']}%")
        
        if stats.get('start_time'):
            print(f"Start time: {stats['start_time']}")
        
        if stats.get('last_update'):
            print(f"Last update: {stats['last_update']}")
        
        # Показываем последние ошибки
        print("\nRecent errors:")
        errors = error_handler.get_error_summary(3)
        
        if errors:
            for error in errors:
                print(f"  - {error['timestamp']}: {error['error_type']} - {error['error_message'][:50]}...")
        else:
            print("  No errors recorded")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to get statistics: {e}")
        return False

def status_command(config_path):
    """Команда проверки статуса репозитория"""
    print("Checking repository status...")
    
    if not is_git_installed():
        print("✗ Git is not installed or not in PATH")
        return False
    
    git_version = get_git_version()
    print(f"✓ Git version: {git_version}")
    
    try:
        config = ConfigManager(config_path)
        git_ops = GitOperations(config)
        
        status = git_ops.get_status()
        
        print(f"\nRepository: {status['path']}")
        print(f"Branch: {status['branch'] or 'N/A'}")
        print(f"Has remote: {status['has_remote']}")
        
        if status['last_commit']:
            print(f"Last commit: {status['last_commit']['hash']} - {status['last_commit']['message']}")
        
        print(f"\nUntracked files: {len(status['untracked_files'])}")
        print(f"Modified files: {len(status['modified_files'])}")
        print(f"Staged files: {len(status['staged_files'])}")
        
        if status['modified_files']:
            print("\nModified files:")
            for file in status['modified_files'][:5]:  # Показываем первые 5
                print(f"  - {file}")
            if len(status['modified_files']) > 5:
                print(f"  ... and {len(status['modified_files']) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to get status: {e}")
        return False

def history_command(config_path, limit=10):
    """Команда просмотра истории коммитов"""
    print(f"Showing last {limit} commits...")
    
    try:
        config = ConfigManager(config_path)
        git_ops = GitOperations(config)
        
        history = git_ops.get_commit_history(limit)
        
        if not history:
            print("No commits found")
            return True
        
        for i, commit in enumerate(history, 1):
            print(f"\n{i}. {commit['hash']} - {commit['message']}")
            print(f"   Author: {commit['author']}")
            print(f"   Date: {commit['date']}")
            print(f"   Files changed: {commit['files_changed']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to get history: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Student Autocommiter - Automated Git commits (Educational Use Only)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init                        # Initialize configuration
  %(prog)s config show                 # Show all configuration
  %(prog)s config get repository.url   # Get specific setting
  %(prog)s config set commit_settings.min_commits_per_day 3  # Update setting
  %(prog)s start                       # Start autocommiter service
  %(prog)s sample ./my_config.yaml     # Create sample config
        
Use responsibly and ethically!
        """
    )
    
    # Основные аргументы
    parser.add_argument('--config', '-c', type=str, default=None,
                       help='Path to configuration file (default: config/user_config.yaml)')
    
    # Субкоманды
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Команда init
    init_parser = subparsers.add_parser('init', help='Initialize configuration')
    
    # Команда config
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('action', choices=['show', 'get', 'set', 'reset', 'reload', 'validate', 'path'],
                              help='Config action to perform')
    config_parser.add_argument('key', nargs='?', help='Configuration key (for get/set)')
    config_parser.add_argument('value', nargs='?', help='Value to set (for set action)')
    
    # Команда start
    start_parser = subparsers.add_parser('start', help='Start autocommiter service')
    start_parser.add_argument('--background', '-b', action='store_true', 
                            help='Run in background')
    start_parser.add_argument('--test', '-t', action='store_true',
                            help='Test mode (create one commit and exit)')
    
    # Команда sample
    sample_parser = subparsers.add_parser('sample', help='Create sample configuration')
    sample_parser.add_argument('output', type=str, help='Output path for sample config')
    
    # Команда status
    status_parser = subparsers.add_parser('status', help='Check service status')

    # Команда history
    history_parser = subparsers.add_parser('history', help='Show commit history')
    history_parser.add_argument('--limit', '-l', type=int, default=10, help='Number of commits to show')

    # Команда uninstall-service
    uninstall_parser = subparsers.add_parser('uninstall-service', help='Remove startup service')

    # Команда test-commit
    test_parser = subparsers.add_parser('test-commit', help='Create a test commit')

    # Команда stats
    stats_parser = subparsers.add_parser('stats', help='Show statistics')

    
    # Парсим аргументы
    args = parser.parse_args()
    
    # Если нет команды, показываем помощь
    if not args.command:
        parser.print_help()
        return
    
    # Показываем этическое предупреждение (кроме config и sample команд)
    if args.command not in ['config', 'sample']:
        if not show_ethical_warning():
            return
    
    # Определяем путь к конфигу
    config_path = args.config
    
    # Выполняем команду
    if args.command == 'init':
        init_command(config_path)
    
    elif args.command == 'config':
        config_command(config_path, args.action, args.key, args.value)
    
    elif args.command == 'start':
        start_command(config_path, args.background, args.test)
    
    elif args.command == 'sample':
        sample_command(args.output)
    
    elif args.command == 'status':
        print("Service status: Not yet implemented")
    
    elif args.command == 'status':
        status_command(config_path)

    elif args.command == 'history':
        history_command(config_path, args.limit)

    elif args.command == 'install-service':
        install_service_command(config_path, args.method)

    elif args.command == 'uninstall-service':
        uninstall_service_command(config_path)

    elif args.command == 'test-commit':
        test_commit_command(config_path)

    elif args.command == 'stats':
        stats_command(config_path)

    else:
        print(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()