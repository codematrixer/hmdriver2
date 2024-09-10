# -*- coding: utf-8 -*-

import time
import pytest


# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# pip install -e .

from hmdriver2._client import HmClient
from hmdriver2.proto import HypiumResponse


@pytest.fixture
def client():
    client = HmClient("FMR0223C13000649")
    client.start()
    yield client
    client.release()


def test_client_create(client):
    resp = client.invoke("Driver.create")  # {"result":"Driver#0"}
    assert resp == HypiumResponse("Driver#0")


def test_client_invoke(client):
    resp: HypiumResponse = client.invoke("Driver.getDisplaySize")
    assert resp == HypiumResponse({"x": 1260, "y": 2720})

    # client.hdc.start_app("com.kuaishou.hmapp", "EntryAbility")
    client.hdc.start_app("com.samples.test.uitest", "EntryAbility")

    resp = client.invoke("On.text", this="On#seed", args=["showToast"])   # {"result":"On#0"}
    by = resp.result
    resp = client.invoke("Driver.findComponent", this="Driver#0", args=[by])   # {"result":"Component#0"}
    t1 = int(time.time())
    resp = client.invoke("Driver.waitForComponent", this="Driver#0", args=[by, 2000])   # {"result":"Component#0"}

    t2 = int(time.time())
    print(f"take: {t2 - t1}")
    component = resp.result

    resp = client.invoke("Component.getText", this=component, args=[])   # {"result":"Component#0"}
    assert resp.result == "showToast"