import subprocess


def run_command(command, callback):
    process = subprocess.Popen(command.split(' '), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if not len(output) and process.poll() is not None:
            break
        if output:
            callback(output.strip().decode())
