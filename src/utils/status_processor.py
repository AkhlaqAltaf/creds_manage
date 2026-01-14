"""
Status processor for handling domain status checking in background
"""
import asyncio
import threading
import aiohttp
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session


class StatusProcessor:
    """Processor for checking domain working status in background"""
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_task(cls, task_id: str) -> None:
        """Create a new task entry"""
        with cls._lock:
            cls._tasks[task_id] = {
                "status": "processing",
                "total": 0,
                "processed": 0,
                "online_count": 0,
                "offline_count": 0,
                "failed_count": 0,
                "current_domain": None,
                "start_time": datetime.now(),
                "errors": []
            }
    
    @classmethod
    def update_task(cls, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task status"""
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id].update(updates)
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        with cls._lock:
            task = cls._tasks.get(task_id)
            if task and task["status"] in ["completed", "failed"]:
                elapsed = (datetime.now() - task["start_time"]).total_seconds()
                task["elapsed_seconds"] = int(elapsed)
            return task
    
    @classmethod
    def stop_all_tasks(cls) -> None:
        """Stop all processing tasks"""
        with cls._lock:
            for task_id in list(cls._tasks.keys()):
                if cls._tasks[task_id]["status"] == "processing":
                    cls._tasks[task_id]["status"] = "stopped"
    
    @classmethod
    def cleanup_task(cls, task_id: str) -> None:
        """Remove task after completion"""
        with cls._lock:
            if task_id in cls._tasks:
                del cls._tasks[task_id]
    
    @staticmethod
    async def check_domain_status(domain: str) -> bool:
        """Check if a domain is online/working"""
        urls_to_try = [
            f"https://{domain}",
            f"http://{domain}",
            f"https://{domain}/favicon.ico"
        ]
        
        for url in urls_to_try:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.head(url, allow_redirects=True) as response:
                        if response.status < 400:
                            return True
            except:
                continue
        
        # Try GET as fallback
        for url in urls_to_try:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, allow_redirects=True) as response:
                        if response.status < 400:
                            return True
            except:
                continue
        
        return False
    
    @classmethod
    async def process_domains_background(
        cls,
        task_id: str,
        domains: List,
        db: Session,
        batch_size: int = 25
    ) -> None:
        """Process domains in background"""
        try:
            # Update total count
            cls.update_task(task_id, {"total": len(domains)})
            
            online_count = 0
            offline_count = 0
            failed_count = 0
            
            # Process domains in batches
            batch_size = min(batch_size, 100)  # Max 100 at a time
            
            for i in range(0, len(domains), batch_size):
                batch = domains[i:i + batch_size]
                
                for domain in batch:
                    # Update current domain
                    cls.update_task(task_id, {
                        "current_domain": domain.domain,
                        "processed": cls._tasks[task_id]["processed"] + 1
                    })
                    
                    try:
                        # Check domain status
                        is_online = await cls.check_domain_status(domain.domain)
                        
                        # Update domain status in database
                        domain.is_working = is_online
                        
                        if is_online:
                            online_count += 1
                        else:
                            offline_count += 1
                        
                        # Update counts
                        cls.update_task(task_id, {
                            "online_count": online_count,
                            "offline_count": offline_count
                        })
                        
                    except Exception as e:
                        failed_count += 1
                        cls.update_task(task_id, {
                            "failed_count": failed_count,
                            "errors": cls._tasks[task_id]["errors"] + [f"{domain.domain}: {str(e)}"]
                        })
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.1)
                
                # Commit batch to database
                db.commit()
                
                # Delay between batches
                if i + batch_size < len(domains):
                    await asyncio.sleep(1)
            
            # Mark task as completed
            cls.update_task(task_id, {
                "status": "completed",
                "current_domain": None
            })
            
        except Exception as e:
            # Mark task as failed
            cls.update_task(task_id, {
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            # Clean up task after 1 hour
            await asyncio.sleep(3600)
            cls.cleanup_task(task_id)