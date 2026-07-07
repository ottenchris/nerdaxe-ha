# NerdAxe Miner for Home Assistant

Home Assistant custom integration for NerdAxe Gamma, NerdQAxe, AxeOS and
ESP-Miner compatible Bitcoin miners.

The integration talks directly to the miner in your local network:

```text
GET http://<miner-host>/api/system/info
```

It creates native Home Assistant entities for live dashboards and automations.
If explicitly enabled, it can additionally keep compact raw history files
outside Home Assistant's normal recorder database.

## Status

This is a conservative controls MVP. Polling is still read-only, and the only
write action is an explicit Home Assistant restart button.

Implemented:

- UI setup via Home Assistant config flow
- Local polling through Home Assistant's aiohttp client session
- `DataUpdateCoordinator` based entity updates
- Sensor and binary sensor entities
- Restart button entity
- Read-only fan and tuning setting diagnostics
- Optional daily NDJSON history under the Home Assistant config directory
- gzip archival for old raw day files
- storage-budget retention
- diagnostics support

Not implemented yet:

- fan speed writes
- frequency/core-voltage writes
- temp-target writes
- pool settings writes
- firmware update
- history export services
- session and tuning-profile analysis

## Installation

### HACS custom repository

1. In Home Assistant, open HACS.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add:

   ```text
   https://github.com/ottenchris/nerdaxe-ha
   ```

4. Select repository type **Integration**.
5. Install **NerdAxe Miner**.
6. Restart Home Assistant.
7. Go to **Settings > Devices & services > Add integration**.
8. Search for **NerdAxe Miner** and enter your miner host or IP address.

Replace the repository URL if you publish this under a different name.

### Manual installation

Copy the integration folder into your Home Assistant config directory:

```text
config/custom_components/nerdaxe_miner/
```

The directory must contain the files from:

```text
custom_components/nerdaxe_miner/
```

Restart Home Assistant, then add the integration from the UI.

## Configuration

Initial setup asks for:

- **Miner host or IP address**: for example `192.168.178.70`
- **Scan interval**: 5-300 seconds, default `10`
- **Enable local raw history**: default disabled
- **Maximum history storage in MB**: default `512`
- **Days to keep uncompressed**: default `30`
- **Store raw API payload**: default disabled

All non-host settings are also available through the integration options page.
Changing options reloads the integration.

## Entities

Numeric sensors:

- Hashrate, hashrate 1m, 10m, 1h, 1d
- ASIC temperature
- VR temperature
- Power
- Voltage
- Current
- Fan percent
- Fan RPM
- Manual fan speed
- Target temperature
- Overheat temperature
- Shares accepted
- Shares rejected
- Best diff
- Best session diff
- Wi-Fi RSSI
- Frequency
- Actual frequency
- Default frequency
- Core voltage
- Actual core voltage
- Default core voltage
- Uptime

Text sensors:

- Firmware version
- Hostname

Timestamp sensors:

- Last boot, derived from the current sample time minus `uptimeSeconds`

Binary sensors:

- Stratum connected
- Automatic fan speed

Buttons:

- Restart

Large raw API payloads are not stored as entity attributes. This keeps Home
Assistant's recorder database smaller and avoids constantly changing large
attribute blobs.

## Controls

Version `0.2.0` adds one writable control:

```text
POST http://<miner-host>/api/system/restart
```

Home Assistant exposes this as a **Restart** button entity with restart device
class. Pressing it asks the miner to reboot. This can interrupt mining, network
connectivity and dashboards until the device comes back online.

Important safety behavior:

- Polling never calls write endpoints. The coordinator only reads
  `GET /api/system/info`.
- Restart is never run automatically by setup, polling, diagnostics or the
  options flow.
- Home Assistant buttons can still be used in automations. Add your own
  automation conditions if you expose this button to broader dashboards.

The AxeOS / ESP-Miner API also documents:

```text
PATCH http://<miner-host>/api/system
```

