from itertools import batched
from hashlib import sha256
from utils import ALPHABET

def encode_base128(data: bytes) -> str:
    result = ""
    for batch in batched(data, 7):
        counter = 0
        for b in map(lambda b:b>127, reversed(batch)): counter = (counter<<1)+b
        result += ALPHABET[counter]
        for b in batch: result += ALPHABET[b%128]
    return result

def decode_base128(text: str) -> bytes:
    result = []
    for counter, *word in batched(text, 8):
        counter = ALPHABET.index(counter)
        for i, ch in enumerate(word):
            result.append(ALPHABET.index(ch)+(counter>>i)%2*128)
    return bytes(result)

def hash(text: str) -> str:
    return encode_base128(sha256(text.encode('utf-8')+b'+salt').digest())