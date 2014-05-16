ADB-Sanity-Check
================

Check if all connected devices are visible in ADB

# Usage

Start server
```bash
nohup check_adb.py --listen 1234 > check_adb.out &
```
A server listen to `http://localhost:1234` is started.
