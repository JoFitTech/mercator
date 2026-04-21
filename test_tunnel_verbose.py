#!/usr/bin/env python
"""Test tunnel with verbose logging."""

import subprocess
import time
import re

print('Testing tunnel connectivity from cloudflared perspective...')
print('=' * 70)

# Start tunnel
cmd = ['cloudflared', 'tunnel', '--url', 'http://localhost:8501']
cmd_str = ' '.join(cmd)
print(f'Running: {cmd_str}')
print()

process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

url_found = None
timeout = time.time() + 30
iteration = 0

try:
    while time.time() < timeout and iteration < 100:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            time.sleep(0.1)
            continue

        iteration += 1
        print(f'{iteration:3d}: {line.rstrip()}')

        # Search for public URL
        url_match = re.search(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
        if url_match and not url_found:
            url_found = url_match.group(0)
            print(f'\nFound public URL: {url_found}')
            print(f'Waiting 10 seconds before terminating...\n')
            time.sleep(10)
            break

        if 'error' in line.lower() or 'failed' in line.lower():
            print(f'  ⚠️  Error detected!')
finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()
    print(f'\nTunnel process terminated.')

