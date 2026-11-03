# Gigaset Weather Info Service

A lightweight weather information service for the Gigaset C610A IP base station and C610H handset.

The application replaces the original Gigaset Info Services endpoints with a local Flask service. It retrieves current weather from Open-Meteo and returns XHTML Mobile 1.2 compatible with the handset's limited renderer.

## Features

- Current temperature and weather conditions
- Feels-like temperature, humidity, pressure and wind speed
- Date and weekday in the page title
- Weather API caching for 30 minutes
- Screen refresh at midnight to update the date
- Last known weather data retained during API failures
- Health-check endpoint
- Configurable location and time zone

## Requirements

- Python 3.10 or newer
- Network access to api.open-meteo.com
- Local DNS override directing the Gigaset Info Services hostname to this server
- Gigaset C610A IP with a compatible handset

## Installation

```bash
cd /opt/gigaset
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
```

## Running as an OpenRC service (Alpine Linux)

The repository includes `gigaset-info.openrc`, an OpenRC service definition for running the weather server under Gunicorn.

The service uses `supervise-daemon` to monitor the Gunicorn process and restart it if necessary.

### Install the service

Install the application and its Python dependencies first, as described in the Installation section.

Copy the OpenRC script to the system service directory:

```bash
cp /opt/gigaset/gigaset-info.openrc /etc/init.d/gigaset-info
chmod 755 /etc/init.d/gigaset-info
```

Enable automatic startup:

```bash
rc-update add gigaset-info default
```

Start the service:

```bash
rc-service gigaset-info start
```

### Service management

Check service status:

```bash
rc-service gigaset-info status
```

Restart after changing `app.py` or `.env`:

```bash
rc-service gigaset-info restart
```

Stop the service:

```bash
rc-service gigaset-info stop
```

Disable automatic startup:

```bash
rc-update del gigaset-info default
```

### Logs

The service writes standard output and error messages to:

`/var/log/gigaset.log`

Monitor the log:

```bash
tail -f /var/log/gigaset.log
```

### Verify installation

Check the health endpoint:

```bash
curl -fsS http://127.0.0.1/health
```

Expected response:

```json
{"status":"ok"}
```

Check the weather endpoint:

```bash
curl -fsS http://127.0.0.1/info/request.do
```

The response should contain XHTML Mobile 1.2 with the current weather information.

**Note:** The health endpoint only verifies that the Flask application is responding. It does not test connectivity to Open-Meteo.

### Service configuration

The OpenRC script uses the following settings:

| Setting | Value |
|---|---|
| Service name | `gigaset-info` |
| Working directory | `/opt/gigaset` |
| Gunicorn executable | `/opt/gigaset/venv/bin/gunicorn` |
| Listen address | `0.0.0.0:80` by default |
| Gunicorn workers | 1 |
| Supervisor | OpenRC `supervise-daemon` |
| Runtime directory | `/run/gigaset` |
| Log file | `/var/log/gigaset.log` |
| Service user | `root` |

The listen address can be overridden with the `BIND` environment variable.

The application reads `LAT`, `LON`, and `TZ` from `/opt/gigaset/.env` using `python-dotenv`.

**Security note:** The supplied service runs as `root` because it binds directly to privileged port 80. For an installation exposed beyond a trusted LAN, consider running Gunicorn as a dedicated unprivileged user behind a reverse proxy.

### Troubleshooting

If the service fails to start, check its status and logs:

```bash
rc-service gigaset-info status
tail -n 50 /var/log/gigaset.log
```

Verify that port 80 is available:

```bash
ss -ltnp '( sport = :80 )'
```

Check Python syntax:

```bash
cd /opt/gigaset && venv/bin/python -m py_compile app.py
```

If weather information is unavailable, verify that the server can establish an HTTPS connection to `api.open-meteo.com`. The application retains its last successfully fetched weather data in memory, but this cache is cleared when the service restarts.

Edit `.env` to configure your coordinates and time zone.

## Configuration

| Variable | Description | Example |
|---|---|---|
| LAT | Latitude | 12.34 |
| LON | Longitude | 56.78 |
| TZ | IANA time zone | Etc/GMT |

The application loads `.env` automatically using `python-dotenv`.

## Running

```bash
cd /opt/gigaset && venv/bin/gunicorn --bind 0.0.0.0:80 --workers 1 app:app
```

Port 80 is required by the current local Gigaset configuration. Binding to this privileged port requires appropriate permissions.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/info/request.do` | Weather XHTML |
| `/info/menu.jsp` | Weather XHTML |
| `/health` | JSON health check |

Test locally:

```bash
curl -s http://127.0.0.1/health
```

```bash
curl -s http://127.0.0.1/info/request.do
```

## Caching

The weather data is cached for 1800 seconds.

The XHTML expiration interval is calculated separately and shortened before midnight, allowing the handset to refresh the displayed date.

If Open-Meteo becomes unavailable, the service returns the last successfully fetched weather data, marked `STALE DATA`.

The weather cache is held in process memory. Restarting Gunicorn clears it.

## Gigaset display limitations

The C610H Info Services renderer supports only a limited subset of XHTML and CSS.

Verified behavior:

- Bold text works.
- CSS font-size changes do not work.
- Standard HTML heading tags do not enlarge text.
- External PNG and WBMP images were not displayed in testing.

## License

No license specified.

