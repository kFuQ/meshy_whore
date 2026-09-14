"""Unit tests for the pure-logic modules (no display required)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from meshy_studio.crypto import Cryptor, CryptoError, load_or_create_master_key
from meshy_studio.schema import MeshyParams, iter_result_files
from meshy_studio.store import SecureStore


class TestCrypto(unittest.TestCase):
    def setUp(self):
        self.key = load_or_create_master_key(Path(tempfile.mkdtemp()) / "m.key")
        self.c = Cryptor(self.key)

    def test_roundtrip(self):
        token = self.c.encrypt(b"secret-value")
        self.assertNotIn(b"secret-value", token)  # not plaintext
        self.assertEqual(self.c.decrypt(token), b"secret-value")

    def test_str_roundtrip(self):
        t = self.c.encrypt_str("héllo-key-123")
        self.assertEqual(self.c.decrypt_str(t), "héllo-key-123")

    def test_tamper_detected(self):
        token = bytearray(self.c.encrypt(b"data"))
        token[-1] ^= 0x01  # flip a tag bit
        with self.assertRaises(CryptoError):
            self.c.decrypt(bytes(token))

    def test_associated_data_binding(self):
        token = self.c.encrypt(b"x", associated_data=b"ctx-A")
        with self.assertRaises(CryptoError):
            self.c.decrypt(token, associated_data=b"ctx-B")

    def test_passphrase_is_deterministic(self):
        k1 = load_or_create_master_key(Path("/nonexistent/ignored"), passphrase="pw")
        k2 = load_or_create_master_key(Path("/nonexistent/ignored"), passphrase="pw")
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 32)  # AES-256


class TestSchema(unittest.TestCase):
    def test_defaults_valid(self):
        p = MeshyParams(image_urls=["https://x/y.png"])
        self.assertEqual(p.validate(), [])

    def test_pbr_requires_texture(self):
        p = MeshyParams(should_texture=False, enable_pbr=True)
        self.assertTrue(any("enable_pbr" in e for e in p.validate()))

    def test_animation_requires_rigging(self):
        p = MeshyParams(enable_animation=True, enable_rigging=False)
        self.assertTrue(any("enable_animation" in e for e in p.validate()))

    def test_polycount_bounds(self):
        self.assertTrue(MeshyParams(target_polycount=5).validate())
        self.assertTrue(MeshyParams(target_polycount=10_000_000).validate())

    def test_arguments_omit_texture_fields_when_disabled(self):
        p = MeshyParams(should_texture=False, texture_prompt="ignore me")
        args = p.to_arguments()
        self.assertNotIn("texture_prompt", args)
        self.assertNotIn("enable_pbr", args)

    def test_arguments_include_rig_when_enabled(self):
        p = MeshyParams(enable_rigging=True, enable_animation=True, animation_action_id=5)
        args = p.to_arguments()
        self.assertTrue(args["enable_rigging"])
        self.assertEqual(args["animation_action_id"], 5)

    def test_iter_result_files(self):
        result = {
            "model_glb": {"url": "https://x/model.glb", "file_name": "model.glb"},
            "thumbnail": {"url": "https://x/t.png"},
            "model_urls": {"fbx": {"url": "https://x/model.fbx"}, "obj": {}},
            "texture_urls": [{"base_color": {"url": "https://x/tex.png"}}],
        }
        labels = [lbl for lbl, _ in iter_result_files(result)]
        self.assertIn("Model (GLB)", labels)
        self.assertIn("Model (FBX)", labels)
        self.assertIn("Thumbnail", labels)
        self.assertTrue(any("base_color" in l for l in labels))
        # obj had no url -> excluded
        self.assertNotIn("Model (OBJ)", labels)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["MESHY_STUDIO_HOME"] = self.tmp
        # Reload config so paths pick up the override.
        import importlib

        import meshy_studio.config as cfg
        import meshy_studio.store as store

        importlib.reload(cfg)
        importlib.reload(store)
        self.store_mod = store

    def test_api_key_encrypted_on_disk(self):
        s = self.store_mod.SecureStore()
        settings = s.load_settings()
        settings["api_key"] = "super-secret-key-abc123"
        s.save_settings(settings)

        from meshy_studio import config as cfg

        raw = Path(cfg.SETTINGS_FILE).read_bytes()
        self.assertNotIn(b"super-secret-key-abc123", raw)  # encrypted!

        s2 = self.store_mod.SecureStore()
        self.assertEqual(s2.load_settings()["api_key"], "super-secret-key-abc123")

    def test_history_roundtrip(self):
        s = self.store_mod.SecureStore()
        s.append_history({"status": "completed", "request_id": "r1"})
        self.assertEqual(len(s.load_history()), 1)

    def tearDown(self):
        os.environ.pop("MESHY_STUDIO_HOME", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
