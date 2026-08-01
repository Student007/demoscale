# Demoscale – technische Projektquelle

Dieses Repository enthält den Quellcode, die Container-Builds und die
Kubernetes-Manifeste der Docker-Skalierungsdemo.

Das bewusst kleine Studierenden-Paket mit nur einer `compose.yaml` liegt unter
[`Student007/demoscaler`](https://github.com/Student007/demoscaler).

## Bestandteile

- `dashboard`: Browseroberfläche und Statusanzeige
- `producer`: erzeugt Aufträge für die Redis-Queue
- `worker`: verarbeitet Aufträge aus der Queue
- `bundle`: Task-Container für Kubernetes-Multi-Container-Pods
- `kubernetes`: Kustomize-Manifeste für Docker Desktop Kubernetes/KIND
- `compose.yaml`: lokaler Entwicklungs- und Compose-Test
- `stack.swarm.yaml`: optionale Swarm-Variante
- `docker-bake.hcl`: Multi-Platform-Builds für Docker Hub

## Lokal entwickeln

```bash
docker compose up -d --build --scale worker=4
docker compose ps
```

Das Dashboard ist anschließend unter <http://localhost:8080> erreichbar.

## Kubernetes/KIND

Die Manifeste können lokal angewendet werden:

```bash
kubectl config use-context docker-desktop
kubectl apply -k kubernetes/
kubectl -n demoscale wait --for=condition=Available deployment --all --timeout=180s
kubectl -n demoscale port-forward service/dashboard 8080:8080
```

Für das Studierenden-Paket werden sie fest versioniert direkt aus diesem
Repository geladen. Diese Kustomize-URL setzt `git` im `PATH` voraus:

```bash
kubectl apply -k 'https://github.com/Student007/demoscale//kubernetes?ref=1.2.10'
```

Das Dashboard erkennt das Client-Betriebssystem und zeigt getrennte
Copy-&-Paste-Blöcke für macOS/Linux sowie Windows PowerShell. Beide laden das
Release als ZIP und wenden dessen lokales Kustomize-Verzeichnis ohne Git an.
PowerShell 5.1 erhält dabei keine `&&`-Operatoren; unter macOS/Linux wird eine
zsh-/bash-kompatible Befehlskette verwendet. Die Auswahl kann in der GUI
jederzeit manuell umgeschaltet werden.

## Images veröffentlichen

Version `1.2.10` veröffentlicht vier Images für `linux/amd64` und
`linux/arm64`:

```bash
docker login --username danbu
docker buildx use demoscale-builder
docker buildx inspect --bootstrap
docker buildx bake --push
```

Veröffentlicht werden:

```text
danbu/demoscale:demoscale-dashboard-1.2.10
danbu/demoscale:demoscale-producer-1.2.10
danbu/demoscale:demoscale-worker-1.2.10
danbu/demoscale:demoscale-bundle-task-1.2.10
```

## Tests

```bash
docker compose config
docker buildx bake --print
python3 -m py_compile dashboard/app.py producer/app.py worker/app.py bundle/app.py
kubectl kustomize kubernetes/
```

## Lizenz

Copyright © 2026 [Daniel Bunzendahl](https://www.linkedin.com/in/daniel-bunzendahl/).

Das Projekt steht unter der [Apache License 2.0](LICENSE). Ergänzende Hinweise
enthält [NOTICE](NOTICE).
