from django.core.cache import cache


def entry_cache_key(entry) -> str:
    return f"delivery:entry:{entry.publication_id}:{entry.slug}"


def list_cache_key(publication_id, locale, status="published") -> str:
    return f"delivery:list:{publication_id}:{locale}:{status}"


def invalidate_entry_cache(entry):
    cache.delete(entry_cache_key(entry))
    cache.delete(list_cache_key(entry.publication_id, entry.locale))
    cache.delete(f"delivery:id:{entry.id}")
