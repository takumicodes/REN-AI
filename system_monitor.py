import psutil
import platform




def system_status():
    cpuusage = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ramusage = ram.percent
    disk = psutil.disk_usage('/')
    diskusage = disk.percent
    
    system_info=  {
        "Your operating system is ": platform.system(),
        " the current cpu usage is":cpuusage,
        " ram currently consumed is":ramusage,
        " The disk usage is":diskusage
    }
    
    return system_info


        
    