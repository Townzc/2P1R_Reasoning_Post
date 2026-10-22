"""Memory-bounded view over one immutable new encoded roster; no re-encoding."""
from pathlib import Path
import json


class EncodedRow(dict):
    def __init__(self, owner, index):
        super().__init__(owner.metadata[index])
        self.owner,self.index,self.loaded=owner,index,None
    def __getitem__(self,key):
        meta=self.owner.metadata[self.index]
        if key in meta:return meta[key]
        if self.loaded is None:
            with self.owner.file.open('rb') as stream:
                stream.seek(self.owner.offsets[self.index]);self.loaded=json.loads(stream.readline())
            if any(self.loaded.get(k)!=v for k,v in meta.items()):raise ValueError('Encoded row metadata differs')
        return self.loaded[key]
    def __iter__(self):
        self['input_ids'];return iter(self.loaded)
    def __len__(self):
        self['input_ids'];return len(self.loaded)
    def items(self):
        self['input_ids'];return self.loaded.items()


class EncodedRows(list):
    """Metadata reads never materialize input/label arrays or full-state copies."""
    def __init__(self,file,metadata,count):
        self.file=Path(file);self.metadata=metadata[:count];self.offsets=[]
        if count not in (3024,9072) or len(self.metadata)!=count:raise ValueError('Exact amended roster required')
        super().__init__([None]*count)
        with self.file.open('rb') as stream:
            for _ in range(count):
                self.offsets.append(stream.tell())
                if not stream.readline():raise ValueError('Truncated encoded roster')
    def __len__(self):return len(self.metadata)
    def __iter__(self):
        for i in range(len(self)):yield self[i]
    def __getitem__(self,index):
        if isinstance(index,slice):return [self[i] for i in range(*index.indices(len(self)))]
        if index<0:index+=len(self)
        if not 0<=index<len(self):raise IndexError(index)
        return EncodedRow(self,index)
