import json
from aiohttp import ClientSession
from app.internal.audible.single import get_single_book
import pytest

@pytest.mark.asyncio
async def test_quick():
    """Quick test with real API call"""
    
    # Test with a real ASIN (find one from Audible)
    asin = "B0DQVKNT56"  # Replace with a working ASIN
    
    async with ClientSession() as session:
        print(f"Fetching book {asin}...")
        book = await get_single_book(session, asin)

        assert book is not None
        assert len(book.series) > 0
        
        # Try to print as JSON if possible
        if hasattr(book, 'json'):
            print(book.model_dump_json(indent=2))
        elif hasattr(book, 'dict'):
            print(json.dumps(book.dict(), indent=2, default=str))
        else:
            print(book)
        
        return book
