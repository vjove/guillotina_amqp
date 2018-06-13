from guillotina import app_settings
from guillotina.component import get_utility
from guillotina_amqp import amqp
from guillotina_amqp.interfaces import IStateManagerUtility
from guillotina_amqp.job import Job

import asyncio
import json
import time


class Worker:
    sleep_interval = 0.05
    last_activity = time.time()
    total_run = 0

    def __init__(self, request, loop=None, max_size=5):
        self.request = request
        self.loop = loop
        self._running = []
        self._max_size = max_size
        self._closing = False
        self._state_manager = None

    @property
    def state_manager(self):
        if self._state_manager is None:
            self._state_manager = get_utility(
                IStateManagerUtility,
                name=app_settings['amqp'].get('persistent_manager', 'dummy'))
        return self._state_manager

    @property
    def num_running(self):
        return len(self._running)

    async def handle_queued_job(self, channel, body, envelope, properties):
        if not isinstance(body, str):
            body = body.decode('utf-8')
        data = json.loads(body)
        await self.state_manager.update(data['task_id'], {
            'status': 'scheduled'
        })
        while len(self._running) >= self._max_size:
            await asyncio.sleep(self.sleep_interval)
            self.last_activity = time.time()
        self.last_activity = time.time()
        job = Job(self.request, data, channel, envelope)
        task = self.loop.create_task(job())
        task._job = job
        job.task = task
        self._running.append(task)
        task.add_done_callback(self._done_callback)

    def _done_callback(self, task):
        self._running.remove(task)
        self.total_run += 1

    async def start(self):
        channel, transport, protocol = await amqp.get_connection()

        await channel.queue_declare(
            queue_name=app_settings['amqp']['queue'] + '-error', durable=True,
            arguments={
                'x-message-ttl': 1000 * 60 * 60 * 24 * 7
            })
        await channel.queue_declare(
            queue_name=app_settings['amqp']['queue'], durable=True,
            arguments={
                'x-dead-letter-exchange': app_settings['amqp']['exchange'],
                'x-dead-letter-routing-key': app_settings['amqp']['queue'] + '-error'
            })
        await channel.queue_bind(
            exchange_name=app_settings['amqp']['exchange'],
            queue_name=app_settings['amqp']['queue'],
            routing_key=app_settings['amqp']['queue'])

        await channel.basic_qos(prefetch_count=4)
        await channel.basic_consume(
            self.handle_queued_job,
            queue_name=app_settings['amqp']['queue'])

    def cancel(self):
        for task in self._running:
            task.cancel()

    async def join(self):
        while len(self._running) > 0:
            await asyncio.sleep(0.01)