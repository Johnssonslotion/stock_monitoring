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

// Major holidays for 2026 (Simplified for KR/US)
export const HOLIDAYS_2026: string[] = [
    '2026-01-01', // New Year
    '2026-02-17', // Seollal (KR)
    '2026-02-18', // Seollal (KR)
    '2026-02-19', // Seollal (KR)
    '2026-03-01', // Independence Movement Day (KR)
    '2026-05-05', // Children's Day (KR)
    '2026-05-24', // Buddha's Birthday (KR)
    '2026-06-06', // Memorial Day (KR)
    '2026-08-15', // Liberation Day (KR)
    '2026-09-24', // Chuseok (KR)
    '2026-09-25', // Chuseok (KR)
    '2026-09-26', // Chuseok (KR)
    '2026-10-03', // National Foundation Day (KR)
    '2026-10-09', // Hangeul Day (KR)
    '2026-12-25', // Christmas
];

/**
 * Determine if the given market is currently open based on the provided Date (UTC).
 * Returns true if current UTC time falls within the market's open interval.
 * Checks for Weekends and Holidays.
 */
export function isMarketOpen(market: string, now: Date = new Date()): boolean {
    const session = MARKET_SESSIONS.find(s => s.market === market.toLowerCase());
    if (!session) return false;

    // 1. Check Weekend
    // getUTCDay: 0 (Sun) to 6 (Sat).
    // Note: This relies on UTC day. Ideally we should check the LOCAL day of the market.
    // For simplicity, we convert to approximate local date for weekend check.
    const localTime = new Date(now.getTime() + session.timezoneOffset * 60 * 1000);
    const dayOfWeek = localTime.getUTCDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) return false;

    // 2. Check Holidays
    const dateString = localTime.toISOString().split('T')[0];
    if (HOLIDAYS_2026.includes(dateString)) return false;

    // 3. Check Hours
    const localMinutes = localTime.getUTCHours() * 60 + localTime.getUTCMinutes();
    const openMinutes = session.openHour * 60;
    const closeMinutes = session.closeHour * 60;

    return localMinutes >= openMinutes && localMinutes < closeMinutes;
}
