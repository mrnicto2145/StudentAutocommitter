# src/system_integration.py
"""
Интеграция с операционной системой для автозапуска
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class SystemIntegration:
    def __init__(self, config_manager):
        """
        Инициализация интеграции с ОС
        
        Args:
            config_manager: Экземпляр ConfigManager
        """
        self.config = config_manager
        self.is_windows = sys.platform == "win32"
        
        logger.info(f"System integration initialized for {sys.platform}")
    
    def install_autostart(self) -> Dict[str, Any]:
        """
        Устанавливает автозапуск при старте системы
        
        Returns:
            Результат операции
        """
        if self.is_windows:
            return self._install_windows_autostart()
        else:
            return self._install_linux_autostart()
    
    def _install_windows_autostart(self) -> Dict[str, Any]:
        """Устанавливает автозапуск в Windows"""
        try:
            method = self.config.get("auto_start.startup_method", "registry")
            
            if method == "registry":
                return self._install_windows_registry()
            elif method == "task_scheduler":
                return self._install_windows_task_scheduler()
            elif method == "service":
                return self._install_windows_service()
            else:
                return {
                    "success": False,
                    "error": f"Unknown startup method: {method}",
                    "method": method
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "unknown"
            }
    
    def _install_windows_registry(self) -> Dict[str, Any]:
        """Устанавливает автозапуск через реестр Windows"""
        try:
            import winreg
            
            # Путь к исполняемому файлу
            if getattr(sys, 'frozen', False):
                # Если упаковано в exe
                exe_path = sys.executable
            else:
                # Если запускается как Python скрипт
                exe_path = sys.executable
                script_path = os.path.abspath(__file__)
                cmd = f'"{exe_path}" "{script_path}"'
                # На самом деле нужно запускать main.py, но для примера:
                main_path = os.path.join(os.path.dirname(script_path), "main.py")
                cmd = f'"{exe_path}" "{main_path}" start'
            
            # Ключ автозапуска
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key_name = "StudentAutocommiter"
            
            # Открываем ключ
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                key_path,
                0,
                winreg.KEY_SET_VALUE
            )
            
            # Устанавливаем значение
            winreg.SetValueEx(
                key,
                key_name,
                0,
                winreg.REG_SZ,
                cmd
            )
            
            winreg.CloseKey(key)
            
            logger.info(f"Added to Windows startup via registry: {key_name}")
            
            return {
                "success": True,
                "method": "registry",
                "key": key_name,
                "command": cmd
            }
            
        except ImportError:
            return {
                "success": False,
                "error": "winreg module not available",
                "method": "registry"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "registry"
            }
    
    def _install_windows_task_scheduler(self) -> Dict[str, Any]:
        """Создает задание в Планировщике задач Windows"""
        try:
            # Создаем XML для задания
            task_name = "StudentAutocommiter"
            task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Student Autocommiter - Automated Git commits</Description>
    <Author>Student Autocommiter</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{sys.executable}</Command>
      <Arguments>"{os.path.join(os.path.dirname(__file__), "main.py")}" start</Arguments>
    </Exec>
  </Actions>
</Task>'''
            
            # Сохраняем XML во временный файл
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(task_xml)
                xml_file = f.name
            
            # Создаем задание через schtasks
            result = subprocess.run(
                ["schtasks", "/create", "/tn", task_name, "/xml", xml_file, "/f"],
                capture_output=True,
                text=True
            )
            
            # Удаляем временный файл
            os.unlink(xml_file)
            
            if result.returncode == 0:
                logger.info(f"Created Windows Task Scheduler task: {task_name}")
                return {
                    "success": True,
                    "method": "task_scheduler",
                    "task_name": task_name
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "method": "task_scheduler"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "task_scheduler"
            }
    
    def _install_windows_service(self) -> Dict[str, Any]:
        """Устанавливает как службу Windows (требует прав администратора)"""
        try:
            # Это сложная операция, требующая дополнительных библиотек
            # и прав администратора
            return {
                "success": False,
                "error": "Windows service installation not yet implemented",
                "method": "service"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "service"
            }
    
    def _install_linux_autostart(self) -> Dict[str, Any]:
        """Устанавливает автозапуск в Linux"""
        try:
            # Для systemd
            if os.path.exists("/etc/systemd/system/"):
                return self._install_linux_systemd()
            # Для crontab
            else:
                return self._install_linux_crontab()
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "linux"
            }
    
    def _install_linux_systemd(self) -> Dict[str, Any]:
        """Создает службу systemd"""
        service_name = "student-autocommiter"
        service_content = f"""[Unit]
