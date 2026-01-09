import pandas as pd
import numpy as np

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    상대강도지수(RSI)를 계산한다.
    
    Args:
        df (pd.DataFrame): 'close' 컬럼을 포함한 데이터프레임
        period (int): 계산 기간 (기본값 14)
        
    Returns:
        pd.Series: RSI 값
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD(Moving Average Convergence Divergence)를 계산한다.
    
    Args:
        df (pd.DataFrame): 'close' 컬럼을 포함한 데이터프레임
        fast (int): 단기 이평선 기간
        slow (int): 장기 이평선 기간
        signal (int): 신호선 기간
        
    Returns:
        tuple: (macd_line, signal_line, histogram)
    """
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2):
    """
    볼린저 밴드(Bollinger Bands)를 계산한다.
    
    Args:
        df (pd.DataFrame): 'close' 컬럼을 포함한 데이터프레임
        period (int): 이동평균 기간
        std_dev (int): 표준편차 승수
        
    Returns:
        tuple: (upper_band, mid_band, lower_band)
    """
    mid_band = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper_band = mid_band + (std * std_dev)
    lower_band = mid_band - (std * std_dev)
    return upper_band, mid_band, lower_band
