"""
Tests for asset parsers.
"""

from __future__ import annotations
import pytest
from netstorm.assets import type_parser


def test_parse_altar():
    text = """
typename Altar
typeflags dontSave altar;
{
    description = "Altar";
    maxHitPoints = 1500;
    cost = 500;
}
P00 : default : "altar01.gif" #00;
L00 : : "altar21.gif" #00;
"""
    defn = type_parser.parse(text)
    assert defn.name == "Altar"
    assert "altar" in defn.flags
    assert defn.properties["maxHitPoints"] == 1500
    assert defn.properties["cost"] == 500
    assert len(defn.clusters) == 2
    assert defn.clusters[0].id == "P00"
    assert defn.clusters[0].files[0] == ("altar01.gif", 0)


def test_parse_bulf():
    text = """
typename bulf
typeflags walker shadow;
{
    description="Bulf";
    speed = 1.8;
}
A00 : : "bulfwalk.gif" #16 : "bulfwalk.gif" #48;
"""
    defn = type_parser.parse(text)
    assert defn.name == "bulf"
    assert defn.properties["speed"] == 1.8
    assert len(defn.clusters[0].files) == 2
    assert defn.clusters[0].files[1] == ("bulfwalk.gif", 48)
