import sqlite3

from mud.collective_wiki import (
    WIKI_HTML,
    WikiFact,
    collective_wiki_snapshot,
    record_wiki_entry,
)


class TinyDatabase:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS characters (id INTEGER PRIMARY KEY, name TEXT)"
            )

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db


def test_collective_wiki_starts_blank_and_grows_only_from_published_knowledge(tmp_path):
    database = TinyDatabase(tmp_path / "wiki.db")

    empty = collective_wiki_snapshot(database)
    assert empty["entry_count"] == 0
    assert empty["entries"] == []
    assert empty["revision"] == 0

    assert record_wiki_entry(
        database,
        category="place",
        entry_key="waymeet_crossroads",
        title="Waymeet Crossroads",
        summary="A discovered location.",
        facts=(
            WikiFact(
                "description",
                "Description",
                "Roads meet beneath an old waymarker.",
                "room_view",
            ),
        ),
        character_name="Prime",
        astralis_day=77,
    )

    # Re-observing the exact same knowledge does not inflate the activity feed.
    assert not record_wiki_entry(
        database,
        category="place",
        entry_key="waymeet_crossroads",
        title="Waymeet Crossroads",
        summary="A discovered location.",
        facts=(
            WikiFact(
                "description",
                "Description",
                "Roads meet beneath an old waymarker.",
                "room_view",
            ),
        ),
        character_name="Another",
        astralis_day=78,
    )

    # The same article can deepen later without exposing any undiscovered sibling facts.
    assert record_wiki_entry(
        database,
        category="place",
        entry_key="waymeet_crossroads",
        title="Waymeet Crossroads",
        facts=(
            WikiFact(
                "hidden:bell",
                "Discovery",
                "A bell can be heard here under unusual conditions.",
                "hidden_discovery",
            ),
        ),
        character_name="Prime",
        astralis_day=79,
    )

    snapshot = collective_wiki_snapshot(database)
    assert snapshot["entry_count"] == 1
    assert snapshot["revision"] == 3
    assert snapshot["categories"] == {"place": 1}
    assert snapshot["entries"][0]["first_discoverer"] == "Prime"
    assert snapshot["entries"][0]["astralis_day"] == 77
    assert [fact["key"] for fact in snapshot["entries"][0]["facts"]] == [
        "description",
        "hidden:bell",
    ]


def test_wiki_page_has_live_blank_state_without_completion_spoilers():
    assert "The record is blank." in WIKI_HTML
    assert "Live collective knowledge" in WIKI_HTML
    assert "percent complete" in WIKI_HTML
    assert "setInterval(refresh,4000)" in WIKI_HTML
