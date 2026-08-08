from __future__ import annotations

import pytest

from onedash.layer_registry import LAYERS, all_layer_ids, get_layer


class TestLayerRegistry:
    def test_all_layer_ids_matches_number_of_layers(self):
        assert len(all_layer_ids()) == len(LAYERS)

    def test_layer_ids_are_unique(self):
        ids = all_layer_ids()
        assert len(ids) == len(set(ids))

    def test_get_layer_returns_matching_definition(self):
        for layer in LAYERS:
            assert get_layer(layer.layer_id) is layer

    def test_get_layer_unknown_id_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_layer("does-not-exist")

    def test_layer_id_property_matches_source_cls_source_id(self):
        for layer in LAYERS:
            assert layer.layer_id == layer.source_cls.source_id

    def test_every_layer_has_label_and_color(self):
        for layer in LAYERS:
            assert layer.label_pt
            assert layer.color.startswith("#")
