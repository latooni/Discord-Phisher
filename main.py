import threading, time, sys, subprocess, pkg_resources, os





required = {'git+https://github.com/Rapptz/asqlite', 'numerize', 'discord.py', 'playwright', 'rich', 'chat-exporter'}

value = input('Have you installed the libraries?\n1: Yes\n2: No\n\n')

if value == '2':
    python = sys.executable
    subprocess.check_call([python, '-m', 'pip', 'install', *required], stdout=subprocess.DEVNULL)
    os.system('cls')
    os.system('playwright install')
    os.system('cls')
    os.system('playwright install-deps')
    os.system('cls')

start = time.time()

def runfile(name):
    subprocess.call([sys.executable, '-u', name])

for f in ["./bot.py", "./generator.py"]:
    thread = threading.Thread(target=runfile, args=(f,))
    thread.start()

os.system('cls')


