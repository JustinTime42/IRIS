"""
Repository helpers for common database operations.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Device, DeviceBoot, SensorReading, SOSIncident, DeviceLog


async def upsert_device(
    session: AsyncSession,
    *,
    device_id: str,
    status: Optional[str] = None,
    last_seen: Optional[datetime] = None,
    version: Optional[str] = None,
    last_error: Optional[str] = None,
    last_boot: Optional[datetime] = None,
    ip_address: Optional[str] = None,
    rssi: Optional[int] = None,
) -> Device:
    """
    Create or update a device row.

    Args:
        session (AsyncSession): DB session
        device_id (str): Device ID
        status (Optional[str]): Current status
        last_seen (Optional[datetime]): Last seen time
        version (Optional[str]): Version string
        last_error (Optional[str]): Last error
        last_boot (Optional[datetime]): Last boot time
        ip_address (Optional[str]): IP address
        rssi (Optional[int]): WiFi RSSI

    Returns:
        Device: The persisted device row.
    """
    result = await session.execute(select(Device).where(Device.device_id == device_id))
    dev = result.scalar_one_or_none()
    now = datetime.utcnow()
    if dev is None:
        dev = Device(
            device_id=device_id,
            status=status,
            last_seen=last_seen or now,
            version=version,
            last_error=last_error,
            last_boot=last_boot,
            ip_address=ip_address,
            rssi=rssi,
        )
        session.add(dev)
    else:
        if status is not None:
            dev.status = status
        dev.last_seen = last_seen or now
        if version is not None:
            dev.version = version
        if last_error is not None:
            dev.last_error = last_error
        if last_boot is not None:
            dev.last_boot = last_boot
        if ip_address is not None:
            dev.ip_address = ip_address
        if rssi is not None:
            dev.rssi = rssi
    await session.commit()
    await session.refresh(dev)
    return dev


async def log_device_boot(
    session: AsyncSession,
    *,
    device_id: str,
    boot_time: Optional[datetime] = None,
    reason: Optional[str] = None,
    success: bool = True,
    version: Optional[str] = None,
    ip_address: Optional[str] = None,
    notes: Optional[str] = None,
) -> DeviceBoot:
    """Insert a device boot log entry."""
    entry = DeviceBoot(
        device_id=device_id,
        boot_time=boot_time or datetime.utcnow(),
        reason=reason,
        success=success,
        version=version,
        ip_address=ip_address,
        notes=notes,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def record_sensor_reading(
    session: AsyncSession,
    *,
    device_id: Optional[str],
    metric: str,
    value_float: Optional[float] = None,
    value_text: Optional[str] = None,
    recorded_at: Optional[datetime] = None,
    tags: Optional[dict] = None,
) -> SensorReading:
    """Insert a sensor reading."""
    row = SensorReading(
        device_id=device_id,
        metric=metric,
        value_float=value_float,
        value_text=value_text,
        recorded_at=recorded_at or datetime.utcnow(),
        tags=tags,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def create_sos_incident(
    session: AsyncSession,
    *,
    device_id: Optional[str],
    error_message: Optional[str] = None,
    details: Optional[dict] = None,
) -> SOSIncident:
    """Create a new SOS incident with status 'open'."""
    incident = SOSIncident(
        device_id=device_id,
        status="open",
        error_message=error_message,
        details=details,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


async def resolve_sos_incident(
    session: AsyncSession,
    *,
    incident_id: int,
    resolved_by: Optional[str] = None,
    resolution_notes: Optional[str] = None,
) -> Optional[SOSIncident]:
    """Mark an SOS incident as resolved."""
    result = await session.execute(select(SOSIncident).where(SOSIncident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return None
    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    incident.resolved_by = resolved_by
    incident.resolution_notes = resolution_notes
    await session.commit()
    await session.refresh(incident)
    return incident


async def get_weather_history(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    bucket: str = "hour",
) -> list[dict]:
    """
    Return aggregated weather history between start and end, bucketed by the given granularity.

    Args:
        session (AsyncSession): DB session.
        start (datetime): Inclusive start time (UTC).
        end (datetime): Exclusive end time (UTC).
        bucket (str): One of 'minute', 'hour', 'day'. Defaults to 'hour'.

    Returns:
        list[dict]: Rows of { ts: ISO string, temperature_f: float | None, pressure_inhg: float | None } sorted by ts.
    """
    # Guard: ensure supported buckets only
    if bucket not in {"minute", "hour", "day"}:
        bucket = "hour"

    # Use a single SQL to compute both series aligned by bucket for efficiency
    sql = text(
        """
        SELECT
            date_trunc(:bucket, recorded_at) AS ts,
            AVG(value_float) FILTER (WHERE metric = 'weather_temperature_f') AS temperature_f,
            AVG(value_float) FILTER (WHERE metric = 'weather_pressure_inhg') AS pressure_inhg
        FROM sensor_readings
        WHERE metric IN ('weather_temperature_f', 'weather_pressure_inhg')
          AND recorded_at >= :start
          AND recorded_at < :end
        GROUP BY ts
        ORDER BY ts ASC
        """
    )
    result = await session.execute(sql, {"bucket": bucket, "start": start, "end": end})
    rows = []
    for ts, temperature_f, pressure_inhg in result.fetchall():
        # Normalize to ISO 8601 without timezone info for client-side
        try:
            ts_iso = ts.isoformat()
        except Exception:
            ts_iso = str(ts)
        rows.append({
            "ts": ts_iso,
            "temperature_f": float(temperature_f) if temperature_f is not None else None,
            "pressure_inhg": float(pressure_inhg) if pressure_inhg is not None else None,
        })
    return rows


async def create_device_log(
    session: AsyncSession,
    *,
    device_id: str,
    level: str,
    component: str,
    message: str,
    details: Optional[dict] = None,
    device_timestamp: Optional[int] = None,
    sequence: Optional[int] = None,
) -> DeviceLog:
    """Insert a device log entry for debugging and crash analysis.
    
    Args:
        session (AsyncSession): DB session
        device_id (str): Device ID
        level (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        component (str): Component that generated the log
        message (str): Log message
        details (Optional[dict]): Additional structured data
        device_timestamp (Optional[int]): Device-local timestamp in ms
        sequence (Optional[int]): Sequence number from device
        
    Returns:
        DeviceLog: The persisted log entry
    """
    log_entry = DeviceLog(
        device_id=device_id,
        level=level.upper(),
        component=component,
        message=message,
        details=details,
        device_timestamp=device_timestamp,
        sequence=sequence,
    )
    session.add(log_entry)
    await session.commit()
    await session.refresh(log_entry)
    return log_entry


async def get_device_logs(
    session: AsyncSession,
    *,
    device_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    level: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
) -> list[DeviceLog]:
    """Retrieve device logs with optional filtering.
    
    Args:
        session (AsyncSession): DB session
        device_id (str): Device ID to get logs for
        start (Optional[datetime]): Start time filter
        end (Optional[datetime]): End time filter
        level (Optional[str]): Log level filter
        component (Optional[str]): Component filter
        limit (int): Maximum number of logs to return
        
    Returns:
        list[DeviceLog]: List of matching log entries ordered by creation time desc
    """
    query = select(DeviceLog).where(DeviceLog.device_id == device_id)
    
    if start:
        query = query.where(DeviceLog.created_at >= start)
    if end:
        query = query.where(DeviceLog.created_at <= end)
    if level:
        query = query.where(DeviceLog.level == level.upper())
    if component:
        query = query.where(DeviceLog.component == component)
        
    query = query.order_by(DeviceLog.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_device_crash_logs(
    session: AsyncSession,
    *,
    device_id: str,
    hours_back: int = 24,
) -> list[DeviceLog]:
    """Get logs that might indicate device crashes or issues.
    
    Args:
        session (AsyncSession): DB session
        device_id (str): Device ID
        hours_back (int): Hours to look back from now
        
    Returns:
        list[DeviceLog]: Error and critical logs that might indicate crashes
    """
    from datetime import timedelta
    start_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    query = select(DeviceLog).where(
        DeviceLog.device_id == device_id,
        DeviceLog.created_at >= start_time,
        DeviceLog.level.in_(['ERROR', 'CRITICAL'])
    ).order_by(DeviceLog.created_at.desc()).limit(50)
    
    result = await session.execute(query)
    return list(result.scalars().all())
