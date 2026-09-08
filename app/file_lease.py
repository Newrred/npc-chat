"""Process-lifetime OS lock; stale lock files do not block after a crash."""
import os


class FileLease:
    def __init__(self, path):
        self.path = path
        self.handle = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise RuntimeError("This database is already used by another app. Only one worker is supported.") from None
        self.handle = handle

    def release(self):
        if self.handle:
            self.handle.close()
            self.handle = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.release()
