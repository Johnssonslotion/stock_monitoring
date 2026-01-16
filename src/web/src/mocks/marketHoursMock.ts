export type MarketSession = {
    market: string;
    openHour: number; // 24h format local time of market
    closeHour: number; // exclusive
    timezoneOffset: number; // offset from UTC in minutes
};

export const MARKET_SESSIONS: MarketSession[] = [
    // Korean market (KR) - 09:00 to 15:30 KST (UTC+9)
    { market: 'kr', openHour: 9, closeHour: 15.5, timezoneOffset: 9 * 60 },
    // US market (US) - 09:30 to 16:00 EST (UTC-5) (adjust for daylight savings not handled)
    { market: 'us', openHour: 9.5, closeHour: 16, timezoneOffset: -5 * 60 },
];

/**
 * Determine if the given market is currently open based on the provided Date (UTC).
 * Returns true if current UTC time falls within the market's open interval.
 */
export function isMarketOpen(market: string, now: Date = new Date()): boolean {
    const session = MARKET_SESSIONS.find(s => s.market === market.toLowerCase());
    if (!session) return false;
    // Convert now to minutes since UTC midnight
    const utcMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
    // Adjust to market local minutes
    const localMinutes = utcMinutes + session.timezoneOffset;
    const openMinutes = session.openHour * 60;
    const closeMinutes = session.closeHour * 60;
    return localMinutes >= openMinutes && localMinutes < closeMinutes;
}
