# Program

This directory stores the staged execution flow used by the framework.

- `step1_prepare_data.py`: load, clean, and calendar-align stock-level daily data.
- `step2_calculate_factors.py`: calculate active ranking and filter factors, then aggregate them to the holding period.
- `step3_select_stocks.py`: filter the universe, rank candidates, and save the rebalance selection.
- `step4_simulate_performance.py`: transform selection weights into account-path and performance outputs.
