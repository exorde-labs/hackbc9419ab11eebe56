from hackbc9419ab11eebe56 import query
from exorde_data.models import Item
import pytest


@pytest.mark.asyncio
async def test_query():
    try:
        # Example parameters dictionary
        parameters = {
            # "max_oldness_seconds":30,
            "maximum_items_to_collect": 3,
            "min_post_length": 20
        }
        async for item in query(parameters):
            assert isinstance(item, Item)
            print("\n")
            print("Title = ",item['title'])
            print("Date = ",item['created_at'])
            print("Content = ",item['content'])
            print("author = ",item['author'])
            print("url = ",item['url'])
            print("external_id = ",item['external_id'])
            print("external_parent_id = ",item['external_parent_id'])
    except ValueError as e:
        print(f"Error: {str(e)}")