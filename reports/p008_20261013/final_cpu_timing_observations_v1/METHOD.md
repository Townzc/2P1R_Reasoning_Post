# Final CPU I/O timing proposal: measured local observations, uncalibrated cloud proxy

All26 existing state-export receipts are copied unchanged; no export, oracle, state load or model was repeated. The final T8 oracle was timed during its one required execution. See OBSERVATIONS for exact domains and limitations.

Actual source transfer bytes: 5891909585; state bytes: 5775946082; compact bytes: 108602405; new input bytes: 56405039.

Forecast formula: 1.2 * (3 * (actual_transfer_bytes + 2*input_bytes) / min(all26_original_HTTP_bytes_per_second) + 4 * 24 * once_only_last_T8_local_oracle_wall_seconds + 300) = 3003.275382355175 seconds. The3x/4x/300s parameters are disclosed engineering scenario assumptions, not measured cloud-host properties or a proven upper bound. This only satisfies the local arithmetic criterion if<=3180; independent numeric acceptance remains required before any upload/call. Allfailedparents and24physical/21logical labels remain.
