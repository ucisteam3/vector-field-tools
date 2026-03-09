import os
import time

while True:
    os.system("git add .")
    os.system('git commit -m "auto update"')
    os.system("git push")
    time.sleep(180)