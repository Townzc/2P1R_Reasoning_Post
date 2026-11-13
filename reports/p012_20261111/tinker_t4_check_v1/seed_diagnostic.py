"""Prepared T4 diagnostic; no execution before the owner releases the T4 hold."""
import argparse
import json
import os
from pathlib import Path
import tinker
from experiments.p012.tinker_lora import load_renderer, generate, write_json, read_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    if request.get('owner_authorized') is not True:
        raise ValueError('T4 diagnostic awaits owner decision')
    if not os.environ.get('TINKER_API_KEY'):
        raise ValueError('Private credential must be supplied in the environment')
    rows = read_rows(request['evaluation'])
    if len(rows) != 64 or request['forecast']['buffered_upper_usd'] > .4:
        raise ValueError('Diagnostic scope or budget changed')
    tokenizer, renderer = load_renderer(request)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / 'REQUEST.json', request)
    service = tinker.ServiceClient(display_name=request['run_id'])
    try:
        client = service.create_sampling_client(base_model=request['model']).result()
        usage = generate(client, tokenizer, renderer, rows, request['evaluation'],
                         args.output / 'generation', n=1, temperature=.7,
                         seed=17, concurrency=32)
        write_json(args.output / 'USAGE.json', usage)
        write_json(args.output / 'COMPLETE.json', {'success': True, 'answers_scored': False,
                   'diagnostic_only': True, 'primary_endpoint_replaced': False})
        service.close(status='success').result()
    except BaseException:
        service.close(status='errored').result()
        raise


if __name__ == '__main__':
    main()
