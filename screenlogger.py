import collections
import functools
import os
import os.path
from PIL import Image
from PIL import ImageChops
from PIL import ImageGrab
import sys
import threading
import time
from typing import Callable

def timeit(f: Callable[[], None]) -> float:
    start = time.time()
    f()
    end = time.time()
    return end - start

class Screenshot:

    def __init__(self, s: Image.Image, m: str) -> None:
        self.screen = s
        self.moment = m

    def diff(self, other: 'Screenshot') -> float:
        total_pixels = self.screen.width * self.screen.height
        diff = ImageChops.difference(self.screen.convert('RGB'), other.screen.convert('RGB'))
        diff_pixels = functools.reduce(lambda ctr, px : ctr + (px != (0, 0, 0)), diff.getdata(), 0)
        return (diff_pixels / total_pixels) * 100.0

    def save(self, path: str) -> None:
        self.screen.save(path)

def get_screenshot() -> Screenshot:
    return Screenshot(ImageGrab.grab(), str(time.time()))

def capturer(folder: str, xab: (float, float, float), lock: threading.Lock, flag: [bool]) -> None:
    x, a, b = xab
    s1, s2 = None, None # pair of screens
    screenshot_queue = collections.deque()

    # loop until flag[0] == True
    while True:
        with lock:
            if flag[0]:
                break
        time.sleep(x)
        s1, s2 = s2, get_screenshot()
        if s1 and s2 and s1.diff(s2) < a: # almost static screen; log it as an event
            if (not screenshot_queue) or screenshot_queue[-1].diff(s1) > b:
                screenshot_queue.append(s1)

    # save screenshots
    for s in screenshot_queue:
        s.save(os.path.join(folder, f'{s.moment}.png'))

if __name__ == '__main__':
    
    # argument check
    if len(sys.argv) != 2:
        sys.exit(f'[{sys.argv[0]}] Usage: python3 {sys.argv[0]} <target-directory>')

    # folder check
    folder = sys.argv[1]
    if os.path.exists(folder):
        if not os.path.isdir(folder):
            sys.exit(f'[{sys.argv[0]}] Error: target is a non-directory file')
    else:
        os.makedirs(folder) # recursively make all needed directories

    # system performance measurement
    print(f'[{sys.argv[0]}] Note: measuring system ...')
    capture_time = timeit(lambda : [None, get_screenshot()][0])
    dummy_screenshot = get_screenshot()
    dummy_path = os.path.join(folder, 'tmp.png')
    save_time = timeit(lambda : [None, dummy_screenshot.save(dummy_path)][0])
    os.remove(dummy_path)

    # argument preparation
    xab = (max(capture_time * 1.5, 1.0), 1.0, 10.0)

    # flag preparation
    lock = threading.Lock()
    flag = [False] # flag needs to be a mutable object

    # start capturing
    worker = threading.Thread(target = capturer, args = (folder, xab, lock, flag))
    worker.start()
    print(f'[{sys.argv[0]}] Note: started capturer with (x, a, b) = {xab} ...'
           'press Ctrl+C once to stop and save')

    # monitor Ctrl+C
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f'[{sys.argv[0]}] Note: stopping and saving into {folder} ...')
        with lock:
            flag[0] = True
        worker.join() # wait for the thread to terminate
