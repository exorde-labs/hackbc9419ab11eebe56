import random
import aiohttp
import asyncio
from datetime import datetime as datett
from datetime import timedelta, timezone
from bs4 import BeautifulSoup
from dateutil import parser
from typing import AsyncGenerator
import hashlib
import logging

from exorde_data import (
    Item,
    Content,
    Author,
    CreatedAt,
    Title,
    Url,
    Domain,
    ExternalId,
    ExternalParentId,
)

################################
base_url = "https://news.ycombinator.com/"
# default values
DEFAULT_OLDNESS_SECONDS = 120
DEFAULT_MAXIMUM_ITEMS = 25
DEFAULT_MIN_POST_LENGTH = 10

class Comment:

    def __init__(self, _user_name, _date_time, _link_thread, comment_link, _title_thread, _comment, _user_id, _parent_user_id):
        self.user_name = _user_name
        self.date_time = _date_time
        self.link_thread = _link_thread
        self.comment_link = comment_link
        self.title_thread = _title_thread
        self.text = _comment
        self.user_id = _user_id
        self.user_parent_id = _parent_user_id


def is_within_timeframe_seconds(dt_str, timeframe_sec):
    # Convert the datetime string to a datetime object
    dt = datett.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%fZ")

    # Make it aware about timezone (UTC)
    dt = dt.replace(tzinfo=timezone.utc)

    # Get the current datetime in UTC
    current_dt = datett.now(timezone.utc)

    # Calculate the time difference between the two datetimes
    time_diff = current_dt - dt

    # Check if the time difference is within the specified timeframe in seconds
    if abs(time_diff) <= timedelta(seconds=timeframe_sec):
        return True
    else:
        return False


USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux i686; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.3',
]

async def request_title_with_timeout(_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(_url, headers={'User-Agent': random.choice(USER_AGENT_LIST)}, timeout=8.0) as response:
                response_text = await response.text()
                soup = BeautifulSoup(response_text, 'html.parser')
                return soup.find("span", {"class": "titleline"}).text
    except Exception as e:
        logging.info(f"[Hackernews] Error request: {str(e)}")


async def request_entries_with_timeout(_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(_url, headers={'User-Agent': random.choice(USER_AGENT_LIST)}, timeout=8.0) as response:
                response_text = await response.text()
                soup = BeautifulSoup(response_text, 'html.parser')
                entries = soup.find_all("tr", {"class": "athing"})
                return entries
    except Exception as e:
        logging.info(f"[Hackernews] Error request: {str(e)}")

def convert_to_standard_timezone(_date):
    """
    Takes an unparsed date and normalizes it
    :param _date: Unparsed date that we need to convert to standard timezone format
    :return: Standardized date format
    """
    dt = parser.parse(_date)  # parse date so we can exploit its data (can't use fuzzy param here to avoid false negatives)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.00Z")


async def parse_entry_for_elements(_athing):
    try:
        user_name = _athing.find("a", {"class": "hnuser"}).text        
        comment_url = base_url +_athing.find("span", {"class": "age"}).find("a")["href"]
        external_id = comment_url.split("?id=")[-1]
        date_time = convert_to_standard_timezone(_athing.find("span", {"class": "age"})["title"])

        blob = _athing.find("span", {"class": "onstory"}).find("a")
        link_thread = base_url + blob["href"]
        external_parent_id = link_thread.split("?id=")[-1]
        link_title = await request_title_with_timeout(link_thread)

        text = link_title + ". "+_athing.find("span", {"class": "commtext c00"}).text

        return Comment(user_name, date_time, link_thread, comment_url, link_title, text, external_id, external_parent_id)
    except Exception as e:
        logging.info("[Hackernews] Parsing Error:" + str(e))

def read_parameters(parameters):
    # Check if parameters is not empty or None
    if parameters and isinstance(parameters, dict):
        try:
            max_oldness_seconds = parameters.get("max_oldness_seconds", DEFAULT_OLDNESS_SECONDS)
        except KeyError:
            max_oldness_seconds = DEFAULT_OLDNESS_SECONDS

        try:
            maximum_items_to_collect = parameters.get("maximum_items_to_collect", DEFAULT_MAXIMUM_ITEMS)
        except KeyError:
            maximum_items_to_collect = DEFAULT_MAXIMUM_ITEMS

        try:
            min_post_length = parameters.get("min_post_length", DEFAULT_MIN_POST_LENGTH)
        except KeyError:
            min_post_length = DEFAULT_MIN_POST_LENGTH
    else:
        # Assign default values if parameters is empty or None
        max_oldness_seconds = DEFAULT_OLDNESS_SECONDS
        maximum_items_to_collect = DEFAULT_MAXIMUM_ITEMS
        min_post_length = DEFAULT_MIN_POST_LENGTH

    return max_oldness_seconds, maximum_items_to_collect, min_post_length


async def query(parameters: dict) -> AsyncGenerator[Item, None]:
    hacker_news_URL = 'https://news.ycombinator.com/newcomments'
    logging.info(f"[Hackernews] Scraping latest posts & comments on {hacker_news_URL}")
    data = await request_entries_with_timeout(hacker_news_URL)

    max_oldness_seconds, maximum_items_to_collect, min_post_length = read_parameters(parameters)
    yielded_items = 0  # Counter for the number of yielded items

    consecutive_rejected_items = 3
    for entry in data:
        if yielded_items >= maximum_items_to_collect:
            break  # Stop the generator if the maximum number of items has been reached

        comment = await parse_entry_for_elements(entry)
        ##### Forge item
        ## start with hash of author
        sha1 = hashlib.sha1()
        # Update the hash with the author string encoded to bytest
        author = "anonymous"
        try:
            author = comment.user_id
        except:
            pass
        sha1.update(author.encode())
        author_sha1_hex = sha1.hexdigest()
        # Make new item & yield        
        if  is_within_timeframe_seconds(dt_str=comment.date_time, timeframe_sec=max_oldness_seconds) \
            and comment.text is not None and len(comment.text) >= min_post_length:
            new_item = Item(
                content=Content(comment.text),
                author=Author(author_sha1_hex),
                created_at=CreatedAt(comment.date_time),
                title=Title(comment.title_thread),
                domain=Domain("news.ycombinator.com"),
                url=Url(comment.comment_link),
                external_id=ExternalId(comment.user_id),
                external_parent_id=ExternalParentId(comment.user_parent_id)
            )
            print(new_item)
            yielded_items += 1  # Increment the counter for yielded items
            yield new_item
        else:
            consecutive_rejected_items -= 1
            if consecutive_rejected_items <= 0:
                break
