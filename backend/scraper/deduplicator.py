import hashlib

def review_hash(property_id:int,review_date,rating:int,positive:str|None=None,negative:str|None=None,external_id:str|None=None)->str:
    raw=f"{property_id}|{review_date.isoformat()}|{rating}|{positive or ''}|{negative or ''}|{external_id or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
