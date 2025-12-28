# src/git_operations.py
"""
Модуль для работы с Git репозиторием
Выполняет операции: clone, commit, push, status и другие
"""

import os
import sys
import time
import random
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import shutil

# Пытаемся импортировать GitPython
try:
    import git
    GITPYTHON_AVAILABLE = True
except ImportError:
    GITPYTHON_AVAILABLE = False
    logging.warning("GitPython not installed, falling back to command-line Git")

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Исключение для ошибок Git операций"""
    pass


class GitOperations:
    def __init__(self, config_manager):
        """
        Инициализация операций с Git
        
        Args:
            config_manager: Экземпляр ConfigManager
        """
        self.config = config_manager
        self.repo_path = self.config.get("repository.local_path", "./workspace")
        self.repo_url = self.config.get("repository.url", "")
        self.branch = self.config.get("repository.branch", "main")
        self.remote_name = self.config.get("repository.remote_name", "origin")
        self.auto_fetch = self.config.get("repository.auto_fetch", True)
        self.auto_pull = self.config.get("repository.auto_pull", False)
        
        # Инициализация репозитория
        self.repo = None
        self._init_repository()
        
        logger.info(f"Git operations initialized for: {self.repo_path}")
    
    def _init_repository(self) -> None:
        """Инициализация или открытие Git репозитория"""
        try:
            # Преобразуем путь в абсолютный
            self.repo_path = os.path.abspath(self.repo_path)
            
            # Проверяем, существует ли директория
            if not os.path.exists(self.repo_path):
                logger.info(f"Repository directory doesn't exist: {self.repo_path}")
                
                # Если есть URL, клонируем репозиторий
                if self.repo_url:
                    self.clone_repository()
                else:
                    # Создаем новую директорию
                    os.makedirs(self.repo_path, exist_ok=True)
                    logger.info(f"Created repository directory: {self.repo_path}")
            
            # Инициализируем GitPython репозиторий
            if GITPYTHON_AVAILABLE:
                try:
                    self.repo = git.Repo(self.repo_path)
                    logger.info(f"Opened existing repository at: {self.repo_path}")
                except (git.InvalidGitRepositoryError, git.NoSuchPathError):
                    # Инициализируем новый репозиторий
                    self.repo = git.Repo.init(self.repo_path)
                    logger.info(f"Initialized new Git repository at: {self.repo_path}")
                    
                    # Создаем начальный коммит
                    self._create_initial_commit()
            else:
                # Используем команды Git
                if not self._is_git_repo_command_line():
                    self._init_repo_command_line()
                    logger.info(f"Initialized new Git repository (command line) at: {self.repo_path}")
        
        except Exception as e:
            logger.error(f"Failed to initialize repository: {e}")
            raise GitError(f"Repository initialization failed: {e}")
    
    def _is_git_repo_command_line(self) -> bool:
        """Проверяем, является ли директория Git репозиторием (через команды)"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _init_repo_command_line(self) -> None:
        """Инициализируем Git репозиторий через команды"""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Настройка пользователя (если не настроен глобально)
            self._configure_git_user()
            
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to initialize repository: {e.stderr}")
    
    def _configure_git_user(self) -> None:
        """Настраивает пользователя Git для репозитория"""
        try:
            # Проверяем, настроен ли пользователь
            result = subprocess.run(
                ["git", "config", "user.name"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                # Устанавливаем имя пользователя
                subprocess.run(
                    ["git", "config", "user.name", "Student Autocommiter"],
                    cwd=self.repo_path,
                    check=True
                )
                subprocess.run(
                    ["git", "config", "user.email", "autocommiter@student.local"],
                    cwd=self.repo_path,
                    check=True
                )
                logger.info("Configured Git user for repository")
                
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to configure Git user: {e}")
    
    def _create_initial_commit(self) -> None:
        """Создает начальный коммит при инициализации репозитория"""
        try:
            # Создаем README файл
            readme_path = os.path.join(self.repo_path, "README.md")
            if not os.path.exists(readme_path):
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write("# Student Autocommiter Project\n\n")
                    f.write("This repository is managed by Student Autocommiter tool.\n")
                    f.write("Created for educational purposes only.\n")
            
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.index.add([readme_path])
                self.repo.index.commit("Initial commit: Project setup")
            else:
                subprocess.run(["git", "add", "README.md"], cwd=self.repo_path, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit: Project setup"],
                    cwd=self.repo_path,
                    check=True
                )
            
            logger.info("Created initial commit")
            
        except Exception as e:
            logger.warning(f"Failed to create initial commit: {e}")
    
    def clone_repository(self) -> None:
        """
        Клонирует удаленный репозиторий
        
        Raises:
            GitError: Если клонирование не удалось
        """
        if not self.repo_url:
            raise GitError("Repository URL is not configured")
        
        logger.info(f"Cloning repository from {self.repo_url} to {self.repo_path}")
        
        try:
            # Удаляем существующую директорию, если она есть
            if os.path.exists(self.repo_path):
                shutil.rmtree(self.repo_path)
            
            if GITPYTHON_AVAILABLE:
                self.repo = git.Repo.clone_from(self.repo_url, self.repo_path)
            else:
                subprocess.run(
                    ["git", "clone", self.repo_url, self.repo_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
                self.repo = None  # GitPython не используется
            
            logger.info(f"Successfully cloned repository")
            
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                error_msg += f"\n{e.stderr}"
            logger.error(f"Failed to clone repository: {error_msg}")
            raise GitError(f"Clone failed: {error_msg}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получает статус репозитория
        
        Returns:
            Словарь со статусом репозитория
        """
        status = {
            "path": self.repo_path,
            "is_repo": False,
            "branch": None,
            "has_remote": False,
            "ahead": 0,
            "behind": 0,
            "untracked_files": [],
            "modified_files": [],
            "staged_files": [],
            "last_commit": None
        }
        
        try:
            if GITPYTHON_AVAILABLE and self.repo:
                status["is_repo"] = True
                status["branch"] = str(self.repo.active_branch)
                
                # Проверяем удаленный репозиторий
                if self.repo.remotes:
                    status["has_remote"] = True
                
                # Получаем статус файлов
                git_status = self.repo.git.status(porcelain=True)
                for line in git_status.split('\n'):
                    if line:
                        code = line[:2]
                        filename = line[3:]
                        
                        if code == '??':
                            status["untracked_files"].append(filename)
                        elif code in [' M', 'MM']:
                            status["modified_files"].append(filename)
                        elif code in ['A ', 'M ', 'D ']:
                            status["staged_files"].append(filename)
                
                # Получаем информацию о последнем коммите
                if self.repo.head.is_valid():
                    last_commit = self.repo.head.commit
                    status["last_commit"] = {
                        "hash": last_commit.hexsha[:8],
                        "message": last_commit.message.strip(),
                        "author": str(last_commit.author),
                        "date": last_commit.committed_datetime.isoformat()
                    }
            
            else:
                # Используем команды Git
                if not self._is_git_repo_command_line():
                    return status
                
                status["is_repo"] = True
                
                # Получаем текущую ветку
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    status["branch"] = result.stdout.strip()
                
                # Проверяем удаленный репозиторий
                result = subprocess.run(
                    ["git", "remote"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                status["has_remote"] = bool(result.stdout.strip())
                
                # Получаем статус файлов
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            code = line[:2]
                            filename = line[3:]
                            
                            if code == '??':
                                status["untracked_files"].append(filename)
                            elif code in [' M', 'MM']:
                                status["modified_files"].append(filename)
                            elif code in ['A ', 'M ', 'D ']:
                                status["staged_files"].append(filename)
                
                # Получаем последний коммит
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%H|%an|%ae|%ad|%s"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split('|', 4)
                    if len(parts) == 5:
                        status["last_commit"] = {
                            "hash": parts[0][:8],
                            "author": f"{parts[1]} <{parts[2]}>",
                            "date": parts[3],
                            "message": parts[4]
                        }
        
        except Exception as e:
            logger.error(f"Failed to get repository status: {e}")
        
        return status
    
    def create_commit(self, changes: Dict[str, str], message: str) -> str:
        """
        Создает коммит с заданными изменениями
        
        Args:
            changes: Словарь {путь_к_файлу: содержимое}
            message: Сообщение коммита
        
        Returns:
            Хэш созданного коммита
        
        Raises:
            GitError: Если не удалось создать коммит
        """
        try:
            logger.info(f"Creating commit: {message}")
            
            # Применяем изменения
            for filepath, content in changes.items():
                full_path = os.path.join(self.repo_path, filepath)
                
                # Создаем директории, если их нет
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Записываем содержимое
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.debug(f"Modified file: {filepath}")
            
            # Добавляем изменения
            if GITPYTHON_AVAILABLE and self.repo:
                # Добавляем все измененные файлы
                self.repo.git.add(A=True)
                
                # Создаем коммит
                commit = self.repo.index.commit(message)
                commit_hash = commit.hexsha
                
            else:
                # Используем команды Git
                subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
                
                result = subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Получаем хэш коммита
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                commit_hash = result.stdout.strip()
            
            logger.info(f"Commit created: {commit_hash[:8]} - {message}")
            
            # Обновляем статус репозитория
            self._sync_with_remote()
            
            return commit_hash
            
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                error_msg += f"\n{e.stderr}"
            
            logger.error(f"Failed to create commit: {error_msg}")
            
            # Пытаемся откатить изменения
            self._cleanup_failed_commit(list(changes.keys()))
            
            raise GitError(f"Commit failed: {error_msg}")
    
    def _cleanup_failed_commit(self, changed_files: List[str]) -> None:
        """Очищает файлы после неудачной попытки коммита"""
        try:
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.git.reset("--hard", "HEAD")
                self.repo.git.clean("-fd")
            else:
                subprocess.run(["git", "reset", "--hard", "HEAD"], 
                             cwd=self.repo_path, capture_output=True)
                subprocess.run(["git", "clean", "-fd"], 
                             cwd=self.repo_path, capture_output=True)
            
            logger.info("Cleaned up failed commit attempt")
            
        except Exception as e:
            logger.warning(f"Failed to clean up after failed commit: {e}")
    
    def _sync_with_remote(self) -> None:
        """Синхронизирует с удаленным репозиторием при необходимости"""
        try:
            if self.auto_fetch:
                self.fetch()
            
            if self.auto_pull:
                self.pull()
            
            # Автоматический push после коммита
            push_enabled = self.config.get("repository.auto_push", True)
            if push_enabled:
                self.push()
                
        except Exception as e:
            logger.warning(f"Sync with remote failed: {e}")
    
    def push(self, force: bool = False) -> bool:
        """
        Отправляет коммиты в удаленный репозиторий
        
        Args:
            force: Принудительный push
        
        Returns:
            True если успешно, False в противном случае
        """
        try:
            logger.info(f"Pushing to {self.remote_name}/{self.branch}")
            
            if GITPYTHON_AVAILABLE and self.repo:
                if force:
                    self.repo.git.push(self.remote_name, self.branch, force=True)
                else:
                    self.repo.git.push(self.remote_name, self.branch)
            else:
                cmd = ["git", "push", self.remote_name, self.branch]
                if force:
                    cmd.append("--force")
                
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Push failed: {result.stderr}")
                    return False
            
            logger.info("Push successful")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                error_msg += f"\n{e.stderr}"
            
            logger.error(f"Push failed: {error_msg}")
            return False
    
    def pull(self) -> bool:
        """
        Получает изменения из удаленного репозитория
        
        Returns:
            True если успешно, False в противном случае
        """
        try:
            logger.info(f"Pulling from {self.remote_name}/{self.branch}")
            
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.git.pull(self.remote_name, self.branch)
            else:
                result = subprocess.run(
                    ["git", "pull", self.remote_name, self.branch],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Pull failed: {result.stderr}")
                    return False
            
            logger.info("Pull successful")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                error_msg += f"\n{e.stderr}"
            
            logger.error(f"Pull failed: {error_msg}")
            return False
    
    def fetch(self) -> bool:
        """
        Получает изменения из удаленного репозитория без слияния
        
        Returns:
            True если успешно, False в противном случае
        """
        try:
            logger.info(f"Fetching from {self.remote_name}")
            
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.remotes[self.remote_name].fetch()
            else:
                result = subprocess.run(
                    ["git", "fetch", self.remote_name],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Fetch failed: {result.stderr}")
                    return False
            
            logger.info("Fetch successful")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'stderr'):
                error_msg += f"\n{e.stderr}"
            
            logger.error(f"Fetch failed: {error_msg}")
            return False
    
    def get_commit_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю коммитов
        
        Args:
            limit: Максимальное количество коммитов
        
        Returns:
            Список коммитов
        """
        commits = []
        
        try:
            if GITPYTHON_AVAILABLE and self.repo:
                for commit in self.repo.iter_commits(max_count=limit):
                    commits.append({
                        "hash": commit.hexsha[:8],
                        "message": commit.message.strip(),
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                        "files_changed": len(commit.stats.files)
                    })
            else:
                # Формат: hash|author|date|message
                result = subprocess.run(
                    ["git", "log", f"--max-count={limit}", 
                     "--format=%H|%an <%ae>|%ai|%s", "--stat"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    i = 0
                    while i < len(lines):
                        if '|' in lines[i]:
                            parts = lines[i].split('|', 3)
                            if len(parts) == 4:
                                commit = {
                                    "hash": parts[0][:8],
                                    "author": parts[1],
                                    "date": parts[2],
                                    "message": parts[3],
                                    "files_changed": 0
                                }
                                
                                # Считаем измененные файлы
                                i += 1
                                while i < len(lines) and lines[i].strip() and '|' not in lines[i]:
                                    if '|' not in lines[i]:
                                        commit["files_changed"] += 1
                                    i += 1
                                
                                commits.append(commit)
                        else:
                            i += 1
        
        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
        
        return commits
    
    def create_branch(self, branch_name: str, switch: bool = False) -> bool:
        """
        Создает новую ветку
        
        Args:
            branch_name: Имя ветки
            switch: Переключиться ли на новую ветку
        
        Returns:
            True если успешно, False в противном случае
        """
        try:
            logger.info(f"Creating branch: {branch_name}")
            
            if GITPYTHON_AVAILABLE and self.repo:
                new_branch = self.repo.create_head(branch_name)
                if switch:
                    new_branch.checkout()
            else:
                cmd = ["git", "branch", branch_name]
                subprocess.run(cmd, cwd=self.repo_path, check=True)
                
                if switch:
                    subprocess.run(["git", "checkout", branch_name], 
                                 cwd=self.repo_path, check=True)
            
            logger.info(f"Branch created: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False
    
    def switch_branch(self, branch_name: str) -> bool:
        """
        Переключается на указанную ветку
        
        Args:
            branch_name: Имя ветки
        
        Returns:
            True если успешно, False в противном случае
        """
        try:
            logger.info(f"Switching to branch: {branch_name}")
            
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.git.checkout(branch_name)
            else:
                result = subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Switch branch failed: {result.stderr}")
                    return False
            
            logger.info(f"Switched to branch: {branch_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch branch: {e}")
            return False
    
    def get_file_content(self, filepath: str, revision: str = "HEAD") -> Optional[str]:
        """
        Получает содержимое файла из указанной ревизии
        
        Args:
            filepath: Путь к файлу
            revision: Ревизия (по умолчанию HEAD)
        
        Returns:
            Содержимое файла или None
        """
        try:
            if GITPYTHON_AVAILABLE and self.repo:
                try:
                    return self.repo.git.show(f"{revision}:{filepath}")
                except git.GitCommandError:
                    return None
            else:
                result = subprocess.run(
                    ["git", "show", f"{revision}:{filepath}"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return result.stdout
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
            return None
    
    def cleanup(self) -> None:
        """
        Очищает временные файлы и выполняет обслуживание репозитория
        """
        try:
            logger.info("Cleaning up repository...")
            
            # Выполняем git gc для оптимизации
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.git.gc("--auto")
            else:
                subprocess.run(["git", "gc", "--auto"], 
                             cwd=self.repo_path, capture_output=True)
            
            # Очищаем untracked файлы
            if GITPYTHON_AVAILABLE and self.repo:
                self.repo.git.clean("-fd")
            else:
                subprocess.run(["git", "clean", "-fd"], 
                             cwd=self.repo_path, capture_output=True)
            
            logger.info("Repository cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику репозитория
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            "total_commits": 0,
            "total_branches": 0,
            "total_tags": 0,
            "first_commit_date": None,
            "last_commit_date": None,
            "authors": {}
        }
        
        try:
            if GITPYTHON_AVAILABLE and self.repo:
                # Количество коммитов
                stats["total_commits"] = len(list(self.repo.iter_commits()))
                
                # Ветки
                stats["total_branches"] = len(self.repo.branches)
                
                # Теги
                stats["total_tags"] = len(self.repo.tags)
                
                # Коммиты по авторам
                for commit in self.repo.iter_commits():
                    author = str(commit.author)
                    stats["authors"][author] = stats["authors"].get(author, 0) + 1
                
                # Даты первого и последнего коммита
                if stats["total_commits"] > 0:
                    first_commit = list(self.repo.iter_commits())[-1]
                    last_commit = self.repo.head.commit
                    
                    stats["first_commit_date"] = first_commit.committed_datetime.isoformat()
                    stats["last_commit_date"] = last_commit.committed_datetime.isoformat()
            
            else:
                # Используем команды Git
                # Количество коммитов
                result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    stats["total_commits"] = int(result.stdout.strip())
                
                # Количество веток
                result = subprocess.run(
                    ["git", "branch", "-a", "--format=%(refname:short)"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    stats["total_branches"] = len(result.stdout.strip().split('\n'))
                
                # Количество тегов
                result = subprocess.run(
                    ["git", "tag", "--list"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    stats["total_tags"] = len(result.stdout.strip().split('\n'))
                
                # Коммиты по авторам
                result = subprocess.run(
                    ["git", "shortlog", "-s", "-n", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.strip().split('\t')
                            if len(parts) == 2:
                                count = int(parts[0].strip())
                                author = parts[1].strip()
                                stats["authors"][author] = count
        
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
        
        return stats


# Утилитарные функции
def is_git_installed() -> bool:
    """
    Проверяет, установлен ли Git в системе
    
    Returns:
        True если Git установлен, False в противном случае
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_git_version() -> Optional[str]:
    """
    Получает версию Git
    
    Returns:
        Версия Git или None
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def create_gitignore(repo_path: str, patterns: List[str] = None) -> None:
    """
    Создает файл .gitignore с указанными паттернами
    
    Args:
        repo_path: Путь к репозиторию
        patterns: Список паттернов для игнорирования
    """
    if patterns is None:
        patterns = [
            "# IDE and editor files",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "*~",
            "",
            "# Python",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "env/",
            "venv/",
            ".env",
            ".venv",
            "",
            "# Logs",
            "logs/",
            "*.log",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Autocommiter",
            "data/",
            "pending_commits.json"
        ]
    
    gitignore_path = os.path.join(repo_path, ".gitignore")
    
    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(patterns))
    
    logger.info(f"Created .gitignore at {gitignore_path}")