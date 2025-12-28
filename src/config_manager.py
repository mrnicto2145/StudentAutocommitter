# src/config_manager.py
"""
Менеджер конфигурации для Student Autocommiter
Управляет загрузкой, сохранением и валидацией конфигурации
"""

import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass


class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация менеджера конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации. 
                        Если None, используется путь по умолчанию.
        """
        self.config_dir = self._get_config_dir()
        self.default_config_path = os.path.join(self.config_dir, "default_config.yaml")
        self.user_config_path = config_path or os.path.join(self.config_dir, "user_config.yaml")
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Валидируем конфигурацию
        self._validate_config()
        
        logger.info(f"Configuration loaded from: {self.user_config_path}")
    
    def _get_config_dir(self) -> str:
        """Получаем путь к директории конфигурации"""
        # Пытаемся найти config/ в текущей директории
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # Поднимаемся на уровень выше src/
        
        config_dir = os.path.join(project_root, "config")
        
        # Если директории нет - создаем
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            
            # Создаем конфигурацию по умолчанию
            self._create_default_config(config_dir)
        
        return config_dir
    
    def _create_default_config(self, config_dir: str) -> None:
        """Создает конфигурационные файлы по умолчанию"""
        
        # Основная конфигурация
        default_config = {
            "repository": {
                "url": "",
                "local_path": "./workspace",
                "branch": "main",
                "remote_name": "origin",
                "auto_fetch": True,
                "auto_pull": False
            },
            "commit_settings": {
                "enabled": True,
                "min_commits_per_day": 1,
                "max_commits_per_day": 5,
                "active_hours": {
                    "start": 9,
                    "end": 21
                },
                "weekend_activity": False,
                "commit_patterns": ["peak_morning", "peak_evening"],
                "min_time_between_commits": 30,  # минут
                "max_time_between_commits": 240  # минут
            },
            "auto_start": {
                "enabled": False,
                "startup_method": "registry",  # registry, task_scheduler, service
                "delay_minutes": 5,
                "run_at_startup": False
            },
            "error_handling": {
                "retry_attempts": 3,
                "retry_delay_minutes": 30,
                "queue_failed_commits": True,
                "max_queue_size": 50,
                "notify_on_error": False
            },
            "stealth_mode": {
                "enabled": True,
                "random_delays": True,
                "vary_commit_times": True,
                "realistic_messages": True,
                "mixed_file_types": True,
                "max_changes_per_commit": 10
            },
            "notifications": {
                "enabled": False,
                "type": "console",  # console, email, webhook, file
                "email": "",
                "webhook_url": "",
                "log_file": "./logs/activity.log"
            },
            "patterns": {
                "commit_messages_file": "./config/patterns/commit_messages.txt",
                "code_snippets_dir": "./config/patterns/code_snippets",
                "file_patterns": "./config/patterns/file_patterns.json"
            },
            "logging": {
                "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
                "file": "./logs/autocommiter.log",
                "max_size_mb": 10,
                "backup_count": 5
            },
            "security": {
                "require_confirmation": True,
                "max_commits_per_run": 100,
                "shutdown_after_hours": 24
            }
        }
        
        # Сохраняем default_config.yaml
        default_path = os.path.join(config_dir, "default_config.yaml")
        with open(default_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        # Создаем user_config.yaml как копию default
        user_path = os.path.join(config_dir, "user_config.yaml")
        with open(user_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        # Создаем директорию для паттернов
        patterns_dir = os.path.join(config_dir, "patterns")
        os.makedirs(patterns_dir, exist_ok=True)
        
        # Создаем файл с сообщениями для коммитов
        messages_file = os.path.join(patterns_dir, "commit_messages.txt")
        default_messages = [
            "Fix bug in {module}",
            "Add {feature} functionality",
            "Refactor {component} for better performance",
            "Update documentation for {file}",
            "Improve error handling in {module}",
            "Optimize {component} memory usage",
            "Add unit tests for {module}",
            "Fix typo in {file}",
            "Update dependencies",
            "Clean up unused imports",
            "Improve code readability",
            "Add comments for clarity",
            "Fix formatting issues",
            "Update configuration",
            "Add validation for {component}",
            "Fix security vulnerability in {module}",
            "Improve logging",
            "Add new feature: {feature}",
            "Fix null pointer exception",
            "Update README.md"
        ]
        
        with open(messages_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(default_messages))
        
        # Создаем директорию для сниппетов кода
        snippets_dir = os.path.join(patterns_dir, "code_snippets")
        os.makedirs(snippets_dir, exist_ok=True)
        
        # Создаем пример сниппета Python
        python_snippet = os.path.join(snippets_dir, "python_example.py")
        with open(python_snippet, 'w', encoding='utf-8') as f:
            f.write("""def calculate_average(numbers):
    \"\"\"Calculate the average of a list of numbers.\"\"\"
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)


def find_max_value(data):
    \"\"\"Find the maximum value in a list.\"\"\"
    if not data:
        return None
    return max(data)


class DataProcessor:
    \"\"\"Process data with various operations.\"\"\"
    
    def __init__(self, data):
        self.data = data
    
    def normalize(self):
        \"\"\"Normalize data to range [0, 1].\"\"\"
        if not self.data:
            return []
        
        min_val = min(self.data)
        max_val = max(self.data)
        
        if max_val == min_val:
            return [0] * len(self.data)
        
        return [(x - min_val) / (max_val - min_val) for x in self.data]
