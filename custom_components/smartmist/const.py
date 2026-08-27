"""Constants for the SmartMist integration."""

DOMAIN = "smartmist"

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Full aggregate state query (all sub-records, comma separated in the response).
CMD_QUERY_FULL_STATE = b"EE000."
CMD_POWER_ON = b"EE0100."
CMD_POWER_OFF = b"EE0101."

UPDATE_INTERVAL_SECONDS = 60
CONNECT_TIMEOUT_SECONDS = 15
RESPONSE_TIMEOUT_SECONDS = 8
