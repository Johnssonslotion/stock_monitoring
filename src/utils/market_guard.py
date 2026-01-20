
import sys
import datetime
import logging
import pytz 

logger = logging.getLogger("MarketGuard")

class MarketAwareGuard:
    """
    Blocks execution during market hours to prevent API key conflicts.
    Protection for Dual-Zone (KR & US).
    Implementation of RFC-006.
    """
    
    # KR Market: 08:30 ~ 16:00 KST (Includes pre/post market)
    KR_START_TIME = datetime.time(8, 30)
    KR_END_TIME = datetime.time(16, 0)
    
    # US Market (ET): 09:20 ~ 16:10 ET (Includes buffers around 09:30~16:00)
    # Using ET allows pytz to handle DST automatically
    US_START_TIME_ET = datetime.time(9, 20)
    US_END_TIME_ET = datetime.time(16, 10)

    @staticmethod
    def check_market_hours(force: bool = False):
        """
        Checks if current time is within KR or US market hours.
        If so, exits the program to protect the Collector singleton key.
        """
        if force:
            logger.warning("Example: FORCING execution during potential market hours! (Override Active)")
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. KR Market Check
        tz_kr = pytz.timezone('Asia/Seoul')
        now_kr = now_utc.astimezone(tz_kr)
        
        if MarketAwareGuard._is_market_open(now_kr, MarketAwareGuard.KR_START_TIME, MarketAwareGuard.KR_END_TIME):
             MarketAwareGuard._block("KR (KST)")

        # 2. US Market Check (Dynamic DST via pytz)
        tz_us = pytz.timezone('America/New_York')
        now_us = now_utc.astimezone(tz_us)
        
        if MarketAwareGuard._is_market_open(now_us, MarketAwareGuard.US_START_TIME_ET, MarketAwareGuard.US_END_TIME_ET):
             MarketAwareGuard._block("US (ET)")

    @staticmethod
    def _is_market_open(now: datetime.datetime, start: datetime.time, end: datetime.time) -> bool:
        # Weekend Check
        if now.weekday() >= 5: # 5=Sat, 6=Sun
            return False
        
        # TODO: Integrate 'holidays' library for precise holiday skipping
        # if now.date() in HOLIDAYS: return False

        t = now.time()
        return start <= t <= end

    @staticmethod
    def _block(market: str):
        msg = (
            f"\n⛔ OPERATION BLOCKED: {market} Market is OPEN!\n"
            f"   The Collector has exclusive lock on the Single API Key.\n"
            f"   Please retry after market close or use --force-emergency if critical.\n"
        )
        print(msg) # Print to stdout for visibility in CLI
        sys.exit(1)

if __name__ == "__main__":
    # CLI Entry Point for Pre-flight Checks
    # Usage: python -m src.utils.market_guard
    logging.basicConfig(level=logging.INFO)
    MarketAwareGuard.check_market_hours()
    print("✅ Market is CLOSED. Operation Safe.")
    sys.exit(0)
