import os
from celery import Celery, signals
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tg_agregator.settings")
app = Celery("tg_agregator")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_TASK_DEFAULT_QUEUE = "celery"
CELERY_TASK_QUEUES = (Queue("celery", Exchange("celery"), routing_key="celery"),)
CELERY_TASK_ROUTES = {"app.*": {"queue": "celery", "routing_key": "celery"}}

CELERY_WORKER_REDIRECT_STDOUTS = True
CELERY_WORKER_REDIRECT_STDOUTS_LEVEL = "INFO"

@signals.worker_ready.connect
def at_start(sender, **kwargs):
    sender.app.send_task("app.fetch_and_publish_every_3h")