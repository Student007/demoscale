# Demoscale – Docker-Skalierungsdemo

Diese Demo zeigt horizontale Skalierung mit Docker Compose: Ein Dashboard nimmt
Aufträge an, ein Producer legt sie in Redis ab und mehrere identische Worker
holen die Aufträge aus derselben Queue. Im Browser werden Queue-Länge,
verarbeitete Jobs und die einzelnen Worker-Container sichtbar.

Die Demo ist ein lokales Lehrbeispiel, kein produktionsfertiger Queue- oder
Monitoringdienst.

## Stand der Demo

Die aktuelle Struktur ist vollständig für die lokale Untersuchung vorbereitet:

- `queue` verwendet Redis 7.4.2 mit AOF und einem persistenten Named Volume.
- `producer`, `dashboard` und `worker` werden aus eigenen Dockerfiles gebaut.
- Die Worker sind zustandsarm und können mit `--scale worker=N` vervielfacht
  werden.
- Healthchecks und `depends_on` mit Health-Bedingung steuern den Compose-Start.
- Die eigenen Images können mit Buildx Bake als `linux/amd64`- und
  `linux/arm64`-Images veröffentlicht werden.
- `stack.swarm.yaml` zeigt den optionalen Transfer auf Docker Swarm.

Der Webcontainer heißt exakt `demoscale`. Die automatisch erzeugten Worker
heißen beispielsweise `demoscale-worker-1` bis `demoscale-worker-4`. Ein fester
`container_name` für Worker wäre ungeeignet, weil Docker dann keine mehreren
Replikas mit demselben Namen starten könnte.

## Voraussetzungen

- Docker Desktop oder Docker Engine
- Docker Compose v2
- für den Registry-Push: ein Docker-Hub-Konto und aktiviertes Buildx

Die Befehle in dieser README werden aus diesem Ordner ausgeführt:

```bash
cd begleitmaterial/docker-skalierungsdemo
```

## Lokal starten

```bash
cp .env.example .env
docker compose config
docker compose up -d --build --scale worker=1
docker compose ps
```

Öffnen Sie anschließend <http://localhost:8080>. Der Port kann in `.env` über
`DASHBOARD_PORT` geändert werden. Der technische JSON-Endpunkt ist unter
<http://localhost:8080/status> erreichbar.

## Skalierung beobachten

Erzeugen Sie Jobs in der Browser-GUI oder per Kommandozeile:

```bash
curl "http://localhost:8080/enqueue?n=20"
docker compose logs --tail=30 worker
docker compose up -d --scale worker=4
curl "http://localhost:8080/enqueue?n=40"
docker compose ps
docker compose logs --tail=50 worker
```

Die vier Worker verwenden dasselbe Image, laufen aber in eigenen Containern.
Alle greifen per Compose-Service-DNS auf `queue:6379` zu; feste Container-IP-
Adressen sind nicht erforderlich. `BRPOP` blockiert, bis ein Auftrag vorhanden
ist. `PROCESS_SECONDS` in `.env` steuert die simulierte Bearbeitungszeit.

## Wichtige Untersuchungsbefehle

```bash
docker compose config
docker compose ps
docker compose logs --tail=50 worker
docker compose exec --index 1 worker sh
docker inspect demoscale
docker volume inspect demoscale-queue
```

`docker compose down` entfernt Container und Netzwerk, lässt das Named Volume
aber bestehen. `docker compose down -v` entfernt zusätzlich `demoscale-queue`
und damit den gespeicherten Redis-Zustand.

## Images und Docker Hub

Die Demo besteht aus drei eigenen Images:

| Dienst | Tag im Docker-Hub-Repository `danbu/demoscale` | Aufgabe |
|---|---|---|
| `dashboard` | `demoscale-dashboard-1.0.0` | Browser-GUI und Status |
| `producer` | `demoscale-producer-1.0.0` | Aufträge erzeugen |
| `worker` | `demoscale-worker-1.0.0` | Aufträge verarbeiten |

`queue` verwendet weiterhin das offizielle Image `redis:7.4.2-alpine3.21`.
Ein Docker-Hub-Repository kann mehrere Tags aufnehmen; dadurch bleiben die
drei Dienste im Repository `demoscale` getrennt adressierbar.
Die ausführbare Docker-Hub-Beschreibung steht in
[`README.dockerhub.md`](README.dockerhub.md).

### Multi-Platform-Images bauen und pushen

Erstellen Sie auf Docker Hub ein Repository mit dem Namen `demoscale` (Docker Hub:
`My Hub` → `Create repository`). Verwenden Sie für die drei Dienste die
unterschiedlichen Tag-Präfixe. Bei `docker login` ist ein Docker-Hub-
Access-Token als Passwort die sichere Wahl.

```bash
export REGISTRY_USER=danbu
export IMAGE_REPOSITORY=demoscale
export IMAGE_TAG=1.0.0

docker login
docker buildx create --name demoscale-builder --driver docker-container --use
docker buildx inspect --bootstrap
docker buildx bake --push
```

Der Bake-Build veröffentlicht jeweils `linux/amd64` und `linux/arm64`.
Prüfen Sie danach zum Beispiel:

```bash
docker buildx imagetools inspect \
  "$REGISTRY_USER/$IMAGE_REPOSITORY:demoscale-worker-$IMAGE_TAG"
```

Wenn der Builder bereits existiert, verwenden Sie statt `docker buildx create`
einfach `docker buildx use demoscale-builder`.

### Demo mit den veröffentlichten Images starten

Setzen Sie in `.env` den Docker-Hub-Namespace und den veröffentlichten Tag:

```dotenv
REGISTRY_USER=danbu
IMAGE_REPOSITORY=demoscale
IMAGE_TAG=1.0.0
```

Laden und starten Sie anschließend ohne lokalen Neubau:

```bash
docker compose pull
docker compose up -d --no-build --scale worker=4
docker compose ps
```

Für die lokale Entwicklung genügt dagegen `docker compose up -d --build`.

## Mehrere physische Rechner: optionaler Swarm-Transfer

Compose skaliert auf einer einzelnen Docker Engine. Für mehrere Hosts müssen
die drei Images aus Docker Hub erreichbar sein:

```bash
export REGISTRY_USER=danbu
export IMAGE_REPOSITORY=demoscale
export IMAGE_TAG=1.0.0
docker swarm init --advertise-addr <manager-ip>
docker stack deploy -c stack.swarm.yaml demoscale
docker service ps demoscale_worker
docker service scale demoscale_worker=4
```

Das Redis-Volume ist lokal und damit nicht automatisch hostübergreifend nutzbar.
Für einen echten Mehrhost-Betrieb braucht Redis Shared Storage oder eine
bewusste Platzierung auf einem Knoten.

## Aufräumen

```bash
docker compose down
docker compose down -v
docker buildx prune
```

Der zweite Compose-Befehl löscht bewusst den Queue-Zustand; der letzte Befehl
bereinigt nicht mehr benötigte Build-Cache-Daten.

## Dateien

| Datei | Zweck |
|---|---|
| `compose.yaml` | lokale Services, Netzwerk, Healthchecks und Skalierung |
| `dashboard/app.py` | Browser-GUI und `/status` |
| `producer/app.py` | HTTP-Endpunkt und Redis-Queue |
| `worker/app.py` | blockierender Queue-Konsument und Heartbeat |
| `docker-bake.hcl` | Multi-Platform-Build und Push der drei Images |
| `stack.swarm.yaml` | optionales Swarm-Manifest |
| `.env.example` | lokale Konfigurationsvorlage |
| `README.dockerhub.md` | Text für die Docker-Hub-Repository-Übersicht |
