from celery import Celery
from core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Cria a instância principal do Celery
celery_app = Celery(
    "cogep_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["worker_service.tasks"]  # Onde procurar por arquivos de tarefas
)

# Configuração opcional (ajusta para UTC, etc.)
celery_app.conf.update(
    task_track_started=True,
    timezone='UTC',
    enable_utc=True,
)

# Configuração do Celery Beat (Agendador de Tarefas)
# Vamos configurar uma tarefa para rodar a cada 30 segundos
celery_app.conf.beat_schedule = {
    'poll-ingestion-queue-every-30-seconds': {
        'task': 'worker_service.tasks.poll_and_process_jobs',
        'schedule': 30.0,  # Em segundos
    },
}