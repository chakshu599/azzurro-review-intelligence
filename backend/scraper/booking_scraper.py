from __future__ import annotations
import asyncio
from dataclasses import dataclass

@dataclass
class ScrapeReport:
    property_code:str
    discovered:int=0
    inserted:int=0
    duplicates:int=0
    invalid:int=0
    errors:list[str]|None=None

class BookingReviewScraper:
    """Responsible public-page scraper shell.

    It deliberately performs no requests until Playwright is installed and
    explicitly enabled. Live collection must respect Booking.com terms,
    robots directives, access restrictions and CAPTCHA challenges.
    """
    def __init__(self,enabled:bool=False,timeout_seconds:int=45):
        self.enabled=enabled
        self.timeout_seconds=timeout_seconds

    async def collect(self,property_config):
        if not self.enabled:
            return ScrapeReport(property_config.property_code,errors=["Live collection disabled; no Booking.com request was made."])
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:
            return ScrapeReport(property_config.property_code,errors=[f"Playwright unavailable: {exc}"])
        try:
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True)
                page=await browser.new_page()
                response=await page.goto(property_config.booking_url,timeout=self.timeout_seconds*1000,wait_until="domcontentloaded")
                if not response or response.status>=400:
                    return ScrapeReport(property_config.property_code,errors=[f"Public page returned HTTP {response.status if response else 'no response'}"])
                await browser.close()
                return ScrapeReport(property_config.property_code,errors=["No review parser completed: public HTML structure may differ or access may be restricted."])
        except Exception as exc:
            return ScrapeReport(property_config.property_code,errors=[exc.__class__.__name__+": "+str(exc)])
