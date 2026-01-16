--
-- PostgreSQL database dump
--

\restrict Qq6bj92i4h0XuKrgpTAPRaDjFxMbO1AG3HfbGcCG1aufK1WSrxcPPH52OxQ7s6N

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: calculate_daily_quality(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_daily_quality(target_date date) RETURNS TABLE(total_ticks bigint, symbol_coverage integer, expected_symbols integer, first_tick timestamp with time zone, last_tick timestamp with time zone, market_coverage numeric, status text, gap_hours integer[])
    LANGUAGE plpgsql
    AS $$
DECLARE
    market_start TIMESTAMPTZ := (target_date || ' 09:00:00+09')::TIMESTAMPTZ;
    market_end TIMESTAMPTZ := (target_date || ' 15:30:00+09')::TIMESTAMPTZ;
    total_market_hours DECIMAL := 6.5;
    covered_hours DECIMAL;
    low_volume_hours INT[];
BEGIN
    -- Calculate hourly gaps
    SELECT ARRAY_AGG(EXTRACT(HOUR FROM hour_bucket)::INT)
    INTO low_volume_hours
    FROM (
        SELECT 
            DATE_TRUNC('hour', time AT TIME ZONE 'Asia/Seoul') as hour_bucket,
            COUNT(*) as tick_count
        FROM market_ticks
        WHERE time::date = target_date
        GROUP BY hour_bucket
        HAVING COUNT(*) < 1000
    ) sub;
    
    -- Calculate coverage percentage
    SELECT 
        COUNT(DISTINCT DATE_TRUNC('hour', time AT TIME ZONE 'Asia/Seoul'))::DECIMAL / total_market_hours * 100
    INTO covered_hours
    FROM market_ticks
    WHERE time::date = target_date
      AND time AT TIME ZONE 'Asia/Seoul' BETWEEN market_start AND market_end;
    
    -- Main query
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_ticks,
        COUNT(DISTINCT symbol)::INT as symbol_coverage,
        20::INT as expected_symbols,
        MIN(time) as first_tick,
        MAX(time) as last_tick,
        COALESCE(covered_hours, 0) as market_coverage,
        CASE 
            WHEN COUNT(*) >= 100000 AND COUNT(DISTINCT symbol) = 20 THEN 'PASS'
            WHEN COUNT(*) >= 50000 THEN 'WARN'
            ELSE 'FAIL'
        END as status,
        COALESCE(low_volume_hours, ARRAY[]::INT[]) as gap_hours
    FROM market_ticks
    WHERE time::date = target_date;
END;
$$;


ALTER FUNCTION public.calculate_daily_quality(target_date date) OWNER TO postgres;

--
-- Name: FUNCTION calculate_daily_quality(target_date date); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.calculate_daily_quality(target_date date) IS 'Calculate daily data quality metrics for a given date';


--
-- Name: store_daily_quality(date); Type: PROCEDURE; Schema: public; Owner: postgres
--

CREATE PROCEDURE public.store_daily_quality(IN target_date date)
    LANGUAGE plpgsql
    AS $$
DECLARE
    quality_result RECORD;
    orderbook_cnt BIGINT;
BEGIN
    -- Get quality metrics
    SELECT * INTO quality_result
    FROM calculate_daily_quality(target_date);
    
    -- Get orderbook count
    SELECT COUNT(*) INTO orderbook_cnt
    FROM market_orderbook
    WHERE time::date = target_date;
    
    -- Insert or update
    INSERT INTO data_quality_metrics (
        date,
        total_ticks,
        symbol_coverage,
        expected_symbols,
        first_tick_time,
        last_tick_time,
        market_hours_coverage,
        status,
        gap_hours,
        orderbook_count
    ) VALUES (
        target_date,
        quality_result.total_ticks,
        quality_result.symbol_coverage,
        quality_result.expected_symbols,
        quality_result.first_tick,
        quality_result.last_tick,
        quality_result.market_coverage,
        quality_result.status,
        quality_result.gap_hours,
        orderbook_cnt
    )
    ON CONFLICT (date) DO UPDATE SET
        total_ticks = EXCLUDED.total_ticks,
        symbol_coverage = EXCLUDED.symbol_coverage,
        first_tick_time = EXCLUDED.first_tick_time,
        last_tick_time = EXCLUDED.last_tick_time,
        market_hours_coverage = EXCLUDED.market_hours_coverage,
        status = EXCLUDED.status,
        gap_hours = EXCLUDED.gap_hours,
        orderbook_count = EXCLUDED.orderbook_count,
        created_at = NOW();
    
    RAISE NOTICE 'Quality metrics stored for %: % (% ticks, % symbols)', 
        target_date, quality_result.status, quality_result.total_ticks, quality_result.symbol_coverage;
END;
$$;


ALTER PROCEDURE public.store_daily_quality(IN target_date date) OWNER TO postgres;

--
-- Name: PROCEDURE store_daily_quality(IN target_date date); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON PROCEDURE public.store_daily_quality(IN target_date date) IS 'Store daily quality metrics to data_quality_metrics table';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _compressed_hypertable_7; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._compressed_hypertable_7 (
);


ALTER TABLE _timescaledb_internal._compressed_hypertable_7 OWNER TO postgres;

--
-- Name: market_ticks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.market_ticks (
    "time" timestamp with time zone NOT NULL,
    symbol text NOT NULL,
    price double precision NOT NULL,
    volume double precision NOT NULL,
    change double precision
);


ALTER TABLE public.market_ticks OWNER TO postgres;

--
-- Name: _direct_view_3; Type: VIEW; Schema: _timescaledb_internal; Owner: postgres
--

CREATE VIEW _timescaledb_internal._direct_view_3 AS
 SELECT public.time_bucket('00:01:00'::interval, "time") AS bucket,
    symbol,
    public.first(price, "time") AS open,
    max(price) AS high,
    min(price) AS low,
    public.last(price, "time") AS close,
    sum(volume) AS volume
   FROM public.market_ticks
  GROUP BY (public.time_bucket('00:01:00'::interval, "time")), symbol;


ALTER VIEW _timescaledb_internal._direct_view_3 OWNER TO postgres;

--
-- Name: _direct_view_4; Type: VIEW; Schema: _timescaledb_internal; Owner: postgres
--

CREATE VIEW _timescaledb_internal._direct_view_4 AS
 SELECT public.time_bucket('00:05:00'::interval, "time") AS bucket,
    symbol,
    public.first(price, "time") AS open,
    max(price) AS high,
    min(price) AS low,
    public.last(price, "time") AS close,
    sum(volume) AS volume
   FROM public.market_ticks
  GROUP BY (public.time_bucket('00:05:00'::interval, "time")), symbol;


ALTER VIEW _timescaledb_internal._direct_view_4 OWNER TO postgres;

--
-- Name: _direct_view_5; Type: VIEW; Schema: _timescaledb_internal; Owner: postgres
--

CREATE VIEW _timescaledb_internal._direct_view_5 AS
 SELECT public.time_bucket('00:01:00'::interval, "time") AS bucket,
    symbol,
    public.first(price, "time") AS open,
    max(price) AS high,
    min(price) AS low,
    public.last(price, "time") AS close,
    sum(volume) AS volume
   FROM public.market_ticks
  GROUP BY (public.time_bucket('00:01:00'::interval, "time")), symbol;


ALTER VIEW _timescaledb_internal._direct_view_5 OWNER TO postgres;

--
-- Name: _hyper_1_118_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_1_118_chunk (
    CONSTRAINT constraint_118 CHECK ((("time" >= '2026-01-15 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-22 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_ticks);


ALTER TABLE _timescaledb_internal._hyper_1_118_chunk OWNER TO postgres;

--
-- Name: _hyper_1_1_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_1_1_chunk (
    CONSTRAINT constraint_1 CHECK ((("time" >= '2026-01-01 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-08 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_ticks);


ALTER TABLE _timescaledb_internal._hyper_1_1_chunk OWNER TO postgres;

--
-- Name: _hyper_1_57_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_1_57_chunk (
    CONSTRAINT constraint_57 CHECK ((("time" >= '2026-01-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_ticks);


ALTER TABLE _timescaledb_internal._hyper_1_57_chunk OWNER TO postgres;

--
-- Name: market_candles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.market_candles (
    "time" timestamp with time zone NOT NULL,
    symbol text NOT NULL,
    "interval" text NOT NULL,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE public.market_candles OWNER TO postgres;

--
-- Name: _hyper_2_100_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_100_chunk (
    CONSTRAINT constraint_100 CHECK ((("time" >= '2024-09-26 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-10-03 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_100_chunk OWNER TO postgres;

--
-- Name: _hyper_2_101_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_101_chunk (
    CONSTRAINT constraint_101 CHECK ((("time" >= '2024-10-03 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-10-10 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_101_chunk OWNER TO postgres;

--
-- Name: _hyper_2_102_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_102_chunk (
    CONSTRAINT constraint_102 CHECK ((("time" >= '2024-10-10 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-10-17 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_102_chunk OWNER TO postgres;

--
-- Name: _hyper_2_103_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_103_chunk (
    CONSTRAINT constraint_103 CHECK ((("time" >= '2024-10-17 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-10-24 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_103_chunk OWNER TO postgres;

--
-- Name: _hyper_2_104_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_104_chunk (
    CONSTRAINT constraint_104 CHECK ((("time" >= '2024-10-24 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-10-31 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_104_chunk OWNER TO postgres;

--
-- Name: _hyper_2_105_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_105_chunk (
    CONSTRAINT constraint_105 CHECK ((("time" >= '2024-10-31 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-11-07 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_105_chunk OWNER TO postgres;

--
-- Name: _hyper_2_106_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_106_chunk (
    CONSTRAINT constraint_106 CHECK ((("time" >= '2024-11-07 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-11-14 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_106_chunk OWNER TO postgres;

--
-- Name: _hyper_2_107_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_107_chunk (
    CONSTRAINT constraint_107 CHECK ((("time" >= '2024-11-14 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-11-21 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_107_chunk OWNER TO postgres;

--
-- Name: _hyper_2_108_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_108_chunk (
    CONSTRAINT constraint_108 CHECK ((("time" >= '2024-11-21 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-11-28 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_108_chunk OWNER TO postgres;

--
-- Name: _hyper_2_109_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_109_chunk (
    CONSTRAINT constraint_109 CHECK ((("time" >= '2024-11-28 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-12-05 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_109_chunk OWNER TO postgres;

--
-- Name: _hyper_2_10_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_10_chunk (
    CONSTRAINT constraint_10 CHECK ((("time" >= '2025-02-27 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-03-06 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_10_chunk OWNER TO postgres;

--
-- Name: _hyper_2_110_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_110_chunk (
    CONSTRAINT constraint_110 CHECK ((("time" >= '2024-12-05 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-12-12 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_110_chunk OWNER TO postgres;

--
-- Name: _hyper_2_111_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_111_chunk (
    CONSTRAINT constraint_111 CHECK ((("time" >= '2024-12-12 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-12-19 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_111_chunk OWNER TO postgres;

--
-- Name: _hyper_2_112_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_112_chunk (
    CONSTRAINT constraint_112 CHECK ((("time" >= '2024-12-19 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-12-26 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_112_chunk OWNER TO postgres;

--
-- Name: _hyper_2_113_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_113_chunk (
    CONSTRAINT constraint_113 CHECK ((("time" >= '2024-12-26 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-01-02 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_113_chunk OWNER TO postgres;

--
-- Name: _hyper_2_114_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_114_chunk (
    CONSTRAINT constraint_114 CHECK ((("time" >= '2023-12-28 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-01-04 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_114_chunk OWNER TO postgres;

--
-- Name: _hyper_2_115_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_115_chunk (
    CONSTRAINT constraint_115 CHECK ((("time" >= '2024-01-04 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-01-11 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_115_chunk OWNER TO postgres;

--
-- Name: _hyper_2_11_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_11_chunk (
    CONSTRAINT constraint_11 CHECK ((("time" >= '2025-03-06 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-03-13 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_11_chunk OWNER TO postgres;

--
-- Name: _hyper_2_12_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_12_chunk (
    CONSTRAINT constraint_12 CHECK ((("time" >= '2025-03-13 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-03-20 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_12_chunk OWNER TO postgres;

--
-- Name: _hyper_2_13_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_13_chunk (
    CONSTRAINT constraint_13 CHECK ((("time" >= '2025-03-20 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-03-27 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_13_chunk OWNER TO postgres;

--
-- Name: _hyper_2_14_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_14_chunk (
    CONSTRAINT constraint_14 CHECK ((("time" >= '2025-03-27 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-04-03 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_14_chunk OWNER TO postgres;

--
-- Name: _hyper_2_15_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_15_chunk (
    CONSTRAINT constraint_15 CHECK ((("time" >= '2025-04-03 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-04-10 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_15_chunk OWNER TO postgres;

--
-- Name: _hyper_2_16_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_16_chunk (
    CONSTRAINT constraint_16 CHECK ((("time" >= '2025-04-10 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-04-17 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_16_chunk OWNER TO postgres;

--
-- Name: _hyper_2_17_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_17_chunk (
    CONSTRAINT constraint_17 CHECK ((("time" >= '2025-04-17 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-04-24 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_17_chunk OWNER TO postgres;

--
-- Name: _hyper_2_18_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_18_chunk (
    CONSTRAINT constraint_18 CHECK ((("time" >= '2025-04-24 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-05-01 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_18_chunk OWNER TO postgres;

--
-- Name: _hyper_2_19_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_19_chunk (
    CONSTRAINT constraint_19 CHECK ((("time" >= '2025-05-01 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-05-08 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_19_chunk OWNER TO postgres;

--
-- Name: _hyper_2_20_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_20_chunk (
    CONSTRAINT constraint_20 CHECK ((("time" >= '2025-05-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-05-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_20_chunk OWNER TO postgres;

--
-- Name: _hyper_2_21_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_21_chunk (
    CONSTRAINT constraint_21 CHECK ((("time" >= '2025-05-15 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-05-22 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_21_chunk OWNER TO postgres;

--
-- Name: _hyper_2_22_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_22_chunk (
    CONSTRAINT constraint_22 CHECK ((("time" >= '2025-05-22 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-05-29 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_22_chunk OWNER TO postgres;

--
-- Name: _hyper_2_23_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_23_chunk (
    CONSTRAINT constraint_23 CHECK ((("time" >= '2025-05-29 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-06-05 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_23_chunk OWNER TO postgres;

--
-- Name: _hyper_2_24_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_24_chunk (
    CONSTRAINT constraint_24 CHECK ((("time" >= '2025-06-05 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-06-12 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_24_chunk OWNER TO postgres;

--
-- Name: _hyper_2_25_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_25_chunk (
    CONSTRAINT constraint_25 CHECK ((("time" >= '2025-06-12 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-06-19 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_25_chunk OWNER TO postgres;

--
-- Name: _hyper_2_26_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_26_chunk (
    CONSTRAINT constraint_26 CHECK ((("time" >= '2025-06-19 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-06-26 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_26_chunk OWNER TO postgres;

--
-- Name: _hyper_2_27_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_27_chunk (
    CONSTRAINT constraint_27 CHECK ((("time" >= '2025-06-26 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-07-03 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_27_chunk OWNER TO postgres;

--
-- Name: _hyper_2_28_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_28_chunk (
    CONSTRAINT constraint_28 CHECK ((("time" >= '2025-07-03 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-07-10 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_28_chunk OWNER TO postgres;

--
-- Name: _hyper_2_29_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_29_chunk (
    CONSTRAINT constraint_29 CHECK ((("time" >= '2025-07-10 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-07-17 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_29_chunk OWNER TO postgres;

--
-- Name: _hyper_2_2_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_2_chunk (
    CONSTRAINT constraint_2 CHECK ((("time" >= '2025-01-02 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-01-09 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_2_chunk OWNER TO postgres;

--
-- Name: _hyper_2_30_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_30_chunk (
    CONSTRAINT constraint_30 CHECK ((("time" >= '2025-07-17 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-07-24 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_30_chunk OWNER TO postgres;

--
-- Name: _hyper_2_31_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_31_chunk (
    CONSTRAINT constraint_31 CHECK ((("time" >= '2025-07-24 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-07-31 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_31_chunk OWNER TO postgres;

--
-- Name: _hyper_2_32_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_32_chunk (
    CONSTRAINT constraint_32 CHECK ((("time" >= '2025-07-31 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-08-07 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_32_chunk OWNER TO postgres;

--
-- Name: _hyper_2_33_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_33_chunk (
    CONSTRAINT constraint_33 CHECK ((("time" >= '2025-08-07 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-08-14 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_33_chunk OWNER TO postgres;

--
-- Name: _hyper_2_34_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_34_chunk (
    CONSTRAINT constraint_34 CHECK ((("time" >= '2025-08-14 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-08-21 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_34_chunk OWNER TO postgres;

--
-- Name: _hyper_2_35_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_35_chunk (
    CONSTRAINT constraint_35 CHECK ((("time" >= '2025-08-21 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-08-28 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_35_chunk OWNER TO postgres;

--
-- Name: _hyper_2_36_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_36_chunk (
    CONSTRAINT constraint_36 CHECK ((("time" >= '2025-08-28 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-09-04 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_36_chunk OWNER TO postgres;

--
-- Name: _hyper_2_37_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_37_chunk (
    CONSTRAINT constraint_37 CHECK ((("time" >= '2025-09-04 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-09-11 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_37_chunk OWNER TO postgres;

--
-- Name: _hyper_2_38_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_38_chunk (
    CONSTRAINT constraint_38 CHECK ((("time" >= '2025-09-11 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-09-18 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_38_chunk OWNER TO postgres;

--
-- Name: _hyper_2_39_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_39_chunk (
    CONSTRAINT constraint_39 CHECK ((("time" >= '2025-09-18 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-09-25 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_39_chunk OWNER TO postgres;

--
-- Name: _hyper_2_3_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_3_chunk (
    CONSTRAINT constraint_3 CHECK ((("time" >= '2025-01-09 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-01-16 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_3_chunk OWNER TO postgres;

--
-- Name: _hyper_2_40_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_40_chunk (
    CONSTRAINT constraint_40 CHECK ((("time" >= '2025-09-25 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-10-02 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_40_chunk OWNER TO postgres;

--
-- Name: _hyper_2_41_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_41_chunk (
    CONSTRAINT constraint_41 CHECK ((("time" >= '2025-10-02 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-10-09 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_41_chunk OWNER TO postgres;

--
-- Name: _hyper_2_42_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_42_chunk (
    CONSTRAINT constraint_42 CHECK ((("time" >= '2025-10-09 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-10-16 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_42_chunk OWNER TO postgres;

--
-- Name: _hyper_2_43_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_43_chunk (
    CONSTRAINT constraint_43 CHECK ((("time" >= '2025-10-16 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-10-23 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_43_chunk OWNER TO postgres;

--
-- Name: _hyper_2_44_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_44_chunk (
    CONSTRAINT constraint_44 CHECK ((("time" >= '2025-10-23 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-10-30 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_44_chunk OWNER TO postgres;

--
-- Name: _hyper_2_45_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_45_chunk (
    CONSTRAINT constraint_45 CHECK ((("time" >= '2025-10-30 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-11-06 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_45_chunk OWNER TO postgres;

--
-- Name: _hyper_2_46_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_46_chunk (
    CONSTRAINT constraint_46 CHECK ((("time" >= '2025-11-06 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-11-13 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_46_chunk OWNER TO postgres;

--
-- Name: _hyper_2_47_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_47_chunk (
    CONSTRAINT constraint_47 CHECK ((("time" >= '2025-11-13 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-11-20 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_47_chunk OWNER TO postgres;

--
-- Name: _hyper_2_48_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_48_chunk (
    CONSTRAINT constraint_48 CHECK ((("time" >= '2025-11-20 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-11-27 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_48_chunk OWNER TO postgres;

--
-- Name: _hyper_2_49_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_49_chunk (
    CONSTRAINT constraint_49 CHECK ((("time" >= '2025-11-27 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-12-04 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_49_chunk OWNER TO postgres;

--
-- Name: _hyper_2_4_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_4_chunk (
    CONSTRAINT constraint_4 CHECK ((("time" >= '2025-01-16 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-01-23 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_4_chunk OWNER TO postgres;

--
-- Name: _hyper_2_50_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_50_chunk (
    CONSTRAINT constraint_50 CHECK ((("time" >= '2025-12-04 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-12-11 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_50_chunk OWNER TO postgres;

--
-- Name: _hyper_2_51_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_51_chunk (
    CONSTRAINT constraint_51 CHECK ((("time" >= '2025-12-11 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-12-18 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_51_chunk OWNER TO postgres;

--
-- Name: _hyper_2_52_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_52_chunk (
    CONSTRAINT constraint_52 CHECK ((("time" >= '2025-12-18 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-12-25 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_52_chunk OWNER TO postgres;

--
-- Name: _hyper_2_53_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_53_chunk (
    CONSTRAINT constraint_53 CHECK ((("time" >= '2025-12-25 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-01 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_53_chunk OWNER TO postgres;

--
-- Name: _hyper_2_54_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_54_chunk (
    CONSTRAINT constraint_54 CHECK ((("time" >= '2026-01-01 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-08 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_54_chunk OWNER TO postgres;

--
-- Name: _hyper_2_5_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_5_chunk (
    CONSTRAINT constraint_5 CHECK ((("time" >= '2025-01-23 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-01-30 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_5_chunk OWNER TO postgres;

--
-- Name: _hyper_2_62_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_62_chunk (
    CONSTRAINT constraint_62 CHECK ((("time" >= '2026-01-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_62_chunk OWNER TO postgres;

--
-- Name: _hyper_2_63_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_63_chunk (
    CONSTRAINT constraint_63 CHECK ((("time" >= '2024-01-11 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-01-18 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_63_chunk OWNER TO postgres;

--
-- Name: _hyper_2_64_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_64_chunk (
    CONSTRAINT constraint_64 CHECK ((("time" >= '2024-01-18 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-01-25 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_64_chunk OWNER TO postgres;

--
-- Name: _hyper_2_65_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_65_chunk (
    CONSTRAINT constraint_65 CHECK ((("time" >= '2024-01-25 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-02-01 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_65_chunk OWNER TO postgres;

--
-- Name: _hyper_2_66_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_66_chunk (
    CONSTRAINT constraint_66 CHECK ((("time" >= '2024-02-01 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-02-08 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_66_chunk OWNER TO postgres;

--
-- Name: _hyper_2_67_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_67_chunk (
    CONSTRAINT constraint_67 CHECK ((("time" >= '2024-02-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-02-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_67_chunk OWNER TO postgres;

--
-- Name: _hyper_2_68_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_68_chunk (
    CONSTRAINT constraint_68 CHECK ((("time" >= '2024-02-15 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-02-22 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_68_chunk OWNER TO postgres;

--
-- Name: _hyper_2_69_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_69_chunk (
    CONSTRAINT constraint_69 CHECK ((("time" >= '2024-02-22 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-02-29 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_69_chunk OWNER TO postgres;

--
-- Name: _hyper_2_6_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_6_chunk (
    CONSTRAINT constraint_6 CHECK ((("time" >= '2025-01-30 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-02-06 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_6_chunk OWNER TO postgres;

--
-- Name: _hyper_2_70_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_70_chunk (
    CONSTRAINT constraint_70 CHECK ((("time" >= '2024-02-29 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-03-07 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_70_chunk OWNER TO postgres;

--
-- Name: _hyper_2_71_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_71_chunk (
    CONSTRAINT constraint_71 CHECK ((("time" >= '2024-03-07 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-03-14 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_71_chunk OWNER TO postgres;

--
-- Name: _hyper_2_72_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_72_chunk (
    CONSTRAINT constraint_72 CHECK ((("time" >= '2024-03-14 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-03-21 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_72_chunk OWNER TO postgres;

--
-- Name: _hyper_2_73_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_73_chunk (
    CONSTRAINT constraint_73 CHECK ((("time" >= '2024-03-21 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-03-28 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_73_chunk OWNER TO postgres;

--
-- Name: _hyper_2_74_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_74_chunk (
    CONSTRAINT constraint_74 CHECK ((("time" >= '2024-03-28 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-04-04 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_74_chunk OWNER TO postgres;

--
-- Name: _hyper_2_75_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_75_chunk (
    CONSTRAINT constraint_75 CHECK ((("time" >= '2024-04-04 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-04-11 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_75_chunk OWNER TO postgres;

--
-- Name: _hyper_2_76_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_76_chunk (
    CONSTRAINT constraint_76 CHECK ((("time" >= '2024-04-11 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-04-18 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_76_chunk OWNER TO postgres;

--
-- Name: _hyper_2_77_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_77_chunk (
    CONSTRAINT constraint_77 CHECK ((("time" >= '2024-04-18 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-04-25 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_77_chunk OWNER TO postgres;

--
-- Name: _hyper_2_78_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_78_chunk (
    CONSTRAINT constraint_78 CHECK ((("time" >= '2024-04-25 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-05-02 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_78_chunk OWNER TO postgres;

--
-- Name: _hyper_2_79_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_79_chunk (
    CONSTRAINT constraint_79 CHECK ((("time" >= '2024-05-02 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-05-09 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_79_chunk OWNER TO postgres;

--
-- Name: _hyper_2_7_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_7_chunk (
    CONSTRAINT constraint_7 CHECK ((("time" >= '2025-02-06 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-02-13 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_7_chunk OWNER TO postgres;

--
-- Name: _hyper_2_80_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_80_chunk (
    CONSTRAINT constraint_80 CHECK ((("time" >= '2024-05-09 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-05-16 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_80_chunk OWNER TO postgres;

--
-- Name: _hyper_2_81_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_81_chunk (
    CONSTRAINT constraint_81 CHECK ((("time" >= '2024-05-16 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-05-23 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_81_chunk OWNER TO postgres;

--
-- Name: _hyper_2_82_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_82_chunk (
    CONSTRAINT constraint_82 CHECK ((("time" >= '2024-05-23 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-05-30 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_82_chunk OWNER TO postgres;

--
-- Name: _hyper_2_83_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_83_chunk (
    CONSTRAINT constraint_83 CHECK ((("time" >= '2024-05-30 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-06-06 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_83_chunk OWNER TO postgres;

--
-- Name: _hyper_2_84_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_84_chunk (
    CONSTRAINT constraint_84 CHECK ((("time" >= '2024-06-06 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-06-13 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_84_chunk OWNER TO postgres;

--
-- Name: _hyper_2_85_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_85_chunk (
    CONSTRAINT constraint_85 CHECK ((("time" >= '2024-06-13 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-06-20 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_85_chunk OWNER TO postgres;

--
-- Name: _hyper_2_86_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_86_chunk (
    CONSTRAINT constraint_86 CHECK ((("time" >= '2024-06-20 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-06-27 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_86_chunk OWNER TO postgres;

--
-- Name: _hyper_2_87_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_87_chunk (
    CONSTRAINT constraint_87 CHECK ((("time" >= '2024-06-27 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-07-04 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_87_chunk OWNER TO postgres;

--
-- Name: _hyper_2_88_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_88_chunk (
    CONSTRAINT constraint_88 CHECK ((("time" >= '2024-07-04 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-07-11 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_88_chunk OWNER TO postgres;

--
-- Name: _hyper_2_89_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_89_chunk (
    CONSTRAINT constraint_89 CHECK ((("time" >= '2024-07-11 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-07-18 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_89_chunk OWNER TO postgres;

--
-- Name: _hyper_2_8_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_8_chunk (
    CONSTRAINT constraint_8 CHECK ((("time" >= '2025-02-13 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-02-20 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_8_chunk OWNER TO postgres;

--
-- Name: _hyper_2_90_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_90_chunk (
    CONSTRAINT constraint_90 CHECK ((("time" >= '2024-07-18 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-07-25 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_90_chunk OWNER TO postgres;

--
-- Name: _hyper_2_91_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_91_chunk (
    CONSTRAINT constraint_91 CHECK ((("time" >= '2024-07-25 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-08-01 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_91_chunk OWNER TO postgres;

--
-- Name: _hyper_2_92_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_92_chunk (
    CONSTRAINT constraint_92 CHECK ((("time" >= '2024-08-01 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-08-08 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_92_chunk OWNER TO postgres;

--
-- Name: _hyper_2_93_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_93_chunk (
    CONSTRAINT constraint_93 CHECK ((("time" >= '2024-08-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-08-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_93_chunk OWNER TO postgres;

--
-- Name: _hyper_2_94_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_94_chunk (
    CONSTRAINT constraint_94 CHECK ((("time" >= '2024-08-15 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-08-22 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_94_chunk OWNER TO postgres;

--
-- Name: _hyper_2_95_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_95_chunk (
    CONSTRAINT constraint_95 CHECK ((("time" >= '2024-08-22 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-08-29 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_95_chunk OWNER TO postgres;

--
-- Name: _hyper_2_96_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_96_chunk (
    CONSTRAINT constraint_96 CHECK ((("time" >= '2024-08-29 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-09-05 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_96_chunk OWNER TO postgres;

--
-- Name: _hyper_2_97_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_97_chunk (
    CONSTRAINT constraint_97 CHECK ((("time" >= '2024-09-05 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-09-12 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_97_chunk OWNER TO postgres;

--
-- Name: _hyper_2_98_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_98_chunk (
    CONSTRAINT constraint_98 CHECK ((("time" >= '2024-09-12 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-09-19 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_98_chunk OWNER TO postgres;

--
-- Name: _hyper_2_99_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_99_chunk (
    CONSTRAINT constraint_99 CHECK ((("time" >= '2024-09-19 00:00:00+00'::timestamp with time zone) AND ("time" < '2024-09-26 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_99_chunk OWNER TO postgres;

--
-- Name: _hyper_2_9_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_2_9_chunk (
    CONSTRAINT constraint_9 CHECK ((("time" >= '2025-02-20 00:00:00+00'::timestamp with time zone) AND ("time" < '2025-02-27 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_candles);


ALTER TABLE _timescaledb_internal._hyper_2_9_chunk OWNER TO postgres;

--
-- Name: _materialized_hypertable_3; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_3 (
    bucket timestamp with time zone NOT NULL,
    symbol text,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE _timescaledb_internal._materialized_hypertable_3 OWNER TO postgres;

--
-- Name: _hyper_3_55_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_3_55_chunk (
    CONSTRAINT constraint_55 CHECK (((bucket >= '2025-12-18 00:00:00+00'::timestamp with time zone) AND (bucket < '2026-02-26 00:00:00+00'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_3);


ALTER TABLE _timescaledb_internal._hyper_3_55_chunk OWNER TO postgres;

--
-- Name: _materialized_hypertable_4; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_4 (
    bucket timestamp with time zone NOT NULL,
    symbol text,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE _timescaledb_internal._materialized_hypertable_4 OWNER TO postgres;

--
-- Name: _hyper_4_56_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_4_56_chunk (
    CONSTRAINT constraint_56 CHECK (((bucket >= '2025-12-18 00:00:00+00'::timestamp with time zone) AND (bucket < '2026-02-26 00:00:00+00'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_4);


ALTER TABLE _timescaledb_internal._hyper_4_56_chunk OWNER TO postgres;

--
-- Name: _materialized_hypertable_5; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_5 (
    bucket timestamp with time zone NOT NULL,
    symbol text,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE _timescaledb_internal._materialized_hypertable_5 OWNER TO postgres;

--
-- Name: _hyper_5_58_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_5_58_chunk (
    CONSTRAINT constraint_58 CHECK (((bucket >= '2025-12-18 00:00:00+00'::timestamp with time zone) AND (bucket < '2026-02-26 00:00:00+00'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_5);


ALTER TABLE _timescaledb_internal._hyper_5_58_chunk OWNER TO postgres;

--
-- Name: market_orderbook; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.market_orderbook (
    "time" timestamp with time zone NOT NULL,
    symbol text NOT NULL,
    ask_price1 double precision,
    ask_vol1 double precision,
    ask_price2 double precision,
    ask_vol2 double precision,
    ask_price3 double precision,
    ask_vol3 double precision,
    ask_price4 double precision,
    ask_vol4 double precision,
    ask_price5 double precision,
    ask_vol5 double precision,
    bid_price1 double precision,
    bid_vol1 double precision,
    bid_price2 double precision,
    bid_vol2 double precision,
    bid_price3 double precision,
    bid_vol3 double precision,
    bid_price4 double precision,
    bid_vol4 double precision,
    bid_price5 double precision,
    bid_vol5 double precision
);


ALTER TABLE public.market_orderbook OWNER TO postgres;

--
-- Name: _hyper_6_119_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_6_119_chunk (
    CONSTRAINT constraint_119 CHECK ((("time" >= '2026-01-15 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-22 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_orderbook);


ALTER TABLE _timescaledb_internal._hyper_6_119_chunk OWNER TO postgres;

--
-- Name: _hyper_6_59_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_6_59_chunk (
    CONSTRAINT constraint_59 CHECK ((("time" >= '2026-01-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_orderbook);


ALTER TABLE _timescaledb_internal._hyper_6_59_chunk OWNER TO postgres;

--
-- Name: market_minutes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.market_minutes (
    "time" timestamp with time zone NOT NULL,
    symbol text NOT NULL,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE public.market_minutes OWNER TO postgres;

--
-- Name: _hyper_8_60_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_8_60_chunk (
    CONSTRAINT constraint_60 CHECK ((("time" >= '2026-01-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_minutes);


ALTER TABLE _timescaledb_internal._hyper_8_60_chunk OWNER TO postgres;

--
-- Name: _hyper_8_61_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_8_61_chunk (
    CONSTRAINT constraint_61 CHECK ((("time" >= '2026-01-01 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-08 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.market_minutes);


ALTER TABLE _timescaledb_internal._hyper_8_61_chunk OWNER TO postgres;

--
-- Name: system_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.system_metrics (
    "time" timestamp with time zone NOT NULL,
    type text NOT NULL,
    value double precision NOT NULL,
    meta jsonb
);


ALTER TABLE public.system_metrics OWNER TO postgres;

--
-- Name: _hyper_9_116_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_9_116_chunk (
    CONSTRAINT constraint_116 CHECK ((("time" >= '2026-01-08 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-15 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.system_metrics);


ALTER TABLE _timescaledb_internal._hyper_9_116_chunk OWNER TO postgres;

--
-- Name: _hyper_9_117_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: postgres
--

CREATE TABLE _timescaledb_internal._hyper_9_117_chunk (
    CONSTRAINT constraint_117 CHECK ((("time" >= '2026-01-15 00:00:00+00'::timestamp with time zone) AND ("time" < '2026-01-22 00:00:00+00'::timestamp with time zone)))
)
INHERITS (public.system_metrics);


ALTER TABLE _timescaledb_internal._hyper_9_117_chunk OWNER TO postgres;

--
-- Name: _partial_view_3; Type: VIEW; Schema: _timescaledb_internal; Owner: postgres
--

CREATE VIEW _timescaledb_internal._partial_view_3 AS
 SELECT public.time_bucket('00:01:00'::interval, "time") AS bucket,
    symbol,
    public.first(price, "time") AS open,
    max(price) AS high,
    min(price) AS low,
    public.last(price, "time") AS close,
    sum(volume) AS volume
   FROM public.market_ticks
  GROUP BY (public.time_bucket('00:01:00'::interval, "time")), symbol;


ALTER VIEW _timescaledb_internal._partial_view_3 OWNER TO postgres;

--
-- Name: _partial_view_4; Type: VIEW; Schema: _timescaledb_internal; Owner: postgres
--

CREATE VIEW _timescaledb_internal._partial_view_4 AS
 SELECT public.time_bucket('00:05:00'::interval, "time") AS bucket,
    symbol,
    public.first(price, "time") AS open,
    max(price) AS high,
    min(price) AS low,
    public.last(price, "time") AS close,
    sum(volume) AS volume
   FROM public.market_ticks
  GROUP BY (public.time_bucket('00:05:00'::interval, "time")), symbol;


ALTER VIEW _timescaledb_internal._partial_view_4 OWNER TO postgres;

--
-- Name: _partial_view_5; Type: VIEW; Schema: _timescaledb_internal; Owner: postgres
--

CREATE VIEW _timescaledb_internal._partial_view_5 AS
 SELECT public.time_bucket('00:01:00'::interval, "time") AS bucket,
    symbol,
    public.first(price, "time") AS open,
    max(price) AS high,
    min(price) AS low,
    public.last(price, "time") AS close,
    sum(volume) AS volume
   FROM public.market_ticks
  GROUP BY (public.time_bucket('00:01:00'::interval, "time")), symbol;


ALTER VIEW _timescaledb_internal._partial_view_5 OWNER TO postgres;

--
-- Name: candle_1m; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.candle_1m AS
 SELECT bucket,
    symbol,
    open,
    high,
    low,
    close,
    volume
   FROM _timescaledb_internal._materialized_hypertable_5;


ALTER VIEW public.candle_1m OWNER TO postgres;

--
-- Name: candles_15m; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.candles_15m AS
 SELECT "time" AS bucket,
    open,
    high,
    low,
    close,
    volume,
    symbol
   FROM public.market_candles
  WHERE ("interval" = '15m'::text);


ALTER VIEW public.candles_15m OWNER TO postgres;

--
-- Name: candles_1d; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.candles_1d AS
 SELECT "time" AS bucket,
    open,
    high,
    low,
    close,
    volume,
    symbol
   FROM public.market_candles
  WHERE ("interval" = '1d'::text);


ALTER VIEW public.candles_1d OWNER TO postgres;

--
-- Name: candles_1h; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.candles_1h AS
 SELECT "time" AS bucket,
    open,
    high,
    low,
    close,
    volume,
    symbol
   FROM public.market_candles
  WHERE ("interval" = '1h'::text);


ALTER VIEW public.candles_1h OWNER TO postgres;

--
-- Name: candles_1m; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.candles_1m AS
 SELECT bucket,
    symbol,
    open,
    high,
    low,
    close,
    volume
   FROM _timescaledb_internal._materialized_hypertable_3;


ALTER VIEW public.candles_1m OWNER TO postgres;

--
-- Name: candles_5m; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.candles_5m AS
 SELECT bucket,
    symbol,
    open,
    high,
    low,
    close,
    volume
   FROM _timescaledb_internal._materialized_hypertable_4;


ALTER VIEW public.candles_5m OWNER TO postgres;

--
-- Name: data_quality_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.data_quality_metrics (
    date date NOT NULL,
    total_ticks bigint NOT NULL,
    symbol_coverage integer NOT NULL,
    expected_symbols integer DEFAULT 20 NOT NULL,
    first_tick_time timestamp with time zone,
    last_tick_time timestamp with time zone,
    market_hours_coverage numeric(5,2),
    status character varying(10),
    gap_hours integer[],
    orderbook_count bigint DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT data_quality_metrics_status_check CHECK (((status)::text = ANY ((ARRAY['PASS'::character varying, 'WARN'::character varying, 'FAIL'::character varying])::text[])))
);


ALTER TABLE public.data_quality_metrics OWNER TO postgres;

--
-- Name: TABLE data_quality_metrics; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.data_quality_metrics IS 'Daily data quality validation results';


--
-- Name: COLUMN data_quality_metrics.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.data_quality_metrics.status IS 'PASS: >100K ticks, WARN: 50K-100K, FAIL: <50K';


--
-- Name: symbol_metadata; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.symbol_metadata (
    symbol character varying(20) NOT NULL,
    market_cap bigint,
    sector character varying(50),
    is_kospi200 boolean,
    is_halted boolean DEFAULT false,
    is_managed boolean DEFAULT false,
    is_delisting boolean DEFAULT false,
    per double precision,
    dividend_yield double precision,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.symbol_metadata OWNER TO postgres;

--
-- Name: _hyper_2_100_chunk 100_95_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_100_chunk
    ADD CONSTRAINT "100_95_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_101_chunk 101_96_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_101_chunk
    ADD CONSTRAINT "101_96_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_102_chunk 102_97_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_102_chunk
    ADD CONSTRAINT "102_97_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_103_chunk 103_98_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_103_chunk
    ADD CONSTRAINT "103_98_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_104_chunk 104_99_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_104_chunk
    ADD CONSTRAINT "104_99_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_105_chunk 105_100_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_105_chunk
    ADD CONSTRAINT "105_100_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_106_chunk 106_101_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_106_chunk
    ADD CONSTRAINT "106_101_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_107_chunk 107_102_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_107_chunk
    ADD CONSTRAINT "107_102_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_108_chunk 108_103_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_108_chunk
    ADD CONSTRAINT "108_103_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_109_chunk 109_104_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_109_chunk
    ADD CONSTRAINT "109_104_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_10_chunk 10_12_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_10_chunk
    ADD CONSTRAINT "10_12_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_110_chunk 110_105_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_110_chunk
    ADD CONSTRAINT "110_105_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_111_chunk 111_106_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_111_chunk
    ADD CONSTRAINT "111_106_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_112_chunk 112_107_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_112_chunk
    ADD CONSTRAINT "112_107_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_113_chunk 113_108_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_113_chunk
    ADD CONSTRAINT "113_108_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_114_chunk 114_109_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_114_chunk
    ADD CONSTRAINT "114_109_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_115_chunk 115_110_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_115_chunk
    ADD CONSTRAINT "115_110_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_11_chunk 11_13_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_11_chunk
    ADD CONSTRAINT "11_13_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_12_chunk 12_14_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_12_chunk
    ADD CONSTRAINT "12_14_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_13_chunk 13_15_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_13_chunk
    ADD CONSTRAINT "13_15_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_14_chunk 14_16_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_14_chunk
    ADD CONSTRAINT "14_16_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_15_chunk 15_17_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_15_chunk
    ADD CONSTRAINT "15_17_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_16_chunk 16_18_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_16_chunk
    ADD CONSTRAINT "16_18_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_17_chunk 17_19_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_17_chunk
    ADD CONSTRAINT "17_19_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_18_chunk 18_20_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_18_chunk
    ADD CONSTRAINT "18_20_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_19_chunk 19_21_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_19_chunk
    ADD CONSTRAINT "19_21_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_20_chunk 20_22_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_20_chunk
    ADD CONSTRAINT "20_22_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_21_chunk 21_23_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_21_chunk
    ADD CONSTRAINT "21_23_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_22_chunk 22_24_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_22_chunk
    ADD CONSTRAINT "22_24_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_23_chunk 23_25_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_23_chunk
    ADD CONSTRAINT "23_25_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_24_chunk 24_26_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_24_chunk
    ADD CONSTRAINT "24_26_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_25_chunk 25_27_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_25_chunk
    ADD CONSTRAINT "25_27_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_26_chunk 26_28_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_26_chunk
    ADD CONSTRAINT "26_28_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_27_chunk 27_29_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_27_chunk
    ADD CONSTRAINT "27_29_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_28_chunk 28_30_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_28_chunk
    ADD CONSTRAINT "28_30_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_29_chunk 29_31_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_29_chunk
    ADD CONSTRAINT "29_31_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_2_chunk 2_4_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_2_chunk
    ADD CONSTRAINT "2_4_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_30_chunk 30_32_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_30_chunk
    ADD CONSTRAINT "30_32_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_31_chunk 31_33_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_31_chunk
    ADD CONSTRAINT "31_33_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_32_chunk 32_34_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_32_chunk
    ADD CONSTRAINT "32_34_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_33_chunk 33_35_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_33_chunk
    ADD CONSTRAINT "33_35_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_34_chunk 34_36_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_34_chunk
    ADD CONSTRAINT "34_36_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_35_chunk 35_37_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_35_chunk
    ADD CONSTRAINT "35_37_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_36_chunk 36_38_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_36_chunk
    ADD CONSTRAINT "36_38_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_37_chunk 37_39_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_37_chunk
    ADD CONSTRAINT "37_39_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_38_chunk 38_40_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_38_chunk
    ADD CONSTRAINT "38_40_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_39_chunk 39_41_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_39_chunk
    ADD CONSTRAINT "39_41_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_3_chunk 3_5_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_3_chunk
    ADD CONSTRAINT "3_5_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_40_chunk 40_42_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_40_chunk
    ADD CONSTRAINT "40_42_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_41_chunk 41_43_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_41_chunk
    ADD CONSTRAINT "41_43_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_42_chunk 42_44_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_42_chunk
    ADD CONSTRAINT "42_44_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_43_chunk 43_45_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_43_chunk
    ADD CONSTRAINT "43_45_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_44_chunk 44_46_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_44_chunk
    ADD CONSTRAINT "44_46_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_45_chunk 45_47_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_45_chunk
    ADD CONSTRAINT "45_47_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_46_chunk 46_48_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_46_chunk
    ADD CONSTRAINT "46_48_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_47_chunk 47_49_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_47_chunk
    ADD CONSTRAINT "47_49_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_48_chunk 48_50_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_48_chunk
    ADD CONSTRAINT "48_50_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_49_chunk 49_51_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_49_chunk
    ADD CONSTRAINT "49_51_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_4_chunk 4_6_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_4_chunk
    ADD CONSTRAINT "4_6_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_50_chunk 50_52_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_50_chunk
    ADD CONSTRAINT "50_52_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_51_chunk 51_53_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_51_chunk
    ADD CONSTRAINT "51_53_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_52_chunk 52_54_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_52_chunk
    ADD CONSTRAINT "52_54_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_53_chunk 53_55_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_53_chunk
    ADD CONSTRAINT "53_55_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_54_chunk 54_56_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_54_chunk
    ADD CONSTRAINT "54_56_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_5_chunk 5_7_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_5_chunk
    ADD CONSTRAINT "5_7_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_8_60_chunk 60_1_market_minutes_time_symbol_key; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_8_60_chunk
    ADD CONSTRAINT "60_1_market_minutes_time_symbol_key" UNIQUE ("time", symbol);


--
-- Name: _hyper_8_61_chunk 61_2_market_minutes_time_symbol_key; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_8_61_chunk
    ADD CONSTRAINT "61_2_market_minutes_time_symbol_key" UNIQUE ("time", symbol);


--
-- Name: _hyper_2_62_chunk 62_57_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_62_chunk
    ADD CONSTRAINT "62_57_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_63_chunk 63_58_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_63_chunk
    ADD CONSTRAINT "63_58_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_64_chunk 64_59_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_64_chunk
    ADD CONSTRAINT "64_59_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_65_chunk 65_60_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_65_chunk
    ADD CONSTRAINT "65_60_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_66_chunk 66_61_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_66_chunk
    ADD CONSTRAINT "66_61_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_67_chunk 67_62_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_67_chunk
    ADD CONSTRAINT "67_62_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_68_chunk 68_63_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_68_chunk
    ADD CONSTRAINT "68_63_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_69_chunk 69_64_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_69_chunk
    ADD CONSTRAINT "69_64_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_6_chunk 6_8_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_6_chunk
    ADD CONSTRAINT "6_8_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_70_chunk 70_65_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_70_chunk
    ADD CONSTRAINT "70_65_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_71_chunk 71_66_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_71_chunk
    ADD CONSTRAINT "71_66_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_72_chunk 72_67_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_72_chunk
    ADD CONSTRAINT "72_67_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_73_chunk 73_68_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_73_chunk
    ADD CONSTRAINT "73_68_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_74_chunk 74_69_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_74_chunk
    ADD CONSTRAINT "74_69_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_75_chunk 75_70_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_75_chunk
    ADD CONSTRAINT "75_70_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_76_chunk 76_71_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_76_chunk
    ADD CONSTRAINT "76_71_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_77_chunk 77_72_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_77_chunk
    ADD CONSTRAINT "77_72_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_78_chunk 78_73_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_78_chunk
    ADD CONSTRAINT "78_73_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_79_chunk 79_74_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_79_chunk
    ADD CONSTRAINT "79_74_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_7_chunk 7_9_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_7_chunk
    ADD CONSTRAINT "7_9_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_80_chunk 80_75_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_80_chunk
    ADD CONSTRAINT "80_75_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_81_chunk 81_76_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_81_chunk
    ADD CONSTRAINT "81_76_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_82_chunk 82_77_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_82_chunk
    ADD CONSTRAINT "82_77_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_83_chunk 83_78_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_83_chunk
    ADD CONSTRAINT "83_78_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_84_chunk 84_79_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_84_chunk
    ADD CONSTRAINT "84_79_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_85_chunk 85_80_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_85_chunk
    ADD CONSTRAINT "85_80_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_86_chunk 86_81_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_86_chunk
    ADD CONSTRAINT "86_81_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_87_chunk 87_82_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_87_chunk
    ADD CONSTRAINT "87_82_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_88_chunk 88_83_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_88_chunk
    ADD CONSTRAINT "88_83_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_89_chunk 89_84_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_89_chunk
    ADD CONSTRAINT "89_84_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_8_chunk 8_10_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_8_chunk
    ADD CONSTRAINT "8_10_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_90_chunk 90_85_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_90_chunk
    ADD CONSTRAINT "90_85_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_91_chunk 91_86_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_91_chunk
    ADD CONSTRAINT "91_86_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_92_chunk 92_87_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_92_chunk
    ADD CONSTRAINT "92_87_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_93_chunk 93_88_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_93_chunk
    ADD CONSTRAINT "93_88_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_94_chunk 94_89_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_94_chunk
    ADD CONSTRAINT "94_89_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_95_chunk 95_90_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_95_chunk
    ADD CONSTRAINT "95_90_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_96_chunk 96_91_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_96_chunk
    ADD CONSTRAINT "96_91_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_97_chunk 97_92_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_97_chunk
    ADD CONSTRAINT "97_92_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_98_chunk 98_93_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_98_chunk
    ADD CONSTRAINT "98_93_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_99_chunk 99_94_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_99_chunk
    ADD CONSTRAINT "99_94_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_2_9_chunk 9_11_unique_candle; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: postgres
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_9_chunk
    ADD CONSTRAINT "9_11_unique_candle" UNIQUE ("time", symbol, "interval");


--
-- Name: data_quality_metrics data_quality_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.data_quality_metrics
    ADD CONSTRAINT data_quality_metrics_pkey PRIMARY KEY (date);


--
-- Name: market_minutes market_minutes_time_symbol_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.market_minutes
    ADD CONSTRAINT market_minutes_time_symbol_key UNIQUE ("time", symbol);


--
-- Name: symbol_metadata symbol_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.symbol_metadata
    ADD CONSTRAINT symbol_metadata_pkey PRIMARY KEY (symbol);


--
-- Name: market_candles unique_candle; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.market_candles
    ADD CONSTRAINT unique_candle UNIQUE ("time", symbol, "interval");


--
-- Name: _hyper_1_118_chunk_market_ticks_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_1_118_chunk_market_ticks_time_idx ON _timescaledb_internal._hyper_1_118_chunk USING btree ("time" DESC);


--
-- Name: _hyper_1_1_chunk_market_ticks_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_1_1_chunk_market_ticks_time_idx ON _timescaledb_internal._hyper_1_1_chunk USING btree ("time" DESC);


--
-- Name: _hyper_1_57_chunk_market_ticks_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_1_57_chunk_market_ticks_time_idx ON _timescaledb_internal._hyper_1_57_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_100_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_100_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_100_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_101_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_101_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_101_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_102_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_102_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_102_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_103_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_103_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_103_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_104_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_104_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_104_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_105_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_105_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_105_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_106_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_106_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_106_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_107_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_107_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_107_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_108_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_108_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_108_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_109_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_109_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_109_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_10_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_10_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_10_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_110_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_110_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_110_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_111_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_111_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_111_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_112_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_112_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_112_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_113_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_113_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_113_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_114_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_114_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_114_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_115_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_115_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_115_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_11_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_11_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_11_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_12_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_12_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_12_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_13_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_13_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_13_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_14_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_14_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_14_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_15_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_15_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_15_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_16_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_16_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_16_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_17_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_17_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_17_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_18_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_18_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_18_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_19_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_19_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_19_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_20_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_20_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_20_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_21_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_21_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_21_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_22_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_22_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_22_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_23_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_23_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_23_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_24_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_24_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_24_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_25_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_25_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_25_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_26_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_26_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_26_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_27_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_27_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_27_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_28_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_28_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_28_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_29_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_29_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_29_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_2_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_2_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_2_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_30_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_30_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_30_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_31_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_31_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_31_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_32_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_32_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_32_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_33_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_33_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_33_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_34_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_34_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_34_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_35_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_35_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_35_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_36_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_36_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_36_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_37_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_37_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_37_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_38_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_38_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_38_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_39_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_39_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_39_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_3_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_3_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_3_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_40_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_40_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_40_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_41_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_41_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_41_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_42_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_42_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_42_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_43_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_43_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_43_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_44_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_44_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_44_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_45_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_45_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_45_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_46_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_46_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_46_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_47_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_47_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_47_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_48_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_48_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_48_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_49_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_49_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_49_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_4_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_4_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_4_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_50_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_50_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_50_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_51_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_51_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_51_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_52_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_52_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_52_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_53_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_53_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_53_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_54_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_54_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_54_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_5_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_5_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_5_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_62_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_62_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_62_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_63_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_63_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_63_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_64_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_64_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_64_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_65_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_65_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_65_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_66_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_66_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_66_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_67_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_67_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_67_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_68_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_68_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_68_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_69_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_69_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_69_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_6_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_6_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_6_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_70_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_70_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_70_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_71_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_71_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_71_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_72_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_72_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_72_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_73_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_73_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_73_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_74_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_74_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_74_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_75_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_75_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_75_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_76_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_76_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_76_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_77_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_77_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_77_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_78_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_78_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_78_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_79_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_79_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_79_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_7_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_7_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_7_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_80_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_80_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_80_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_81_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_81_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_81_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_82_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_82_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_82_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_83_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_83_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_83_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_84_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_84_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_84_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_85_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_85_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_85_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_86_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_86_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_86_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_87_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_87_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_87_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_88_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_88_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_88_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_89_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_89_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_89_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_8_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_8_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_8_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_90_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_90_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_90_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_91_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_91_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_91_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_92_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_92_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_92_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_93_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_93_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_93_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_94_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_94_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_94_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_95_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_95_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_95_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_96_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_96_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_96_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_97_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_97_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_97_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_98_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_98_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_98_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_99_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_99_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_99_chunk USING btree ("time" DESC);


--
-- Name: _hyper_2_9_chunk_market_candles_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_2_9_chunk_market_candles_time_idx ON _timescaledb_internal._hyper_2_9_chunk USING btree ("time" DESC);


--
-- Name: _hyper_3_55_chunk__materialized_hypertable_3_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_3_55_chunk__materialized_hypertable_3_bucket_idx ON _timescaledb_internal._hyper_3_55_chunk USING btree (bucket DESC);


--
-- Name: _hyper_3_55_chunk__materialized_hypertable_3_symbol_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_3_55_chunk__materialized_hypertable_3_symbol_bucket_idx ON _timescaledb_internal._hyper_3_55_chunk USING btree (symbol, bucket DESC);


--
-- Name: _hyper_4_56_chunk__materialized_hypertable_4_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_4_56_chunk__materialized_hypertable_4_bucket_idx ON _timescaledb_internal._hyper_4_56_chunk USING btree (bucket DESC);


--
-- Name: _hyper_4_56_chunk__materialized_hypertable_4_symbol_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_4_56_chunk__materialized_hypertable_4_symbol_bucket_idx ON _timescaledb_internal._hyper_4_56_chunk USING btree (symbol, bucket DESC);


--
-- Name: _hyper_5_58_chunk__materialized_hypertable_5_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_5_58_chunk__materialized_hypertable_5_bucket_idx ON _timescaledb_internal._hyper_5_58_chunk USING btree (bucket DESC);


--
-- Name: _hyper_5_58_chunk__materialized_hypertable_5_symbol_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_5_58_chunk__materialized_hypertable_5_symbol_bucket_idx ON _timescaledb_internal._hyper_5_58_chunk USING btree (symbol, bucket DESC);


--
-- Name: _hyper_6_119_chunk_market_orderbook_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_6_119_chunk_market_orderbook_time_idx ON _timescaledb_internal._hyper_6_119_chunk USING btree ("time" DESC);


--
-- Name: _hyper_6_59_chunk_market_orderbook_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_6_59_chunk_market_orderbook_time_idx ON _timescaledb_internal._hyper_6_59_chunk USING btree ("time" DESC);


--
-- Name: _hyper_8_60_chunk_market_minutes_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_8_60_chunk_market_minutes_time_idx ON _timescaledb_internal._hyper_8_60_chunk USING btree ("time" DESC);


--
-- Name: _hyper_8_61_chunk_market_minutes_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_8_61_chunk_market_minutes_time_idx ON _timescaledb_internal._hyper_8_61_chunk USING btree ("time" DESC);


--
-- Name: _hyper_9_116_chunk_system_metrics_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_9_116_chunk_system_metrics_time_idx ON _timescaledb_internal._hyper_9_116_chunk USING btree ("time" DESC);


--
-- Name: _hyper_9_117_chunk_system_metrics_time_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _hyper_9_117_chunk_system_metrics_time_idx ON _timescaledb_internal._hyper_9_117_chunk USING btree ("time" DESC);


--
-- Name: _materialized_hypertable_3_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _materialized_hypertable_3_bucket_idx ON _timescaledb_internal._materialized_hypertable_3 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_3_symbol_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _materialized_hypertable_3_symbol_bucket_idx ON _timescaledb_internal._materialized_hypertable_3 USING btree (symbol, bucket DESC);


--
-- Name: _materialized_hypertable_4_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _materialized_hypertable_4_bucket_idx ON _timescaledb_internal._materialized_hypertable_4 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_4_symbol_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _materialized_hypertable_4_symbol_bucket_idx ON _timescaledb_internal._materialized_hypertable_4 USING btree (symbol, bucket DESC);


--
-- Name: _materialized_hypertable_5_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _materialized_hypertable_5_bucket_idx ON _timescaledb_internal._materialized_hypertable_5 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_5_symbol_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: postgres
--

CREATE INDEX _materialized_hypertable_5_symbol_bucket_idx ON _timescaledb_internal._materialized_hypertable_5 USING btree (symbol, bucket DESC);


--
-- Name: idx_dqm_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dqm_date ON public.data_quality_metrics USING btree (date DESC);


--
-- Name: idx_dqm_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dqm_status ON public.data_quality_metrics USING btree (status);


--
-- Name: idx_market_cap; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_market_cap ON public.symbol_metadata USING btree (market_cap DESC);


--
-- Name: idx_sector; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sector ON public.symbol_metadata USING btree (sector);


--
-- Name: market_candles_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX market_candles_time_idx ON public.market_candles USING btree ("time" DESC);


--
-- Name: market_minutes_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX market_minutes_time_idx ON public.market_minutes USING btree ("time" DESC);


--
-- Name: market_orderbook_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX market_orderbook_time_idx ON public.market_orderbook USING btree ("time" DESC);


--
-- Name: market_ticks_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX market_ticks_time_idx ON public.market_ticks USING btree ("time" DESC);


--
-- Name: system_metrics_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX system_metrics_time_idx ON public.system_metrics USING btree ("time" DESC);


--
-- PostgreSQL database dump complete
--

\unrestrict Qq6bj92i4h0XuKrgpTAPRaDjFxMbO1AG3HfbGcCG1aufK1WSrxcPPH52OxQ7s6N

