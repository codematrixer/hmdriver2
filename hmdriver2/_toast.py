# -*- coding: utf-8 -*-

from .proto import HypiumResponse


class ToastWatcher:
    def __init__(self, session: "Driver"):  # type: ignore
        self.session = session

    def start(self) -> bool:
        """
        Initiates the observer to listen for a UI toast event

        Returns:
            bool: True if the observer starts successfully, else False.
        """
        api = "Driver.uiEventObserverOnce"
        resp: HypiumResponse = self.session._invoke(api, args=["toastShow"])
        return resp.result

    def get(self, timeout: int = 5) -> str:
        """
        Read the latest toast message content from the recent period.

        Args:
            timeout (int): The maximum time to wait for a toast to appear if there are no matching toasts within the given time.

        Returns:
            str: The content of the latest toast message.
        """
        api = "Driver.getRecentUiEvent"
        resp: HypiumResponse = self.session._invoke(api, args=[timeout])
        if resp.result:
            return resp.result.get("text")
        return None