Description=Student Autocommiter Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={os.getcwd()}
ExecStart={sys.executable} {os.path.join(os.path.dirname(__file__), "main.py")} start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_file = f"/etc/systemd/system/{service_name}.service"
        
        try:
            # Требует прав sudo
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # Включаем автозапуск
            subprocess.run(["systemctl", "enable", service_name], check=True)
            
            logger.info(f"Created systemd service: {service_name}")
            
            return {
                "success": True,
                "method": "systemd",
                "service_name": service_name
            }
            
        except PermissionError:
            return {
                "success": False,
                "error": "Permission denied. Try with sudo.",
                "method": "systemd"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "systemd"
            }
    
    def _install_linux_crontab(self) -> Dict[str, Any]:
        """Добавляет в crontab"""
        try:
            # Команда для запуска при перезагрузке
            command = f"@reboot {sys.executable} {os.path.join(os.path.dirname(__file__), 'main.py')} start"
            
            # Получаем текущий crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Добавляем нашу команду
            new_crontab = current_crontab.strip() + f"\n{command}\n"
            
            # Устанавливаем новый crontab
            subprocess.run(
                ["crontab", "-"],
                input=new_crontab,
                text=True,
                check=True
            )
            
            logger.info("Added to crontab for autostart")
            
            return {
                "success": True,
                "method": "crontab",
                "command": command
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "crontab"
            }
    
    def remove_autostart(self) -> Dict[str, Any]:
        """
        Удаляет автозапуск
        
        Returns:
            Результат операции
        """
        if self.is_windows:
            return self._remove_windows_autostart()
        else:
            return self._remove_linux_autostart()
    
    def _remove_windows_autostart(self) -> Dict[str, Any]:
        """Удаляет автозапуск в Windows"""
        try:
            import winreg
            
            method = self.config.get("auto_start.startup_method", "registry")
            
            if method == "registry":
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                key_name = "StudentAutocommiter"
                
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        key_path,
                        0,
                        winreg.KEY_SET_VALUE
                    )
                    
                    winreg.DeleteValue(key, key_name)
                    winreg.CloseKey(key)
                    
                    logger.info(f"Removed from Windows startup registry: {key_name}")
                    
                    return {
                        "success": True,
                        "method": "registry"
                    }
                    
                except FileNotFoundError:
                    # Ключ уже не существует
                    return {
                        "success": True,
                        "method": "registry",
                        "note": "Already removed"
                    }
                    
            elif method == "task_scheduler":
                task_name = "StudentAutocommiter"
                
                result = subprocess.run(
                    ["schtasks", "/delete", "/tn", task_name, "/f"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info(f"Removed Windows Task Scheduler task: {task_name}")
                    return {
                        "success": True,
                        "method": "task_scheduler"
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr,
                        "method": "task_scheduler"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown startup method: {method}",
                    "method": method
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "method": "unknown"
            }
    
    def check_autostart_status(self) -> Dict[str, Any]:
        """
        Проверяет статус автозапуска
        
        Returns:
            Информация о статусе
        """
        if self.is_windows:
            return self._check_windows_autostart()
        else:
            return self._check_linux_autostart()
    
    def _check_windows_autostart(self) -> Dict[str, Any]:
        """Проверяет автозапуск в Windows"""
        try:
            import winreg
            
            # Проверяем реестр
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key_name = "StudentAutocommiter"
            
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    key_path,
                    0,
                    winreg.KEY_READ
                )
                
                value, reg_type = winreg.QueryValueEx(key, key_name)
                winreg.CloseKey(key)
                
                return {
                    "installed": True,
                    "method": "registry",
                    "command": value
                }
                
            except FileNotFoundError:
                # Не установлено в реестре
                pass
            
            # Проверяем Планировщик задач
            result = subprocess.run(
                ["schtasks", "/query", "/tn", "StudentAutocommiter", "/fo", "LIST"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "installed": True,
                    "method": "task_scheduler",
                    "status": "active"
                }
            
            return {
                "installed": False,
                "methods_checked": ["registry", "task_scheduler"]
            }
            
        except Exception as e:
            return {
                "installed": False,
                "error": str(e)
            }
    
    def create_startup_script(self) -> bool:
        """
        Создает скрипт для запуска при старте системы
        
        Returns:
            True если успешно
        """
        try:
            # Создаем батник для Windows
            if self.is_windows:
                script_content = f'''@echo off
echo Starting Student Autocommiter...
"{sys.executable}" "{os.path.join(os.path.dirname(__file__), "main.py")}" start
pause
'''
                script_path = os.path.join(os.getcwd(), "start_autocommiter.bat")
                
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                logger.info(f"Created startup script: {script_path}")
                return True
            
            # Для Linux
            else:
                script_content = f'''#!/bin/bash
echo "Starting Student Autocommiter..."
cd "{os.getcwd()}"
"{sys.executable}" "{os.path.join(os.path.dirname(__file__), "main.py")}" start
'''
                script_path = os.path.join(os.getcwd(), "start_autocommiter.sh")
                
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                # Делаем исполняемым
                os.chmod(script_path, 0o755)
                
                logger.info(f"Created startup script: {script_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create startup script: {e}")
            return False