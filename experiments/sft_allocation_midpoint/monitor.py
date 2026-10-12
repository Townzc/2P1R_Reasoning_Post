"""Low-frequency GPU resource samples; no model calls or RNG operations."""
import json
from pathlib import Path
import subprocess
import threading
import time


class GPURecorder:
    def __init__(self, directory, interval=60):
        self.path = Path(directory) / 'gpu_samples.jsonl'
        self.interval = interval
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.thread.start()

    def _loop(self):
        with self.path.open('x') as stream:
            while not self.stop_event.is_set():
                record = {'epoch': time.time()}
                try:
                    record['csv'] = subprocess.check_output([
                        'nvidia-smi', '--query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit',
                        '--format=csv,noheader,nounits'], text=True, timeout=5).strip()
                except Exception as exc:
                    record['error'] = repr(exc)
                stream.write(json.dumps(record) + '\n'); stream.flush()
                self.stop_event.wait(self.interval)

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=6)
        if self.thread.is_alive():
            raise RuntimeError('GPU recorder did not close before manifest')
