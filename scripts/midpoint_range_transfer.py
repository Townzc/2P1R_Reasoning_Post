"""Bounded read-only checkpoint transport; all ranges and failures are retained."""
import asyncio
from pathlib import Path
import shutil
import time

from experiments.sft_allocation_midpoint.common import sha, dump


BLOCK = 8 * 1024 * 1024


def ranges(size, block=BLOCK):
    if type(size) is not int or size <= 0 or type(block) is not int or block <= 0:
        raise ValueError('Invalid byte range')
    return [(start, min(block, size-start)) for start in range(0, size, block)]


def assemble(parts, target, spec):
    """Only an exact full-file hash allows a new destination; never overwrite."""
    parts, target = Path(parts), Path(target)
    if target.exists():
        raise FileExistsError(target.name)
    candidate = parts / 'assembled.pt'
    with candidate.open('xb') as dest:
        for start, length in ranges(spec['bytes']):
            part = parts / f'{start:012d}.bin'
            if part.stat().st_size != length:
                raise ValueError('Range size differs')
            with part.open('rb') as source:
                shutil.copyfileobj(source, dest)
    if candidate.stat().st_size != spec['bytes'] or sha(candidate) != spec['sha256']:
        raise ValueError('Whole checkpoint SHA differs')
    with candidate.open('rb') as source, target.open('xb') as dest:
        shutil.copyfileobj(source, dest)
    if sha(target) != spec['sha256']:
        raise ValueError('Published local copy differs')


def download_large(volume_name, remote, target, spec, seconds=240, transport_tag=""):
    import re
    if transport_tag and not re.fullmatch(r"[a-zA-Z0-9_-]+", transport_tag):
        raise ValueError("Invalid transport attempt tag")
    import aiohttp
    from modal.volume import _Volume, _raise_on_block_response_error, _read_block_body
    from modal_proto import api_pb2

    target = Path(target)
    if target.exists():
        raise FileExistsError(target.name)
    parts = target.with_name(target.name + '.parts' + ('_' + transport_tag if transport_tag else ''))
    parts.mkdir(exist_ok=False)
    records = []
    started = time.time()

    async def work():
        volume = _Volume.from_name(volume_name, create_if_missing=False)
        await volume.hydrate()
        sem = asyncio.Semaphore(4)
        timeout = aiohttp.ClientTimeout(total=35, connect=10, sock_read=15)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async def one(start, length):
                async with sem:
                    record = dict(start=start, length=length, status='attempted')
                    records.append(record)
                    tick = time.monotonic()
                    try:
                        response = await asyncio.wait_for(volume.client._stub.VolumeGetFile2(
                            api_pb2.VolumeGetFile2Request(volume_id=volume.object_id, path=remote,
                                start=start, len=length, client_pads_blocks=True)), 20)
                        if response.start != start or response.len != length or len(response.get_urls) != 1:
                            raise ValueError('Provider range boundary differs')
                        async with client.get(response.get_urls[0]) as response_http:
                            await _raise_on_block_response_error(response_http)
                            body = await _read_block_body(response_http, length)
                        # Match the SDK's sparse trailing-zero block protocol.
                        if len(body) > length:
                            raise ValueError('Oversized provider range')
                        body = body.ljust(length, b'\0')
                        file = parts / f'{start:012d}.bin'
                        with file.open('xb') as dest:
                            dest.write(body)
                        record.update(status='verified_response', sha256=sha(file))
                    except BaseException as error:
                        record.update(status='failed_or_interrupted', error_type=type(error).__name__)
                        raise
                    finally:
                        record['seconds'] = time.monotonic()-tick
            await asyncio.gather(*(one(start, length) for start, length in ranges(spec['bytes'])))

    receipt = dict(remote=remote, expected=spec, read_only=True, scientific_calls=0,
                   started_epoch=started, ranges=records, complete=False, retry_count=0)
    try:
        asyncio.run(asyncio.wait_for(work(), seconds))
        assemble(parts, target, spec)
        receipt['complete'] = True
    except BaseException as error:
        receipt['error_type'] = type(error).__name__
        raise
    finally:
        receipt['finished_epoch'] = time.time()
        dump(parts/'transport_receipt.json', receipt)



if __name__ == '__main__':
    import argparse, json
    p=argparse.ArgumentParser()
    p.add_argument('--volume',required=True);p.add_argument('--remote',required=True)
    p.add_argument('--target',required=True);p.add_argument('--spec-json',required=True)
    p.add_argument('--transport-tag',default='')
    a=p.parse_args()
    download_large(a.volume,a.remote,a.target,json.loads(a.spec_json),transport_tag=a.transport_tag)
