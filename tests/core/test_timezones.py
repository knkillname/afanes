"""Environment checks for the bundled time-zone data and local zone detection."""

import zoneinfo

import tzlocal


class TestTimeZoneDependencies:
    def test_iana_rules_resolve_from_the_bundled_database(self) -> None:
        zone = zoneinfo.ZoneInfo("America/Mexico_City")

        assert zone.key == "America/Mexico_City"

    def test_the_local_zone_is_an_iana_name(self) -> None:
        name = tzlocal.get_localzone_name()

        assert zoneinfo.ZoneInfo(name).key == name
