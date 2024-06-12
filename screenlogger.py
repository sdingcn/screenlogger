import collections
import functools
import os
import os.path
import psutil
from PIL import Image
from PIL import ImageChops
from PIL import ImageGrab
import sys
import threading
import time
import timeit
from typing import Any, Callable


class Screenshot:

    def __init__(self, screen: Image.Image, moment: str) -> None:
        self.screen = screen
        self.moment = moment

    def diff(self, other: 'Screenshot') -> float:
        total_pixels = self.screen.width * self.screen.height
        diff = ImageChops.difference(self.screen.convert('RGB'), other.screen.convert('RGB'))
        diff_pixels = functools.reduce(lambda ctr, px: ctr + (px != (0, 0, 0)), diff.getdata(), 0)
        return (diff_pixels / total_pixels) * 100.0

    def save(self, path: str) -> None:
        self.screen.save(path)


def get_screenshot() -> Screenshot:
    return Screenshot(
        screen = ImageGrab.grab(),
        moment = str(time.time())
    )


class PerfStat:

    def __init__(self, capture_time, save_time, screenshot_size, vm_size) -> None:
        self.capture_time = capture_time
        self.save_time = save_time
        self.screenshot_size = screenshot_size
        self.vm_size = vm_size


def perf_check(folder: str):
    repetition = 3

    capture_time = timeit.timeit(lambda: get_screenshot(), number = repetition) / repetition  # seconds

    save_time = 0.0
    screenshot_size = 0.0
    tmp_path = os.path.join(folder, 'tmp.png')
    for _ in range(repetition):
        tmp_screenshot = get_screenshot()
        save_time += timeit.timeit(lambda: tmp_screenshot.save(tmp_path), number = 1)  # seconds
        screenshot_size += os.path.getsize(tmp_path)  # bytes
        os.remove(tmp_path)
    save_time /= repetition
    screenshot_size /= repetition

    vm_size = psutil.virtual_memory().total  # bytes

    return PerfStat(
        capture_time = capture_time,
        save_time = save_time,
        screenshot_size = screenshot_size,
        vm_size = vm_size
    )


def capturer(folder: str, xab: (float, float, float), qs: int, lock: threading.Lock, flag: [bool]) -> None:
    x, a, b = xab
    s1, s2 = None, None  # pair of screens
    screenshot_queue = collections.deque()

    # loop until flag[0] == True
    while True:
        with lock:
            if flag[0]:
                break
        t1 = time.time()  # seconds
        s1, s2 = s2, get_screenshot()
        t2 = time.time()
        tdiff = t2 - t1
        if tdiff < x:
            time.sleep(x - tdiff)
        if s1 and s2 and s1.diff(s2) < a:  # almost static screen; consider logging it as an event
            if (not screenshot_queue) or screenshot_queue[-1].diff(s1) > b:
                screenshot_queue.append(s1)
        if len(screenshot_queue) > qs:
            for i in range(qs):
                s = screenshot_queue.popleft()
                s.save(os.path.join(folder, f'{s.moment}.png'))

    # save unsaved screenshots
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
        os.makedirs(folder)  # recursively make all needed directories
    
    print(f'[{sys.argv[0]}] Note: checking system performance ...')

    # argument preparation
    perf_stat = perf_check(folder)
    xab = (
        max(perf_stat.capture_time * 3, 1.0),
        1.0,
        10.0
    )
    qs = int(perf_stat.vm_size * 0.01 / (perf_stat.screenshot_size * 3))

    # flag preparation
    lock = threading.Lock()
    flag = [False]  # flag needs to be a mutable object

    # start capturing
    worker = threading.Thread(target = capturer, args = (folder, xab, qs, lock, flag))
    worker.start()
    print(f'[{sys.argv[0]}] Note: started capturer with (x, a, b) = {xab}, qs = {qs} ...'
           'press Ctrl+C once to stop')

    # monitor Ctrl+C
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f'[{sys.argv[0]}] Note: stopping ...')
        with lock:
            flag[0] = True
        worker.join()  # wait for the thread to terminate
