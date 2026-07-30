# Demoscale – Testanleitung

Demoscale zeigt horizontale Skalierung mit Docker Compose. Ein Dashboard nimmt
Aufträge an, Redis dient als gemeinsame Queue und mehrere Worker verarbeiten
die Aufträge parallel.

Compose benennt die Container automatisch, zum Beispiel
`demoscale-dashboard-1` und `demoscale-worker-1` bis
`demoscale-worker-4`.

## Voraussetzungen

- Docker Desktop oder Docker Engine
- Docker Compose v2
- Zugriff auf die veröffentlichten Images im Docker-Hub-Repository
  `danbu/demoscale`

## 1. Veröffentlichten Stack vorbereiten

Führen Sie die Befehle aus dem Demo-Verzeichnis aus. Setzen Sie in `.env` den
Docker-Hub-Namespace und den Image-Tag, der getestet werden soll:

```dotenv
REGISTRY_USER=danbu
IMAGE_REPOSITORY=demoscale
IMAGE_TAG=1.2.9
DASHBOARD_PORT=8080
JOB_COUNT=12
PROCESS_SECONDS=2
```

Laden Sie die Images und starten Sie zunächst einen Worker:

```bash
docker compose pull
docker compose up -d --no-build --scale worker=1
docker compose ps
```

Erwartet werden die Container `demoscale-dashboard-1`, `demoscale-producer-1`,
`demoscale-queue-1` und `demoscale-worker-1`. Redis und Producer sollten als
`healthy` angezeigt werden.

## 2. Weboberfläche prüfen

Öffnen Sie <http://localhost:8080>. Die Oberfläche enthält Schaltflächen für
5, 20 und 40 Testjobs. Der technische JSON-Endpunkt ist unter
<http://localhost:8080/status> erreichbar.
[Dashboard-Screenshot öffnen](https://raw.githubusercontent.com/Student007/demoscale/refs/heads/main/docs/demoscale-dashboard.jpg)

Der Screenshot zeigt vier aktive Worker, eine leere Queue und bereits
verarbeitete Testjobs.

## 3. Testjobs erzeugen

Jobs können direkt im Browser oder über die Kommandozeile erzeugt werden:

```bash
curl "http://localhost:8080/health"
curl "http://localhost:8080/enqueue?n=10"
curl "http://localhost:8080/status"
```

Die Antwort des Enqueue-Endpunkts sollte `"enqueued": 10` enthalten.

## 4. Worker skalieren

Skalieren Sie den Worker-Service auf vier Container:

```bash
docker compose up -d --scale worker=4
docker compose ps
```

Erzeugen Sie erneut Jobs, zum Beispiel:

```bash
curl "http://localhost:8080/enqueue?n=20"
```

Nach ungefähr 12 Sekunden bei `PROCESS_SECONDS=2` prüfen Sie den Status:

```bash
curl "http://localhost:8080/status"
docker compose logs --tail=50 worker
```

Ein erfolgreicher Test zeigt:

- `queue_length: 0`, sobald alle Jobs verarbeitet wurden;
- mindestens vier Einträge unter `workers`;
- einen erhöhten Wert bei `processed`;
- in den Logs unterschiedliche Worker-Namen bei der Verarbeitung.

## 5. Test beenden

```bash
docker compose down
```

Das Named Volume bleibt dabei erhalten. Für einen vollständigen Neustart mit
gelöschten Redis-Queue-Daten verwenden Sie:

```bash
docker compose down -v
```

## Wichtige Hinweise

- Compose skaliert die Worker innerhalb einer einzelnen Docker Engine.
- Die Worker verwenden dasselbe Image und greifen über den Service-Namen
  `queue` auf Redis zu.
- Ein fester `container_name` würde wiederholbare Starts erschweren und ist
  für skalierte Worker ungeeignet. Deshalb verwaltet Compose alle Namen.
