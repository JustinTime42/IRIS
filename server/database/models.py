"""
ORM models for IRIS PostgreSQL database using SQLAlchemy 2.x.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        nullable=False,
    )


class Device(Base):
    """
    Represents a physical device (Pico W) in the system.

    Attributes:
        device_id (str): Unique ID of the device.
        status (str): Current status (online, offline, needs_help, updating, error).
        last_seen (datetime): Last time the device was seen.
        version (str): Reported app version/commit.
        last_error (str): Last error message if any.
        last_boot (datetime): Last boot time reported.
        ip_address (str): Last observed IP.
        rssi (int): Last observed WiFi RSSI.
    """

    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    version: Mapped[Optional[str]] = mapped_column(String(64))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    last_boot: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    rssi: Mapped[Optional[int]] = mapped_column(Integer)

    boots: Mapped[list[DeviceBoot]] = relationship(back_populates="device")  # type: ignore[name-defined]
    sos_incidents: Mapped[list[SOSIncident]] = relationship(back_populates="device")  # type: ignore[name-defined]


class DeviceBoot(Base):
    """
    Device boot events audit log.

    Attributes:
        id (int): Auto-increment primary key.
        device_id (str): FK to `devices.device_id`.
        boot_time (datetime): When the device booted.
        reason (str): Optional reason (power_on, crash_recovery, update, etc.).
        success (bool): Whether the boot completed successfully.
        version (str): Version at boot.
        ip_address (str): IP at boot.
        notes (str): Additional notes.
    """

    __tablename__ = "device_boots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    boot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(64))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    device: Mapped[Device] = relationship(back_populates="boots")

    __table_args__ = (
        Index("ix_device_boots_device_time", "device_id", "boot_time"),
    )


class SOSIncident(Base):
    """
    SOS incidents raised by devices that require human intervention.

    Attributes:
        id (int): Auto-increment primary key.
        device_id (str): FK to `devices.device_id`.
        status (str): 'open' or 'resolved'.
        error_message (str): Short message.
        details (JSON): Enhanced details payload from device.
        resolved_at (datetime): When resolved.
        resolved_by (str): Who resolved it.
        resolution_notes (str): Notes about fix.
    """

    __tablename__ = "sos_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), ForeignKey("devices.device_id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(String(64))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)

    device: Mapped[Optional[Device]] = relationship(back_populates="sos_incidents")

    __table_args__ = (
        CheckConstraint("status IN ('open','resolved')", name="ck_sos_status"),
        Index("ix_sos_device_status_time", "device_id", "status", "created_at"),
    )


class SensorReading(Base):
    """
    Time-series sensor readings.

    Attributes:
        id (int): Auto-increment primary key.
        device_id (str): Device that reported the reading.
        metric (str): Metric name (e.g., 'temperature_f', 'pressure_inhg', 'freezer_temp_f', 'door_state').
        value_float (float): Numeric value if applicable.
        value_text (str): Text value for categorical metrics (e.g., door states).
        recorded_at (datetime): Timestamp of the reading.
        tags (JSON): Optional extra structured data.
    """

    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), ForeignKey("devices.device_id", ondelete="SET NULL"))
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value_float: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False)
    tags: Mapped[Optional[dict]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_sensor_device_metric_time", "device_id", "metric", "recorded_at"),
    )


class DeviceLog(Base):
    """
    Detailed device logging for crash analysis and debugging.

    Attributes:
        id (int): Auto-increment primary key.
        device_id (str): FK to devices.device_id.
        level (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        component (str): Component that generated the log (bootstrap, app, wifi, mqtt, sensors).
        message (str): Log message.
        details (JSON): Additional structured data (stack trace, system stats, etc.).
        device_timestamp (int): Device-local timestamp in ms (ticks_ms).
        sequence (int): Sequence number for ordering logs from same device.
    """

    __tablename__ = "device_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component: Mapped[str] = mapped_column(String(32), nullable=False)  # bootstrap, app, wifi, mqtt, sensors, etc.
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    device_timestamp: Mapped[Optional[int]] = mapped_column(Integer)  # Device ticks_ms for correlation
    sequence: Mapped[Optional[int]] = mapped_column(Integer)  # Sequence number from device

    __table_args__ = (
        CheckConstraint("level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')", name="ck_log_level"),
        Index("ix_device_logs_device_time", "device_id", "created_at"),
        Index("ix_device_logs_level_time", "level", "created_at"),
        Index("ix_device_logs_component", "component", "created_at"),
    )


class SystemEvent(Base):
    """
    System-wide events such as power outages or server changes.

    Attributes:
        id (int): Auto-increment primary key.
        type (str): Event type key.
        message (str): Human-readable message.
        meta (JSON): Additional structured data.
    """

    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    # 'metadata' is reserved by SQLAlchemy Declarative; use attribute 'meta' and keep column name 'metadata'
    meta: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
