# increase the page number when necessary. 
# Add --strategy-only to only crawl strategies from:
# 1. https://www.tradingview.com/scripts/?script_type=strategies  
# 2. https://www.tradingview.com/scripts/editors-picks/?script_type=strategies
cd /workspace/trading_indicators/crawler && \
 python main_trading.py --pages 40 \
 --output-file /workspace/trading_indicators/outputs/trade_raw_data_$(date +%Y%m%d_%H%M%S).json \
 --verbose