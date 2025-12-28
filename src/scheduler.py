
# src/scheduler.py
"""
Планировщик для автоматического создания коммитов по расписанию
"""

import schedule
import time
import random
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import signal
import sys
import os
import json

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, config_manager, git_operations, commit_generator):
        """
        Инициализация планировщика
        
        Args:
            config_manager: Экземпляр ConfigManager
            git_operations: Экземпляр GitOperations
            commit_generator: Экземпляр CommitGenerator
        """
        self.config = config_manager
        self.git_ops = git_operations
        self.commit_gen = commit_generator
        
        self.is_running = False
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        
        # Статистика
        self.stats = {
            "commits_created": 0,
            "last_commit_time": None,
            "errors": 0,
            "start_time": None
        }
        
        logger.info("Scheduler initialized")
    
    def start(self) -> bool:
        """
        Запускает планировщик
        
        Returns:
            True если успешно, False в противном случае
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return False
        
        logger.info("Starting scheduler...")
        
        # Настройка обработки сигналов
        self._setup_signal_handlers()
        
        # Проверка конфигурации
        if not self._validate_configuration():
            return False
        
        # Сброс флагов
        self.is_running = True
        self.stop_event.clear()
        self.stats["start_time"] = datetime.now()
        
        # Настройка расписания
        self._setup_schedule()
        
        # Запуск в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Scheduler started successfully")
        return True
    
    def stop(self) -> bool:
        """
        Останавливает планировщик
        
        Returns:
            True если успешно, False в противном случае
        """
        if not self.is_running:
            return True
        
        logger.info("Stopping scheduler...")
        
        self.is_running = False
        self.stop_event.set()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Scheduler stopped")
        return True
    
    def _setup_signal_handlers(self):
        """Настраивает обработку сигналов ОС"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _validate_configuration(self) -> bool:
        """Проверяет конфигурацию"""
        # Проверяем путь к репозиторию
        repo_path = self.config.get("repository.local_path")
        if not repo_path or repo_path == "./workspace":
            logger.error("Repository path not configured")
            return False
        
        # Проверяем настройки коммитов
        min_commits = self.config.get("commit_settings.min_commits_per_day")
        max_commits = self.config.get("commit_settings.max_commits_per_day")
        
        if min_commits is None or max_commits is None:
            logger.error("Commit settings not configured")
            return False
        
        if min_commits > max_commits:
            logger.error("min_commits_per_day > max_commits_per_day")
            return False
        
        return True
    
    def _setup_schedule(self):
        """Настраивает расписание задач"""
        # Очищаем существующие задачи
        schedule.clear()
        
        # Ежедневная задача для планирования коммитов
        schedule.every().day.at("00:05").do(self._plan_daily_commits)
        
        # Ежечасная проверка состояния
        schedule.every().hour.do(self._health_check)
        
        # Ежедневная статистика
        schedule.every().day.at("23:55").do(self._log_daily_stats)
        
        # Обработка отложенных коммитов
        schedule.every(30).minutes.do(self._process_pending_commits)
        
        logger.info("Schedule configured")
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        logger.info("Scheduler thread started")
        
        # Немедленно планируем коммиты на сегодня
        self._plan_daily_commits()
        
        # Основной цикл
        while self.is_running and not self.stop_event.is_set():
            try:
                # Запускаем запланированные задачи
                schedule.run_pending()
                
                # Задержка между проверками
                time.sleep(60)  # Проверяем каждую минуту
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self.stats["errors"] += 1
                time.sleep(60)
        
        logger.info("Scheduler thread stopped")
    
    def _plan_daily_commits(self):
        """Планирует коммиты на текущий день"""
        now = datetime.now()
        day_of_week = now.strftime('%A')
        
        # Проверяем выходные
        if day_of_week in ['Saturday', 'Sunday']:
            if not self.config.get("commit_settings.weekend_activity", False):
                logger.info("Skipping weekend (weekend_activity is False)")
                return
        
        # Определяем количество коммитов на день
        min_commits = self.config.get("commit_settings.min_commits_per_day", 1)
        max_commits = self.config.get("commit_settings.max_commits_per_day", 5)
        num_commits = random.randint(min_commits, max_commits)
        
        logger.info(f"Planning {num_commits} commits for {now.date()}")
        
        # Получаем часы активности
        start_hour = self.config.get("commit_settings.active_hours.start", 9)
        end_hour = self.config.get("commit_settings.active_hours.end", 21)
        
        # Генерируем времена для коммитов
        commit_times = self._generate_commit_times(num_commits, start_hour, end_hour)
        
        # Планируем каждый коммит
        for commit_time in commit_times:
            # Случайная задержка для реалистичности
            if self.config.get("stealth_mode.random_delays", True):
                delay_minutes = random.randint(0, 30)
                commit_time += timedelta(minutes=delay_minutes)
            
            # Форматируем время
            time_str = commit_time.strftime("%H:%M")
            
            # Планируем задачу
            schedule.every().day.at(time_str).do(
                self._create_scheduled_commit,
                scheduled_time=commit_time
            )
            
            logger.debug(f"Scheduled commit at {time_str}")
        
        logger.info(f"Scheduled {len(commit_times)} commits for today")
    
    def _generate_commit_times(self, num_commits: int, start_hour: int, end_hour: int) -> list:
        """Генерирует времена для коммитов"""
        times = []
        
        # Преобразуем в объекты datetime
        now = datetime.now()
        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        if start_time < now:
            start_time = now.replace(minute=now.minute + 5)  # Начинаем через 5 минут
        
        if num_commits <= 0:
            return times
        
        if num_commits == 1:
            # Один коммит в середине рабочего дня
            mid_time = start_time + (end_time - start_time) / 2
            times.append(mid_time)
            return times
        
        # Распределяем коммиты в течение дня
        total_minutes = (end_time - start_time).total_seconds() / 60
        interval = total_minutes / (num_commits - 1) if num_commits > 1 else total_minutes
        
        for i in range(num_commits):
            commit_time = start_time + timedelta(minutes=interval * i)
            
            # Добавляем небольшую случайность
            if self.config.get("stealth_mode.vary_commit_times", True):
                jitter = random.randint(-15, 15)
                commit_time += timedelta(minutes=jitter)
            
            # Ограничиваем временем активности
            if commit_time < start_time:
                commit_time = start_time
            elif commit_time > end_time:
                commit_time = end_time
            
            times.append(commit_time)
        
        return sorted(times)
    
    def _create_scheduled_commit(self, scheduled_time: datetime = None):
        """Создает запланированный коммит"""
        try:
            logger.info("Creating scheduled commit...")
            
            # Генерируем изменения
            repo_path = self.config.get("repository.local_path")
            changes = self.commit_gen.generate_changes(repo_path)
            
            if not changes:
                logger.warning("No changes generated, skipping commit")
                return
            
            # Генерируем сообщение коммита
            message = self.commit_gen.generate_commit_message()
            
            # Создаем коммит
            commit_hash = self.git_ops.create_commit(changes, message)
            
            # Обновляем статистику
            self.stats["commits_created"] += 1
            self.stats["last_commit_time"] = datetime.now()
            
            logger.info(f"Created commit: {commit_hash[:8]} - {message}")
            
            # Логируем детали
            self._log_commit_details(commit_hash, message, changes)
            
        except Exception as e:
            logger.error(f"Failed to create scheduled commit: {e}")
            self.stats["errors"] += 1
            
            # Обработка ошибки
            self._handle_commit_error(e, scheduled_time)
    
    def _log_commit_details(self, commit_hash: str, message: str, changes: dict):
        """Логирует детали коммита"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "commit_hash": commit_hash[:8],
            "message": message,
            "files_changed": list(changes.keys()),
            "file_count": len(changes)
        }
        
        logger.debug(f"Commit details: {log_entry}")
        
        # Сохраняем в файл логов
        try:
            log_file = self.config.get("logging.file", "./logs/commits.log")
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry['timestamp']} | {log_entry['commit_hash']} | "
                       f"{log_entry['message']} | {log_entry['file_count']} files\n")
        except Exception as e:
            logger.warning(f"Failed to write commit log: {e}")
    
    def _handle_commit_error(self, error: Exception, scheduled_time: datetime = None):
        """Обрабатывает ошибку создания коммита"""
        error_handler_enabled = self.config.get("error_handling.queue_failed_commits", True)
        
        if error_handler_enabled and scheduled_time:
            # Добавляем в очередь для повторной попытки
            self._add_to_retry_queue(scheduled_time, str(error))
    
    def _add_to_retry_queue(self, scheduled_time: datetime, error_msg: str):
        """Добавляет неудачный коммит в очередь повтора"""
        try:
            queue_file = "./data/pending_commits.json"
            os.makedirs(os.path.dirname(queue_file), exist_ok=True)
            
            # Загружаем существующую очередь
            queue = []
            if os.path.exists(queue_file):
                with open(queue_file, 'r', encoding='utf-8') as f:
                    queue = json.load(f)
            
            # Добавляем новую запись
            queue.append({
                "scheduled_time": scheduled_time.isoformat(),
                "error": error_msg,
                "retry_count": 0,
                "next_retry": (datetime.now() + timedelta(
                    minutes=self.config.get("error_handling.retry_delay_minutes", 30)
                )).isoformat()
            })
            
            # Ограничиваем размер очереди
            max_size = self.config.get("error_handling.max_queue_size", 50)
            if len(queue) > max_size:
                queue = queue[-max_size:]
            
            # Сохраняем очередь
            with open(queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, indent=2)
            
            logger.info("Added failed commit to retry queue")
            
        except Exception as e:
            logger.error(f"Failed to add to retry queue: {e}")
    
    def _process_pending_commits(self):
        """Обрабатывает отложенные коммиты"""
        try:
            queue_file = "./data/pending_commits.json"
            
            if not os.path.exists(queue_file):
                return
            
            with open(queue_file, 'r', encoding='utf-8') as f:
                queue = json.load(f)
            
            new_queue = []
            retry_attempts = self.config.get("error_handling.retry_attempts", 3)
            
            for item in queue:
                next_retry = datetime.fromisoformat(item["next_retry"])
                
                if datetime.now() >= next_retry:
                    # Попытка повторного выполнения
                    try:
                        logger.info(f"Retrying failed commit from {item['scheduled_time']}")
                        
                        # Здесь должна быть логика повторного создания коммита
                        # Пока просто удаляем из очереди после максимального количества попыток
                        
                        item["retry_count"] += 1
                        
                        if item["retry_count"] < retry_attempts:
                            # Планируем следующую попытку
                            item["next_retry"] = (datetime.now() + timedelta(
                                minutes=self.config.get("error_handling.retry_delay_minutes", 30)
                            )).isoformat()
                            new_queue.append(item)
                        else:
                            logger.warning(f"Failed commit removed after {retry_attempts} retries")
                    
                    except Exception as e:
                        logger.error(f"Retry failed: {e}")
                        new_queue.append(item)
                else:
                    new_queue.append(item)
            
            # Сохраняем обновленную очередь
            with open(queue_file, 'w', encoding='utf-8') as f:
                json.dump(new_queue, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to process pending commits: {e}")
    
    def _health_check(self):
        """Проверка состояния системы"""
        try:
            # Проверяем репозиторий
            status = self.git_ops.get_status()
            
            # Проверяем статистику
            if self.stats["last_commit_time"]:
                time_since_last = datetime.now() - self.stats["last_commit_time"]
                if time_since_last > timedelta(hours=24):
                    logger.warning(f"No commits for {time_since_last}")
            
            logger.debug("Health check passed")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def _log_daily_stats(self):
        """Логирует ежедневную статистику"""
        stats = {
            "date": datetime.now().date().isoformat(),
            "commits_created": self.stats["commits_created"],
            "errors": self.stats["errors"],
            "uptime": str(datetime.now() - self.stats["start_time"]) if self.stats["start_time"] else "N/A"
        }
        
        logger.info(f"Daily stats: {stats}")
        
        # Сбрасываем счетчики
        self.stats["commits_created"] = 0
        self.stats["errors"] = 0
    
    def get_status(self) -> dict:
        """Возвращает статус планировщика"""
        return {
            "is_running": self.is_running,
            "stats": self.stats.copy(),
            "next_run": schedule.next_run() if schedule.jobs else None,
            "jobs_count": len(schedule.jobs)
        }
    
    def create_test_commit(self) -> bool:
        """Создает тестовый коммит (для ручного запуска)"""
        try:
            logger.info("Creating test commit...")
            
            repo_path = self.config.get("repository.local_path")
            changes = self.commit_gen.generate_changes(repo_path)
            message = self.commit_gen.generate_commit_message()
            
            commit_hash = self.git_ops.create_commit(changes, message)
            
            logger.info(f"Test commit created: {commit_hash[:8]} - {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create test commit: {e}")
            return False