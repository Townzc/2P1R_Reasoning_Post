"""CR candidate R3 shared batch geometry; all scientific requests/seeds unchanged."""
ENDPOINT_COUNT = 3300
ENDPOINT_BATCH = 512
ENGINE_MAX_SEQS = 256
GRAPH_CAPTURE_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256]
ENDPOINT_BATCHES = (ENDPOINT_COUNT + ENDPOINT_BATCH - 1) // ENDPOINT_BATCH


def endpoint_batches(count):
    if type(count) is not int or count < 1 or count > ENDPOINT_COUNT:
        raise ValueError('Positive original endpoint roster size required')
    return (count + ENDPOINT_BATCH - 1) // ENDPOINT_BATCH


def resources(kind, arm):
    if kind not in ('student', 'baseline') or arm not in ('S-L15', 'S-F15', 'S-L3'):
        raise ValueError('Original A/D kind and arm required')
    if kind == 'baseline' and arm == 'S-F15':
        raise ValueError('No separate full-parameter baseline')
    return {'cpu': 4, 'memory_mib': 98304 if arm == 'S-F15' else 32768}