with settings such as `fanspeed`, `autofanspeed`, `temptarget`, `frequency`,
`coreVoltage` and `overclockEnabled`. This integration intentionally does not
write those settings yet. Fan and tuning values are exposed as read-only
diagnostic entities until hardware-specific ranges and guardrails are added.

Firmware update endpoints such as `/api/system/OTA` and `/api/system/OTAWWW`
are explicitly out of scope.

## Raw History

Raw history is opt-in. If enabled, samples are written below the Home Assistant
config directory:

```text
<config>/nerdaxe_recorder/<device-id>/
```

Files use one UTC day per file:

```text
history-YYYY-MM-DD.ndjson
history-YYYY-MM-DD.ndjson.gz
```

Each line contains one JSON object with `ts`, normalized fields such as
`hashRate`, `temp`, `power`, `fanPercent`, `manualFanSpeed`, `frequency`,
`defaultFrequency`, `coreVoltage`, `defaultCoreVoltage`, `lastBoot` and
`stratumConnected`, plus sanitized unrecognized API fields under `extra` when
present.

Fetch failures are stored as event rows:

```json
{"eventType":"fetch_error","source":"coordinator","message":"..."}
```

Retention behavior:

- Days older than the uncompressed keep window are gzipped.
- If the storage budget is exceeded, the oldest compressed archives are deleted
  first.
- If the budget is still exceeded, older non-current day files are deleted.

## Home Assistant Concepts

**Custom integration**: Python code loaded by Home Assistant from
`custom_components/nerdaxe_miner`. HACS only installs and updates this folder;
Home Assistant still runs the integration.

**Config flow**: the UI setup wizard. This integration uses it to collect the
miner host and validate the local API before creating a config entry.

**Options flow**: the UI settings page for an existing config entry. This is
where scan interval and history settings can be changed later.

**Entity**: a value Home Assistant can display, record and automate. This
integration exposes miner metrics as real sensor entities instead of one large
JSON attribute.

**Button entity**: a stateless Home Assistant entity for one-off actions. This
integration uses it for restart because restart is an explicit command, not a
persistent on/off state.

**Device**: Home Assistant groups all entities from the same miner under one
device in the device registry.

**DataUpdateCoordinator**: Home Assistant's standard helper for polling one API
once per interval and sharing the result across many entities.

**Recorder vs raw history**: Home Assistant's recorder stores entity state
history for dashboards and long-term statistics. This integration's raw history
is separate and keeps compact NDJSON samples for later export, tuning analysis
or external processing.

**Diagnostics**: a Home Assistant support dump for the integration. It includes
redacted config/options, the last normalized sample and history-store settings.

## Privacy Notes

The default entity states are small and do not include full upstream payloads.
Local raw history is disabled by default.

If **Enable local raw history** is enabled, the local NDJSON files may contain
miner identifiers, hostnames, pool-related status and other fields returned by
the miner API. If **Store raw API payload** is also enabled, those files can
contain the full upstream payload, including pool URLs, usernames or
wallet-like identifiers. Keep raw history files private and treat Home
Assistant backups that include them as private too.

## Development

Install test dependencies:

```bash
python -m pip install -e ".[test]"
```

Install the local pre-commit hooks once per clone:

```bash
pre-commit install
```

The hooks run `ruff check --fix` and `ruff format` before each commit. The Ruff
hook version is pinned in `.pre-commit-config.yaml`.

Run checks:

```bash
ruff format --check .
ruff check .
pytest
```

Run the same pre-commit hooks manually across the full repository:

```bash
pre-commit run --all-files
```

The core normalization and history-store tests are written with `unittest`, so
they can also run without Home Assistant installed:

```bash
python -m unittest discover
```

## Repository Layout

```text
custom_components/nerdaxe_miner/
  __init__.py
  api.py
  binary_sensor.py
  button.py
  config_flow.py
  const.py
  coordinator.py
  diagnostics.py
  history_store.py
  manifest.json
  models.py
  normalizer.py
  sensor.py
  strings.json
tests/
  test_api.py
  test_coordinator.py
  test_history_store.py
  test_normalizer.py
```

## License

MIT
