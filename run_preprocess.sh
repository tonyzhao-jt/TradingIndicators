# cd /workspace/trading_indicators/preprocess/data_agent && \
#     ./run.sh process /workspace/trading_indicators/outputs/strategies_20251014_054134.json 


python /workspace/verl/tools/split_json_data.py \
    --input /workspace/verl/preprocess/data_sft/processed_output_2/intermediate_data_280items_20251017_011134.json --output-dir /workspace/verl/preprocess/data_sft/processed_output_2/split_data \
    --prefix processed_strategies