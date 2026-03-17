import pytest
from scrape_gitlab.description_parser import (
    remove_comments,
    get_headline_content,
    get_bullet_point,
    parse_description,
)
from scrape_gitlab.output import find_label


class TestRemoveComments:
    def test_single_comment(self):
        assert remove_comments("hello <!-- comment --> world") == "hello  world"

    def test_multiline_comment(self):
        text = "before\n<!-- multi\nline\ncomment -->\nafter"
        assert remove_comments(text) == "before\n\nafter"

    def test_no_comments(self):
        assert remove_comments("no comments here") == "no comments here"

    def test_multiple_comments(self):
        text = "a <!-- c1 --> b <!-- c2 --> c"
        assert remove_comments(text) == "a  b  c"


class TestGetHeadlineContent:
    def test_basic(self):
        text = "## Description of problem\nSomething is broken\n## Steps to reproduce\nDo X"
        result = get_headline_content(text, "Description of problem")
        assert "Something is broken" in str(result)

    def test_last_section(self):
        text = "## Additional information\nExtra details here"
        result = get_headline_content(text, "Additional information")
        assert "Extra details here" in str(result)

    def test_missing_section(self):
        text = "## Other section\nContent"
        result = get_headline_content(text, "Description of problem")
        assert result == "n/a"


class TestGetBulletPoint:
    def test_basic(self):
        text = "Host machine\nOperating system: Ubuntu 22.04\nArchitecture: x86_64"
        result = get_bullet_point(text, "Host", "Operating system")
        assert result == "Ubuntu 22.04"

    def test_with_backticks(self):
        text = "Host machine\nOperating system: `Ubuntu 22.04`\n"
        result = get_bullet_point(text, "Host", "Operating system")
        assert "Ubuntu" in result

    def test_missing(self):
        text = "Host machine\nArchitecture: x86_64\n"
        result = get_bullet_point(text, "Host", "Operating system")
        assert result == "n/a"


class TestParseDescription:
    def test_full_description(self):
        text = (
            "<!-- hidden -->\n"
            "Host machine\n"
            "Operating system: Linux\n"
            "Architecture: x86_64\n"
            "QEMU version: 8.0\n"
            "Emulated machine\n"
            "Operating system: Windows\n"
            "Architecture: aarch64\n"
            "## Description of problem\n"
            "It crashes\n"
            "## Steps to reproduce\n"
            "Run it\n"
            "## Additional information\n"
            "None\n"
        )
        result = parse_description(text)
        assert result["host-arch"] == "x86_64"
        assert result["qemu-version"] == "8.0"
        assert result["guest-arch"] == "aarch64"
        assert "It crashes" in str(result["description"])
        assert "Run it" in str(result["reproduce"])

    def test_missing_fields(self):
        result = parse_description("nothing useful here")
        assert result["host-os"] == "n/a"
        assert result["description"] == "n/a"


class TestFindLabel:
    def test_found(self):
        labels = ["target: x86", "host: linux", "accel: tcg"]
        assert find_label(labels, "target") == "target_x86"

    def test_missing(self):
        labels = ["host: linux"]
        assert find_label(labels, "target") == "target_missing"

    def test_colon_space_replaced(self):
        labels = ["accel: kvm"]
        result = find_label(labels, "accel")
        assert ": " not in result
        assert result == "accel_kvm"
