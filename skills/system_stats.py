
"""system_stats: Monitor CPU, Memory, and Disk usage."""
import psutil
import platform
import json

def run(arg=None):
    """
    Get system statistics (CPU, RAM, Disk, OS).
    args: "cpu", "memory", "disk", "os", or "all" (default)
    """
    arg = arg or "all"
    data = {}

    if arg in ("os", "all"):
        data["os"] = f"{platform.system()} {platform.release()} ({platform.version()})"
        data["machine"] = platform.machine()
        data["processor"] = platform.processor()

    if arg in ("cpu", "all"):
        data["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        data["cpu_count"] = psutil.cpu_count()

    if arg in ("memory", "all"):
        mem = psutil.virtual_memory()
        data["memory_total_gb"] = round(mem.total / (1024**3), 1)
        data["memory_used_percent"] = mem.percent

    if arg in ("disk", "all"):
        disk = psutil.disk_usage('/')
        data["disk_total_gb"] = round(disk.total / (1024**3), 1)
        data["disk_free_gb"] = round(disk.free / (1024**3), 1)
        data["disk_used_percent"] = disk.percent

    return json.dumps(data, indent=2)

if __name__ == "__main__":
    print(run())
