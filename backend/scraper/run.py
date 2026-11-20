from __future__ import annotations
import argparse, asyncio, time
from scraper.property_config import get_all_properties,get_property
from scraper.booking_scraper import BookingReviewScraper

def main():
    parser=argparse.ArgumentParser(description="Azzurro Booking.com review collector")
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all",action="store_true")
    group.add_argument("--property",type=str)
    parser.add_argument("--live",action="store_true",help="Explicitly attempt public-page collection")
    args=parser.parse_args()
    configs=get_all_properties() if args.all else ([get_property(args.property)] if get_property(args.property) else [])
    if not configs:
        print("Unknown property code")
        raise SystemExit(2)
    scraper=BookingReviewScraper(enabled=args.live)
    started=time.monotonic(); report=[]
    async def run():
        for cfg in configs:
            r=await scraper.collect(cfg)
            report.append(r)
    asyncio.run(run())
    print("Azzurro Collection Report")
    print(f"Duration: {time.monotonic()-started:.2f}s")
    for r in report:
        print(f"{r.property_code}: discovered={r.discovered} inserted={r.inserted} duplicates={r.duplicates} invalid={r.invalid}")
        for error in r.errors or []: print(f"  error: {error}")

if __name__=="__main__":main()
