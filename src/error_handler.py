# src/error_handler.py
"""
Обработчик ошибок и система отложенных коммитов
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler:
    def __init__(self, config_manager):
        """
        Инициализация обработчика ошибок
        
        Args:
            config_manager: Экземпляр ConfigManager
        """
        self.config = config_manager
        self.data_dir = self._get_data_dir()
        
        # Файлы данных
        self.pending_file = os.path.join(self.data_dir, "pending_commits.json")
        self.errors_file = os.path.join(self.data_dir, "errors.json")
        self.stats_file = os.path.join(self.data_dir, "statistics.json")
        
        # Инициализация файлов
        self._init_data_files()
        
        logger.info("Error handler initialized")
    
    def _get_data_dir(self) -> str:
        """Возвращает путь к директории данных"""
        data_dir = self.config.get("storage.data_dir", "./data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    
    def _init_data_files(self):
        """Инициализирует файлы данных"""
        # pending_commits.json
        if not os.path.exists(self.pending_file):
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        # errors.json
        if not os.path.exists(self.errors_file):
            with open(self.errors_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        # statistics.json
        if not os.path.exists(self.stats_file):
            default_stats = {
                "total_commits": 0,
                "successful_commits": 0,
                "failed_commits": 0,
                "pending_commits": 0,
                "last_error": None,
                "start_time": datetime.now().isoformat()
            }
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(default_stats, f)
    
    def handle_commit_error(self, error: Exception, commit_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Обрабатывает ошибку создания коммита
        
        Args:
            error: Исключение
            commit_data: Данные коммита
        
        Returns:
            Информация об обработке ошибки
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "commit_data": commit_data
        }
        
        logger.error(f"Commit error: {error_info['error_message']}")
        
        # Сохраняем ошибку
        self._save_error(error_info)
        
        # Обновляем статистику
        self._update_stats(failed=True)
        
        # Добавляем в очередь отложенных коммитов, если включено
        if self.config.get("error_handling.queue_failed_commits", True) and commit_data:
            return self._add_to_pending_queue(commit_data, error_info)
        
        return {"handled": False, "error": error_info}
    
    def _save_error(self, error_info: Dict[str, Any]):
        """Сохраняет информацию об ошибке"""
        try:
            errors = []
            if os.path.exists(self.errors_file):
                with open(self.errors_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
            
            # Ограничиваем количество сохраненных ошибок
            max_errors = self.config.get("error_handling.max_stored_errors", 100)
            errors.append(error_info)
            
            if len(errors) > max_errors:
                errors = errors[-max_errors:]
            
            with open(self.errors_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save error: {e}")
    
    def _add_to_pending_queue(self, commit_data: Dict[str, Any], error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Добавляет коммит в очередь отложенных"""
        try:
            pending = []
            if os.path.exists(self.pending_file):
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    pending = json.load(f)
            
            pending_item = {
                "added_at": datetime.now().isoformat(),
                "commit_data": commit_data,
                "error_info": error_info,
                "retry_count": 0,
                "next_retry": (datetime.now() + timedelta(
                    minutes=self.config.get("error_handling.retry_delay_minutes", 30)
                )).isoformat(),
                "max_retries": self.config.get("error_handling.retry_attempts", 3)
            }
            
            pending.append(pending_item)
            
            # Ограничиваем размер очереди
            max_size = self.config.get("error_handling.max_queue_size", 50)
            if len(pending) > max_size:
                pending = pending[-max_size:]
            
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump(pending, f, indent=2)
            
            # Обновляем статистику
            self._update_pending_stats(len(pending))
            
            logger.info(f"Added to pending queue. Total pending: {len(pending)}")
            
            return {
                "handled": True,
                "added_to_queue": True,
                "queue_position": len(pending),
                "next_retry": pending_item["next_retry"]
            }
            
        except Exception as e:
            logger.error(f"Failed to add to pending queue: {e}")
            return {"handled": False, "error": str(e)}
    
    def get_pending_commits(self) -> List[Dict[str, Any]]:
        """Возвращает список отложенных коммитов"""
        try:
            if os.path.exists(self.pending_file):
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to get pending commits: {e}")
        
        return []
    
    def process_pending_commits(self, retry_callback) -> Dict[str, Any]:
        """
        Обрабатывает отложенные коммиты
        
        Args:
            retry_callback: Функция для повторной попытки создания коммита
        
        Returns:
            Статистика обработки
        """
        stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "removed": 0
        }
        
        try:
            pending = self.get_pending_commits()
            if not pending:
                return stats
            
            new_pending = []
            
            for item in pending:
                next_retry = datetime.fromisoformat(item["next_retry"])
                
                if datetime.now() >= next_retry:
                    stats["processed"] += 1
                    
                    try:
                        # Пытаемся выполнить коммит
                        result = retry_callback(item["commit_data"])
                        
                        if result.get("success", False):
                            stats["succeeded"] += 1
                            stats["removed"] += 1
                            logger.info(f"Retry succeeded for commit from {item['added_at']}")
                        else:
                            # Увеличиваем счетчик попыток
                            item["retry_count"] += 1
                            
                            if item["retry_count"] < item["max_retries"]:
                                # Планируем следующую попытку
                                delay = self.config.get("error_handling.retry_delay_minutes", 30)
                                item["next_retry"] = (datetime.now() + timedelta(minutes=delay)).isoformat()
                                new_pending.append(item)
                                stats["failed"] += 1
                                logger.warning(f"Retry failed, will retry later")
                            else:
                                # Удаляем после максимального количества попыток
                                stats["removed"] += 1
                                stats["failed"] += 1
                                logger.error(f"Max retries reached, removing from queue")
                    
                    except Exception as e:
                        logger.error(f"Error processing pending commit: {e}")
                        stats["failed"] += 1
                        new_pending.append(item)
                
                else:
                    # Еще не время для повторной попытки
                    new_pending.append(item)
            
            # Сохраняем обновленную очередь
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump(new_pending, f, indent=2)
            
            # Обновляем статистику
            self._update_pending_stats(len(new_pending))
            
            if stats["succeeded"] > 0:
                self._update_stats(successful=True, count=stats["succeeded"])
            
            if stats["failed"] > 0:
                self._update_stats(failed=True, count=stats["failed"])
        
        except Exception as e:
            logger.error(f"Failed to process pending commits: {e}")
        
        return stats
    
    def _update_stats(self, successful: bool = False, failed: bool = False, count: int = 1):
        """Обновляет статистику"""
        try:
            stats = {}
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            
            stats["total_commits"] = stats.get("total_commits", 0) + count
            
            if successful:
                stats["successful_commits"] = stats.get("successful_commits", 0) + count
            
            if failed:
                stats["failed_commits"] = stats.get("failed_commits", 0) + count
            
            stats["last_update"] = datetime.now().isoformat()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
    
    def _update_pending_stats(self, pending_count: int):
        """Обновляет статистику отложенных коммитов"""
        try:
            stats = {}
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            
            stats["pending_commits"] = pending_count
            stats["last_update"] = datetime.now().isoformat()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to update pending stats: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                
                # Добавляем расчетные значения
                if stats.get("total_commits", 0) > 0:
                    success_rate = (stats.get("successful_commits", 0) / stats["total_commits"]) * 100
                    stats["success_rate_percent"] = round(success_rate, 2)
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
        
        return {}
    
    def clear_pending_queue(self) -> bool:
        """Очищает очередь отложенных коммитов"""
        try:
            with open(self.pending_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            
            self._update_pending_stats(0)
            logger.info("Pending queue cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear pending queue: {e}")
            return False
    
    def get_error_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Возвращает сводку ошибок"""
        try:
            if os.path.exists(self.errors_file):
                with open(self.errors_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
                
                # Возвращаем последние ошибки
                return errors[-limit:]
        except Exception as e:
            logger.error(f"Failed to get error summary: {e}")
        
        return []