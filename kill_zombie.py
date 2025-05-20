import os
import subprocess

def kill_zombie_processes():
    try:
        current_pid = os.getpid()
        result = subprocess.run(['ps', '-eo', 'pid,cmd'], stdout=subprocess.PIPE)
        lines = result.stdout.decode().split('\n')

        zombie_keywords = ['main.py', 'webapp.py', 'flask', 'werkzeug']
        to_kill = []

        for line in lines:
            if any(keyword in line for keyword in zombie_keywords) and 'kill_zombie' not in line:
                parts = line.strip().split(None, 1)
                if len(parts) < 2:
                    continue
                pid, cmd = parts
                if pid.isdigit() and int(pid) != current_pid:
                    to_kill.append(pid)

        if to_kill:
            print(f"Убиваем лишние процессы: {to_kill}")
            subprocess.run(['kill', '-9'] + to_kill)
        else:
            print("Лишних процессов не найдено.")
    except Exception as e:
        print(f"Ошибка при попытке завершения процессов: {e}")

kill_zombie_processes()
