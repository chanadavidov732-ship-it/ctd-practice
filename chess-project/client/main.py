import asyncio
import logging
import threading

from client.network.app_bridge import AppBridge
from client.ui.screen_manager import ScreenManager
from client.ui.screens.login_screen import LoginScreen

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    bridge = AppBridge()
    network_thread = threading.Thread(target=lambda: asyncio.run(bridge.serve()), daemon=True)
    network_thread.start()

    ScreenManager(bridge, LoginScreen).run()


if __name__ == "__main__":
    main()
