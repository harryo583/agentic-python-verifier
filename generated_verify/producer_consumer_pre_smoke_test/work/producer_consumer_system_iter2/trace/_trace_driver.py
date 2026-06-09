import os
import random
import sys

random.seed(int(os.environ.get("TRACE_SEED", "0")))
sys.path.insert(0, os.environ["TRACE_PKG_PARENT"])

from producer_consumer_system.app import run

run(steps=int(os.environ.get("TRACE_STEPS", "50")))
