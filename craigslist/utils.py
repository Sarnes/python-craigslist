from bs4 import BeautifulSoup
import requests
import os
from requests.exceptions import RequestException

ALL_SITES_URL = 'http://www.craigslist.org/about/sites'
SITE_URL = 'http://%s.craigslist.org'
USER_AGENT = 'Mozilla/5.0'


def bs(content):
    return BeautifulSoup(content, 'html.parser')


def isiterable(var):
    try:
        return iter(var) and True
    except TypeError:
        return False


def requests_get(*args, **kwargs):
    """
    Retries network errors up to 3 times.
    """

    logger = kwargs.pop('logger', None)

    # Set default User-Agent header if not defined.
    kwargs.setdefault('headers', {}).setdefault('User-Agent', USER_AGENT)

    max_retries = 3
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            return requests.get(*args, **kwargs)

        except (RequestException, ConnectionError, Timeout, socket.error) as exc:
            last_exc = exc

            if logger:
                logger.warning(
                    "Request failed (attempt %d/%d): %s",
                    attempt, max_retries, exc
                )

            # small exponential backoff: 0.5s, 1s, 2s
            if attempt < max_retries:
                time.sleep(0.5 * (2 ** (attempt - 1)))

    # If all retries failed, re-raise last exception
    raise last_exc


def get_all_sites():
    response = requests.get(ALL_SITES_URL)
    response.raise_for_status()  # Something failed?
    soup = BeautifulSoup(response.content, 'html.parser')
    sites = set()

    for box in soup.findAll('div', {'class': 'box'}):
        for a in box.findAll('a'):
            # Remove protocol and get subdomain
            site = a.attrs['href'].rsplit('//', 1)[1].split('.')[0]
            sites.add(site)

    return sites


def get_all_areas(site):
    response = requests.get(SITE_URL % site)
    response.raise_for_status()  # Something failed?
    soup = BeautifulSoup(response.content, 'html.parser')
    raw = soup.select('ul.sublinks li a')
    sites = set(a.attrs['href'].rsplit('/')[1] for a in raw)
    return sites


def get_list_filters(url):
    list_filters = {}
    response = requests_get(url)
    soup = bs(response.content)
    for list_filter in soup.find_all('div', class_='search-attribute'):
        filter_key = list_filter.attrs['data-attr']
        filter_labels = list_filter.find_all('label')
        options = {opt.text.strip(): opt.find('input').get('value')
                   for opt in filter_labels}
        list_filters[filter_key] = {'url_key': filter_key, 'value': options}
    return list_filters
