#!/bin/sh

# Create password file if it doesn't exist
if [ ! -f /mosquitto/config/passwd ] && [ -n "${MOSQUITTO_USERNAME}" ] && [ -n "${MOSQUITTO_PASSWORD}" ]; then
    echo "Creating password file..."
    touch /mosquitto/config/passwd
    mosquitto_passwd -b /mosquitto/config/passwd "${MOSQUITTO_USERNAME}" "${MOSQUITTO_PASSWORD}"
    chmod 644 /mosquitto/config/passwd
    echo "Password file created."
fi

# Start mosquitto
echo "Starting Mosquitto..."
exec /docker-entrypoint.sh /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
