from celery import Celery
import os


def create_celery_app() -> Celery:
    celery_app = Celery(
        "crypto_app",
        broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
        # Include your task modules
        include=[
            "app.services.celery_tasks",
        ]
    )
    
    # Celery configuration
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_routes={
            "app.services.celery_tasks.*": {"queue": "crypto_queue"},
        },
        # Add beat schedule if you have periodic tasks
        beat_schedule={
            # Example: 'fetch-crypto-data': {
            #     'task': 'app.services.celery_tasks.fetch_crypto_data',
            #     'schedule': 60.0,  # Run every 60 seconds
            # },
        },
    )
    
    return celery_app