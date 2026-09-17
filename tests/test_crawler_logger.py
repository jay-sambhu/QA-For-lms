import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from crawler.crawler import WebsiteCrawler, logger


def test_crawler_logger_defined():
    """Verify logger is properly imported and configured as a Logger instance."""
    assert isinstance(logger, logging.Logger)
    assert logger.name == "crawler.crawler"


def test_crawler_chromium_missing_logs_warning():
    """Verify that when Chromium executable is missing, logger.warning is invoked without NameError."""
    async def _run():
        crawler = WebsiteCrawler("https://example.com")

        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock()
        mock_browser.close = AsyncMock()

        mock_playwright.chromium.launch = AsyncMock(
            side_effect=[
                Exception("Executable doesn't exist at /path/to/chromium"),
                mock_browser,
            ]
        )

        with patch("crawler.crawler.async_playwright") as mock_pw_ctx, \
             patch("crawler.crawler.logger.warning") as mock_warn, \
             patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)) as mock_subproc, \
             patch("crawler.crawler.DeviceConfigManager.get_devices_config", return_value={}):

            mock_pw_ctx.return_value.__aenter__.return_value = mock_playwright

            await crawler.crawl()

            mock_warn.assert_called_once_with(
                "Chromium executable missing. Running automatic playwright installation..."
            )
            mock_subproc.assert_called_once()

    asyncio.run(_run())
