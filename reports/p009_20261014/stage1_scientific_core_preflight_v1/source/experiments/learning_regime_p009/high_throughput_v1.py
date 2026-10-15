"""Owner-selected common engine settings; no model import or measurement here."""
from copy import deepcopy

BATCH_SIZE = 256
ENGINE_KWARGS = dict(
    dtype='bfloat16', tensor_parallel_size=1, max_model_len=2048,
    max_num_seqs=256, max_num_batched_tokens=8192, gpu_memory_utilization=.80,
    enforce_eager=False, enable_prefix_caching=False, enable_chunked_prefill=True,
    seed=17, generation_config='vllm', disable_log_stats=True, trust_remote_code=False,
    compilation_config=dict(level=3, cudagraph_mode='FULL_AND_PIECEWISE',
        cudagraph_capture_sizes=[1, 2, 4, 8, 16, 32, 64, 128, 256]),
)


def engine_kwargs():
    return deepcopy(ENGINE_KWARGS)


def actual_engine(config):
    """Fail before generating if vLLM silently changes the selected configuration."""
    actual = dict(
        max_model_len=config.model_config.max_model_len,
        enforce_eager=config.model_config.enforce_eager,
        dtype=str(config.model_config.dtype),
        max_num_seqs=config.scheduler_config.max_num_seqs,
        max_num_batched_tokens=config.scheduler_config.max_num_batched_tokens,
        enable_chunked_prefill=config.scheduler_config.enable_chunked_prefill,
        enable_prefix_caching=config.cache_config.enable_prefix_caching,
        gpu_memory_utilization=config.cache_config.gpu_memory_utilization,
        compilation_level=config.compilation_config.level,
        cudagraph_mode=config.compilation_config.cudagraph_mode.name,
        cudagraph_capture_sizes=sorted(config.compilation_config.cudagraph_capture_sizes),
    )
    return validate_observed_engine(actual)


def validate_observed_engine(actual):
    expected = dict(max_model_len=2048, enforce_eager=False, dtype='torch.bfloat16',
        max_num_seqs=256, max_num_batched_tokens=8192, enable_chunked_prefill=True,
        enable_prefix_caching=False, gpu_memory_utilization=.80, compilation_level=3,
        cudagraph_mode='FULL_AND_PIECEWISE',
        cudagraph_capture_sizes=[1, 2, 4, 8, 16, 32, 64, 128, 256])
    if actual != expected:
        raise ValueError('Actual high-throughput engine differs; no eager fallback')
    return actual
