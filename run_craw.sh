# increase the page number when necessary. 
cd /workspace/trading_indicators/crawler && \
 python main_trading.py --pages 10 \
 --output-file /workspace/trading_indicators/output/trade_raw_data_$(date +%Y%m%d_%H%M%S).json \
 --verbose