import re
import subprocess
import sys
import time


def pids_listening(port: int) -> list[str]:
    out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore")
    pids: set[str] = set()
    needle = f":{port}"
    for line in out.splitlines():
        u = line.upper()
        if needle in u and "LISTENING" in u:
            m = re.search(r"LISTENING\s+(\d+)\s*$", line.strip())
            if m:
                pids.add(m.group(1))
    return sorted(pids)


def kill_pid(pid: str) -> None:
    subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/kill_port.py <port> [retries]")
        return 2
    port = int(sys.argv[1])
    retries = int(sys.argv[2]) if len(sys.argv) >= 3 else 5

    for _ in range(retries):
        pids = pids_listening(port)
        if not pids:
            print(f"Port {port} kosong")
            return 0
        print(f"Kill PIDs {pids} (port {port})")
        for pid in pids:
            kill_pid(pid)
        time.sleep(1)

    pids = pids_listening(port)
    if pids:
        print(f"[ERROR] Port {port} masih dipakai oleh PID: {', '.join(pids)}")
        return 1
    print(f"Port {port} kosong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