""")
        
        # Создаем файл с паттернами имен файлов
        patterns_file = os.path.join(patterns_dir, "file_patterns.json")
        default_patterns = {
            "python": ["*.py"],
            "javascript": ["*.js", "*.jsx", "*.ts", "*.tsx"],
            "html": ["*.html", "*.htm"],
            "css": ["*.css", "*.scss", "*.less"],
            "documentation": ["*.md", "*.txt", "*.rst"],
            "configuration": ["*.json", "*.yaml", "*.yml", "*.ini", "*.cfg"],
            "data": ["*.csv", "*.xml", "*.sql"]
        }
        
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(default_patterns, f, indent=2)
        
        logger.info(f"Created default configuration in {config_dir}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файлов"""
        
        # Если пользовательский конфиг не существует, используем дефолтный
        if not os.path.exists(self.user_config_path):
            logger.warning(f"User config not found at {self.user_config_path}, using default")
            config_path = self.default_config_path
        else:
            config_path = self.user_config_path
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # Загружаем дефолтную конфигурацию для заполнения недостающих значений
            if config_path != self.default_config_path and os.path.exists(self.default_config_path):
                with open(self.default_config_path, 'r', encoding='utf-8') as f:
                    default_config = yaml.safe_load(f) or {}
                
                # Рекурсивно мержим конфигурации
                config = self._merge_configs(default_config, config)
            
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            raise ConfigError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Рекурсивно объединяет две конфигурации"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self) -> None:
        """Валидирует загруженную конфигурацию"""
        errors = []
        
        # Проверка обязательных полей
        required_fields = [
            "repository.local_path",
            "commit_settings.min_commits_per_day",
            "commit_settings.max_commits_per_day"
        ]
        
        for field in required_fields:
            if self.get(field) is None:
                errors.append(f"Missing required field: {field}")
        
        # Проверка значений
        min_commits = self.get("commit_settings.min_commits_per_day")
        max_commits = self.get("commit_settings.max_commits_per_day")
        
        if min_commits is not None and max_commits is not None:
            if min_commits > max_commits:
                errors.append("min_commits_per_day cannot be greater than max_commits_per_day")
            if min_commits < 0:
                errors.append("min_commits_per_day cannot be negative")
            if max_commits > 100:
                errors.append("max_commits_per_day is too high (max 100)")
        
        # Проверка часов активности
        start_hour = self.get("commit_settings.active_hours.start")
        end_hour = self.get("commit_settings.active_hours.end")
        
        if start_hour is not None and end_hour is not None:
            if not (0 <= start_hour <= 23):
                errors.append("active_hours.start must be between 0 and 23")
            if not (0 <= end_hour <= 23):
                errors.append("active_hours.end must be between 0 and 23")
            if start_hour >= end_hour:
                errors.append("active_hours.start must be less than active_hours.end")
        
        if errors:
            error_msg = "\n".join(errors)
            logger.error(f"Configuration validation failed:\n{error_msg}")
            raise ConfigError(f"Invalid configuration:\n{error_msg}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение конфигурации по ключу (dot notation)
        
        Args:
            key: Ключ в формате 'section.subsection.key'
            default: Значение по умолчанию, если ключ не найден
        
        Returns:
            Значение конфигурации или default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any, save: bool = False) -> None:
        """
        Устанавливает значение конфигурации
        
        Args:
            key: Ключ в формате 'section.subsection.key'
            value: Новое значение
            save: Сохранять ли изменения в файл
        """
        keys = key.split('.')
        config = self.config
        
        # Проходим по всем ключам кроме последнего
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Устанавливаем значение
        config[keys[-1]] = value
        
        if save:
            self.save()
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Сохраняет текущую конфигурацию в файл
        
        Args:
            path: Путь для сохранения. Если None, используется user_config_path
        """
        save_path = path or self.user_config_path
        
        # Создаем директорию, если ее нет
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuration saved to: {save_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigError(f"Failed to save configuration: {e}")
    
    def reload(self) -> None:
        """Перезагружает конфигурацию из файла"""
        self.config = self._load_config()
        self._validate_config()
        logger.info("Configuration reloaded")
    
    def reset_to_default(self) -> None:
        """Сбрасывает конфигурацию к значениям по умолчанию"""
        if os.path.exists(self.default_config_path):
            with open(self.default_config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
            
            self.save()
            logger.info("Configuration reset to default values")
        else:
            logger.error("Default configuration file not found")
    
    def get_all(self) -> Dict[str, Any]:
        """Возвращает всю конфигурацию"""
        return self.config.copy()
    
    def print_config(self, section: Optional[str] = None) -> None:
        """
        Выводит конфигурацию в консоль
        
        Args:
            section: Опциональная секция для вывода. Если None, выводит все.
        """
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print(" " * indent + f"{key}:")
                    print_dict(value, indent + 2)
                else:
                    print(" " * indent + f"{key}: {value}")
        
        if section:
            config_to_print = self.get(section)
            if config_to_print:
                print(f"\n{section}:")
                if isinstance(config_to_print, dict):
                    print_dict(config_to_print, 2)
                else:
                    print(f"  {config_to_print}")
            else:
                print(f"Section '{section}' not found")
        else:
            print("\nCurrent Configuration:")
            print_dict(self.config)
    
    def export_to_json(self, path: str) -> None:
        """Экспортирует конфигурацию в JSON файл"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration exported to JSON: {path}")
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            raise ConfigError(f"Failed to export configuration: {e}")


# Утилитарные функции
def get_config_dir() -> str:
    """Возвращает путь к директории конфигурации"""
    return os.path.dirname(os.path.abspath(__file__))


def create_sample_config(output_path: str) -> None:
    """Создает пример конфигурационного файла"""
    sample_config = {
        "repository": {
            "url": "https://github.com/username/project.git",
            "local_path": "C:/Projects/my_project",
            "branch": "main"
        },
        "commit_settings": {
            "min_commits_per_day": 2,
            "max_commits_per_day": 6,
            "active_hours": {
                "start": 10,
                "end": 20
            }
        }
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"Sample configuration created at: {output_path}")