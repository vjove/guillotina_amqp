# guillotina_amqp Docs

UNFINISHED!!!!

Some proof of concept here but unfinished!


Integrates aioamqp into guillotina.


## Configuration

Example docs:

```json
    {
        "amqp": {
	       "host": "localhost",
	       "port": 5673,
           "login": "guest",
           "password": "guest",
           "vhost": "/",
           "heartbeat": 800
	    }
    }
```
    
## Dependencies

Python >= 3.6


## Installation

This example will use virtualenv::

```
virtualenv .
./bin/pip install .[test]
```

## Running

Most simple way to get running::

```
./bin/guillotina
```

## Queue tasks

```python
from guillotina_amqp import add_task
await add_task(my_func, 'foobar', kw_arg='blah')
```
