import queue
import threading
import time
from abc import ABC, abstractmethod
from queue import Queue
from typing import Dict

TASKS_QUEUE = Queue()
