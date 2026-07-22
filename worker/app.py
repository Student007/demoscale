"""Process jobs from the shared queue and publish a small heartbeat.

Each Compose replica runs this same file. The container hostname becomes the
worker identity, so the dashboard can show that multiple containers are
actually processing jobs.
"""

import json
import os
import socket
import time

import redis


REDIS_HOST = os.environ.get("REDIS_HOST", "queue")
QUEUE_KEY = os.environ.get("QUEUE_KEY", "jobs")
PROCESS_SECONDS = float(os.environ.get("PROCESS_SECONDS", "2"))
redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
worker_name = os.environ.get("WORKER_NAME") or socket.gethostname()
worker_key = f"scale:worker:{worker_name}"


def publish(status, current_job=""):
    # Didaktischer Kern: Jede Replik veröffentlicht denselben kleinen
    # Beobachtungssatz, ergänzt um ihren eigenen Container- bzw. Hostnamen.
    processed = redis_client.hget(worker_key, "processed") or "0"
    redis_client.hset(
        worker_key,
        mapping={
            "name": worker_name,
            "container": socket.gethostname(),
            "status": status,
            "current_job": current_job,
            "processed": processed,
            "last_seen": str(int(time.time())),
        },
    )
    # Expiration removes stale replicas from the dashboard after a stop.
    redis_client.expire(worker_key, 20)


def main():
    redis_client.ping()
    print(f"worker {worker_name} waiting for jobs", flush=True)
    while True:
        publish("waiting")
        # BRPOP blockiert, bis ein Auftrag vorhanden ist. Genau deshalb kann
        # dasselbe Worker-Image mit --scale mehrfach parallel laufen.
        item = redis_client.brpop(QUEUE_KEY, timeout=5)
        if item is None:
            continue
        _, raw_job = item
        job = json.loads(raw_job)
        publish("processing", job["id"])
        print(f"worker {worker_name} processing {job['id']}", flush=True)
        # Die Wartezeit simuliert Arbeit und macht die Verteilung in der GUI
        # sichtbar; sie ist keine fachliche Berechnung.
        time.sleep(PROCESS_SECONDS)
        redis_client.incr("scale:processed")
        redis_client.hincrby(worker_key, "processed", 1)
        print(f"worker {worker_name} finished {job['id']}", flush=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        publish("stopped")
