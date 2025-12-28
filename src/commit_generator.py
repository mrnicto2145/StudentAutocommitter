# src/commit_generator.py
"""
Генератор реалистичных коммитов с изменениями
"""

import os
import random
import json
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class CommitGenerator:
    def __init__(self, config_manager):
        """
        Инициализация генератора коммитов

        Args:
            config_manager: Экземпляр ConfigManager
        """
        self.config = config_manager
        self.patterns_dir = self.config.get("patterns.path", "./config/patterns")

        # Загружаем шаблоны
        self.commit_messages = self._load_commit_messages()
        self.file_patterns = self._load_file_patterns()
        self.code_snippets = self._load_code_snippets()

        # История изменений для реалистичности
        self.change_history = {}

        logger.info("Commit generator initialized")

    def _load_commit_messages(self) -> List[str]:
        """Загружает шаблоны сообщений коммитов"""
        messages_file = self.config.get(
            "patterns.commit_messages_file", f"{self.patterns_dir}/commit_messages.txt"
        )

        try:
            if os.path.exists(messages_file):
                with open(messages_file, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.warning(f"Failed to load commit messages: {e}")

        # Шаблоны по умолчанию
        return [
            "Fix bug in {module}",
            "Add {feature} feature",
            "Update {file}",
            "Refactor {component}",
            "Improve {module} performance",
            "Add tests for {module}",
            "Fix typo in {file}",
            "Update dependencies",
            "Clean up code",
            "Add documentation",
            "Fix {issue} issue",
            "Optimize {component}",
            "Add error handling",
            "Update configuration",
            "Fix security issue",
            "Improve logging",
            "Add validation",
            "Update README",
            "Fix null pointer",
            "Add comments",
        ]

    def _load_file_patterns(self) -> Dict[str, List[str]]:
        """Загружает паттерны имен файлов"""
        patterns_file = self.config.get(
            "patterns.file_patterns", f"{self.patterns_dir}/file_patterns.json"
        )

        try:
            if os.path.exists(patterns_file):
                with open(patterns_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load file patterns: {e}")

        # Паттерны по умолчанию
        return {
            "python": ["*.py"],
            "javascript": ["*.js", "*.jsx"],
            "html": ["*.html", "*.htm"],
            "css": ["*.css", "*.scss"],
            "markdown": ["*.md"],
            "json": ["*.json"],
            "yaml": ["*.yaml", "*.yml"],
            "text": ["*.txt"],
        }

    def _load_code_snippets(self) -> Dict[str, str]:
        """Загружает сниппеты кода"""
        snippets_dir = self.config.get(
            "patterns.code_snippets_dir", f"{self.patterns_dir}/code_snippets"
        )

        snippets = {}

        try:
            if os.path.exists(snippets_dir):
                for file in os.listdir(snippets_dir):
                    if file.endswith(".py"):
                        filepath = os.path.join(snippets_dir, file)
                        with open(filepath, "r", encoding="utf-8") as f:
                            snippets[file] = f.read()
        except Exception as e:
            logger.warning(f"Failed to load code snippets: {e}")

        # Сниппеты по умолчанию
        if not snippets:
            snippets = {
                "function.py": """
def {function_name}({params}):
    \"\"\"{docstring}\"\"\"
    {implementation}
    return result
""",
                "class.py": """
class {class_name}:
    \"\"\"{docstring}\"\"\"
    
    def __init__(self, {init_params}):
        \"\"\"Initialize {class_name}.\"\"\"
        {init_implementation}
    
    def {method_name}(self, {method_params}):
        \"\"\"{method_docstring}\"\"\"
        {method_implementation}
        return result
""",
                "test.py": """
import unittest

class Test{ClassName}(unittest.TestCase):
    \"\"\"Test cases for {class_name}.\"\"\"
    
    def setUp(self):
        \"\"\"Set up test fixtures.\"\"\"
        {setup_code}
    
    def test_{test_case}(self):
        \"\"\"Test {test_case} functionality.\"\"\"
        {test_code}
        self.assertEqual(result, expected)
""",
            }

        return snippets

    def generate_commit_message(self) -> str:
        """Генерирует реалистичное сообщение коммита"""
        template = random.choice(self.commit_messages)

        # Заполняем плейсхолдеры
        replacements = {
            "{module}": random.choice(
                ["api", "database", "ui", "auth", "utils", "config"]
            ),
            "{feature}": random.choice(
                ["search", "filter", "export", "import", "validation", "cache"]
            ),
            "{file}": random.choice(
                ["README.md", "config.yaml", "utils.py", "main.py"]
            ),
            "{component}": random.choice(
                ["service", "controller", "model", "helper", "manager"]
            ),
            "{issue}": random.choice(
                ["memory leak", "race condition", "type error", "formatting"]
            ),
        }

        message = template
        for key, value in replacements.items():
            message = message.replace(key, value)

        # Добавляем детали
        detail_chance = random.random()
        if detail_chance > 0.7:
            details = [
                f" (fixes #{random.randint(1, 100)})",
                f" - improve performance",
                f" for better reliability",
                f" with additional tests",
            ]
            message += random.choice(details)

        # Добавляем эмодзи (опционально)
        if (
            self.config.get("stealth_mode.realistic_messages", True)
            and random.random() > 0.5
        ):
            emojis = ["🚀", "✨", "🐛", "🔧", "📝", "⚡", "🔒", "✅", "♻️", "📚"]
            message = f"{message} {random.choice(emojis)}"

        return message

    def generate_changes(self, repo_path: str) -> Dict[str, str]:
        """
        Генерирует реалистичные изменения файлов

        Args:
            repo_path: Путь к репозиторию

        Returns:
            Словарь {путь_к_файлу: содержимое}
        """
        changes = {}

        # Определяем тип изменения
        change_type = self._select_change_type()

        if change_type == "new_file":
            changes.update(self._generate_new_file(repo_path))

        elif change_type == "modify_existing":
            changes.update(self._modify_existing_file(repo_path))

        elif change_type == "refactor":
            changes.update(self._refactor_code(repo_path))

        elif change_type == "multiple":
            # Несколько небольших изменений
            for _ in range(random.randint(1, 3)):
                sub_type = self._select_change_type()
                if sub_type == "new_file":
                    changes.update(self._generate_new_file(repo_path))
                else:
                    changes.update(self._modify_existing_file(repo_path))

        # Ограничиваем количество изменений
        max_changes = self.config.get("stealth_mode.max_changes_per_commit", 5)
        if len(changes) > max_changes:
            # Оставляем только первые max_changes изменений
            changes = dict(list(changes.items())[:max_changes])

        logger.debug(f"Generated {len(changes)} changes of type: {change_type}")
        return changes

    def _select_change_type(self) -> str:
        """Выбирает тип изменения"""
        weights = {
            "new_file": 0.3,  # 30% - новый файл
            "modify_existing": 0.4,  # 40% - изменение существующего
            "refactor": 0.2,  # 20% - рефакторинг
            "multiple": 0.1,  # 10% - несколько изменений
        }

        return random.choices(list(weights.keys()), weights=list(weights.values()))[0]

    def _generate_new_file(self, repo_path: str) -> Dict[str, str]:
        """Генерирует новый файл"""
        # Выбираем тип файла
        file_types = list(self.file_patterns.keys())
        file_type = random.choice(file_types)

        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        if file_type == "python":
            filename = f"src/{random.choice(['utils', 'helpers', 'services', 'models'])}/module_{timestamp}.py"
            content = self._generate_python_file()
        elif file_type == "javascript":
            filename = f"js/{random.choice(['components', 'utils', 'services'])}/module_{timestamp}.js"
            content = self._generate_javascript_file()
        elif file_type == "markdown":
            filename = f"docs/{random.choice(['feature', 'api', 'usage'])}_notes.md"
            content = self._generate_markdown_file()
        else:
            filename = f"files/{file_type}_{timestamp}.txt"
            content = f"File created at {timestamp}\n\n"

        return {filename: content}

    def _modify_existing_file(self, repo_path: str) -> Dict[str, str]:
        """Модифицирует существующий файл"""
        # Ищем существующие файлы
        existing_files = []
        for root, dirs, files in os.walk(repo_path):
            # Игнорируем .git директорию
            if ".git" in root:
                continue

            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, repo_path)

                # Игнорируем бинарные файлы и специфичные
                if not any(
                    rel_path.endswith(ext) for ext in [".pyc", ".pyo", ".so", ".dll"]
                ):
                    existing_files.append(rel_path)

        if not existing_files:
            return self._generate_new_file(repo_path)

        # Выбираем случайный файл
        filename = random.choice(existing_files)
        filepath = os.path.join(repo_path, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Применяем изменения в зависимости от типа файла
            if filename.endswith(".py"):
                new_content = self._modify_python_file(content)
            elif filename.endswith(".md"):
                new_content = self._modify_markdown_file(content)
            elif filename.endswith((".js", ".jsx", ".ts", ".tsx")):
                new_content = self._modify_javascript_file(content)
            elif filename.endswith((".txt", ".rst")):
                new_content = self._modify_text_file(content)
            else:
                # Для других файлов - просто добавляем комментарий
                new_content = (
                    content + f"\n\n# Updated at {datetime.now().isoformat()}\n"
                )

            return {filename: new_content}

        except Exception as e:
            logger.warning(f"Failed to modify file {filename}: {e}")
            return {}

    def _generate_python_file(self) -> str:
        """Генерирует Python файл"""
        snippet = random.choice(list(self.code_snippets.values()))

        # Заполняем плейсхолдеры
        replacements = {
            "{function_name}": random.choice(
                ["process_data", "calculate_value", "validate_input", "format_output"]
            ),
            "{class_name}": random.choice(
                ["DataProcessor", "FileHandler", "ApiClient", "Validator"]
            ),
            "{params}": random.choice(["data", "input_data", "value", "items"]),
            "{docstring}": random.choice(
                ["Process the data.", "Calculate the value.", "Validate input."]
            ),
            "{implementation}": "result = data * 2\n    # TODO: Implement logic",
            "{method_name}": random.choice(
                ["get_result", "process", "validate", "save"]
            ),
            "{method_params}": "",
            "{method_docstring}": "Process the data.",
            "{method_implementation}": "pass",
            "{ClassName}": "TestProcessor",
            "{class_name}": "processor",
            "{test_case}": random.choice(["addition", "validation", "processing"]),
            "{setup_code}": "self.data = [1, 2, 3]",
            "{test_code}": "result = sum(self.data)",
        }

        content = snippet
        for key, value in replacements.items():
            content = content.replace(key, value)

        # Добавляем импорты
        imports = [
            "import os",
            "import sys",
            "import json",
            "from typing import List, Dict, Optional",
            "from datetime import datetime",
        ]

        import_line = random.choice(imports)
        if "import" in content:
            content = f"{import_line}\n{content}"

        return content

    def _modify_python_file(self, content: str) -> str:
        """Модифицирует Python файл"""
        lines = content.split("\n")

        if not lines:
            return content

        # Выбираем тип модификации
        modification_type = random.choice(
            [
                "add_function",
                "add_class",
                "modify_function",
                "add_import",
                "fix_bug",
                "add_comment",
            ]
        )

        if modification_type == "add_function" and len(lines) > 10:
            # Добавляем новую функцию
            insert_pos = random.randint(len(lines) // 2, len(lines) - 1)

            new_function = f"""
def new_function_{random.randint(1, 100)}(data):
    \"\"\"Process data with new functionality.\"\"\"
    # Implement new feature
    processed = [x * 2 for x in data]
    return processed
"""
            lines.insert(insert_pos, new_function)

        elif modification_type == "modify_function":
            # Находим функцию и модифицируем ее
            for i, line in enumerate(lines):
                if line.strip().startswith("def "):
                    # Добавляем комментарий или меняем реализацию
                    if i + 1 < len(lines):
                        lines.insert(
                            i + 1, f"    # Updated at {datetime.now().isoformat()}"
                        )
                    break

        elif modification_type == "add_comment":
            # Добавляем комментарий в случайное место
            if len(lines) > 5:
                insert_pos = random.randint(0, len(lines) - 1)
                comment = f"# TODO: {random.choice(['Optimize', 'Refactor', 'Add tests', 'Fix edge case'])}"
                lines.insert(insert_pos, comment)

        return "\n".join(lines)

    def _generate_markdown_file(self) -> str:
        """Генерирует Markdown файл"""
        titles = [
            "User Guide",
            "API Documentation",
            "Development Notes",
            "Feature Specification",
            "Troubleshooting Guide",
        ]

        title = random.choice(titles)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        content = f"""# {title}

        Created: {timestamp}

        ## Overview

        This document describes the {title.lower()}.

        ## Features

        - Feature 1: Description
        - Feature 2: Description
        - Feature 3: Description

        ## Usage

        ```python
        # Example code
        def example():
            pass
        Notes

        Additional information and considerations.

        """
        return content

    def _modify_markdown_file(self, content: str) -> str:
        """Модифицирует Markdown файл"""
        lines = content.split("\n")

        # Добавляем новую секцию
        new_section = random.choice(
            [
                "## Changelog",
                "## Known Issues",
                "## Future Improvements",
                "## Performance Notes",
            ]
        )

        insert_pos = min(len(lines), random.randint(len(lines) // 2, len(lines)))

        new_content = f"\n{new_section}\n\n- {random.choice(['Added new feature', 'Fixed bug', 'Improved performance', 'Updated documentation'])} at {datetime.now().strftime('%H:%M')}\n"

        lines.insert(insert_pos, new_content)
        return "\n".join(lines)

    def _generate_javascript_file(self) -> str:
        """Генерирует JavaScript файл"""
        return f"""// JavaScript module
        // Created: {datetime.now().isoformat()}

        export function processData(data) {{
        // Process the data
        return data.map(item => item * 2);
        }}

        export const config = {{
        apiUrl: 'https://api.example.com',
        timeout: 5000
        }};
        """

    def _modify_javascript_file(self, content: str) -> str:
        """Модифицирует JavaScript файл"""
        # Просто добавляем комментарий
        return content + f"\n\n// Updated at {datetime.now().isoformat()}"

    def _modify_text_file(self, content: str) -> str:
        """Модифицирует текстовый файл"""
        return content + f"\n\nUpdated: {datetime.now().isoformat()}"

    def _refactor_code(self, repo_path: str) -> Dict[str, str]:
        """Выполняет рефакторинг кода"""
        # Пока упрощенная версия - просто модифицируем случайный файл
        return self._modify_existing_file(repo_path)
