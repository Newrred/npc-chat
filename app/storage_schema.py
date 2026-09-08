"""SQLite schema v1. Relationship scores are normalized, checked columns."""
from sqlalchemy import (JSON, CheckConstraint, Column, Float, ForeignKey, ForeignKeyConstraint,
                        Integer, MetaData, String, Table, Text)

metadata = MetaData()
profiles = Table("profiles", metadata,
    Column("id", String(64), primary_key=True), Column("created", Float, nullable=False))
sessions = Table("sessions", metadata,
    Column("id", String(128), primary_key=True),
    Column("profile_id", ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
    Column("character_id", String(64), nullable=False))
relationships = Table("character_relationships", metadata,
    Column("profile_id", ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("character_id", String(64), primary_key=True),
    *[Column(name, Integer, nullable=False) for name in ("affection", "trust", "comfort", "interest", "irritation")],
    Column("flags", JSON, nullable=False), Column("summary", Text, nullable=False),
    Column("history", JSON, nullable=False), Column("recent", JSON, nullable=False),
    Column("version", Integer, nullable=False), Column("turn_count", Integer, nullable=False),
    *[CheckConstraint(f"{name} BETWEEN 0 AND 100", name=f"ck_{name}")
      for name in ("affection", "trust", "comfort", "interest", "irritation")])
turns = Table("turns", metadata,
    Column("profile_id", String(64), primary_key=True), Column("character_id", String(64), primary_key=True),
    Column("client_turn_id", String(128), primary_key=True), Column("payload_hash", String(64), nullable=False),
    Column("response", JSON, nullable=False), Column("decision", JSON, nullable=False),
    Column("user_message", Text, nullable=False), Column("created", Float, nullable=False),
    ForeignKeyConstraint(["profile_id", "character_id"],
                         ["character_relationships.profile_id", "character_relationships.character_id"],
                         ondelete="CASCADE"))
memories = Table("memories", metadata,
    Column("profile_id", String(64), primary_key=True), Column("character_id", String(64), primary_key=True),
    Column("key", String(64), primary_key=True), Column("kind", String(20), nullable=False),
    Column("content", Text, nullable=False), Column("importance", Integer, nullable=False),
    Column("confidence", Float, nullable=False), Column("source_turn", String(128), nullable=False),
    Column("updated", Float, nullable=False),
    CheckConstraint("importance BETWEEN 0 AND 3"), CheckConstraint("confidence BETWEEN 0 AND 1"),
    ForeignKeyConstraint(["profile_id", "character_id"],
                         ["character_relationships.profile_id", "character_relationships.character_id"],
                         ondelete="CASCADE"))
imports = Table("legacy_imports", metadata,
    Column("source_id", String(256), primary_key=True),
    Column("profile_id", String(64), nullable=False),
    Column("imported_at", Float, nullable=False))
