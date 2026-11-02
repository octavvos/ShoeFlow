import requests
from celery import shared_task

from . import services


@shared_task(autoretry_for=(requests.RequestException,), retry_backoff=60, max_retries=5)
def fetch_cbu_rates():
    return [str(rate) for rate in services.fetch_cbu_rates()]
