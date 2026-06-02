import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import json
import fakeredis
from unittest.mock import patch
import services.redis_publisher as pub_mod


def test_publish_uses_correct_channel():
    fake = fakeredis.FakeRedis(decode_responses=True)
    pub_mod._client = None
    channels = []
    orig = fake.publish

    def cap(ch, msg):
        channels.append(ch)
        return orig(ch, msg)

    fake.publish = cap
    with patch("services.redis_publisher.redis.from_url", return_value=fake):
        from services.redis_publisher import publish_round
        publish_round("sim-99", {"round": 1})
    assert "pubsub:sim:sim-99:rounds" in channels


def test_publish_payload_is_json():
    fake = fakeredis.FakeRedis(decode_responses=True)
    pub_mod._client = None
    payloads = []
    orig = fake.publish

    def cap(ch, msg):
        payloads.append(msg)
        return orig(ch, msg)

    fake.publish = cap
    with patch("services.redis_publisher.redis.from_url", return_value=fake):
        from services.redis_publisher import publish_round
        publish_round("sim-88", {"round": 2, "val": 0.5})
    assert json.loads(payloads[0])["val"] == 0.5
