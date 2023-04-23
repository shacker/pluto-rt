# Pluto: Real-time web results for long-running processes

Any time you have a need to trigger a long-running process from a web view,
you run into Python's blocking nature. Nothing will be displayed until the
process is complete, and you'll hit timeouts if you exceed the default timeout
for your web application process.

To solve the long-running aspect, we turn to background workers like django-q
or django-celery. But then the user has no insight into what the background
worker is doing.

This system solves that by using a library called [QR3](https://pypi.org/project/qr3/), which
utilizes Redis as a message queuing service. Messages can be placed on the queue and their order is
remembered. As messages are retrieved from the queue, it automatically delivers the
oldest ones first.

https://user-images.githubusercontent.com/102694/233860792-652f8790-6f31-4dd8-8c37-fc479171c576.mov

The overall strategy is this:

1. Invoke your background processor (worker) with a unique queue name
1. The worker places messages onto the queue, associated with that name
1. A private internal API retrieves and removes the oldest `n` messages from that queue
1. HTMX polling from the web view appends the results of each gulp to a display table


## Prerequisites

We assume you already have these installed and working

- A running Django project
- A running Redis server
- A base project template called `base.html` (use a custom template if not - see below)
- Your `base.html` includes HTMX
- A runnning background processor such as django-q or django-celery
- A standalone function that processes data and whose real-time output you want to display
- A `KEY_PREFIX` is defined in in your project cache settings, e.g.

```
CACHES = {
    "default": {
        ...
        "BACKEND": "django_redis.cache.RedisCache",
        "KEY_PREFIX": config.REDIS_PREFIX,  # or some fixed string for your project
        ...
    }
}
```

## Installation:

- `pip install ~/dev/pluto-rt` (TODO: temporary)
- Add `pluto_rt` to the list of installed apps in project settings.
- To enable the internal API (required), add this to your top-level urls.py:

```
path("rt_messages/", include("rt.urls")),
```

## Usage
There are two views you'll need to control: the view that kicks off the process
and passes tasks to the background worker, and the view that consumes the results.

### Calling the process

First: Work to be done should be defined in a single function, which will be passed to the
background worker.  The calling view should generate a descriptive queue name, made relatively
unique with an ID (upload ID works well for this). It should invoke your background processor with
that function and the queue name as arguments, then redirect to the display view. For example:

```
from django.views import View

class Home(View):
    """
    On POST, receive upload ID (or something unique-ish), generate a queue_name,
    and call a background process that acceps the queue_name. Then redirect
    to the real-time results display view.
    """

    def get(self, request):
        ctx = {}
        return render(request, "home.html", ctx)

    def post(self, request):
        upload_id = request.POST.get("upload_id")
        queue_name = f"demo_run_{upload_id}"
        async_task(
            sample_ops_function,
            queue_name=queue_name,
        )
        return redirect(reverse("rt_demo", kwargs={"queue_name": queue_name}))
```

### Background worker

The invocation above refers to `sample_ops_function` which can be any function
in your project. The function *must* accept a `queue_name` argument. This demo
example just generates some random messages with random states and pushes them
onto the queue.

```
from pluto_rt.views import get_rt_queue_handle
from faker import Faker
import random


def sample_ops_function(queue_name: str):
    """
    Demo function that processes data, such as reading and
    handling rows of an ETL job (reading a spreadsheet, sending email, whatever.)
    In this case, we just generate `n` random messages and put them
    on the queue. The html template is responsible for popping those
    messages off the queue. In real-world use, this function would be some
    long-running ETL or other task that can be reasonably chunked.

    Args:
        Required queue_name (generated in the calling view and passed in)

    """
    mqueue = get_rt_queue_handle(queue_name)

    for idx in range(1, 26):
        # Do some work here, on a row or any task chunk, then emit a message

        msg = f"{idx}: {Faker().sentence()}"
        statuses = ["success", "danger", "info", "warning"]

        row_dict = {"status": random.choice(statuses), "msg": msg}
        mqueue.push(row_dict)

    row_dict = {"status": "success", "msg": "Demo complete"}
    mqueue.push(row_dict)
```

### Displaying results

The invoking view above redirects to the real-time results display view, which would
be written something like this:

```
class DemoResults(View):
    """
    This view accepts the queue_name and renders HTML that uses
    the queue_name to call the internal API, grabbing some number of
    items, separated by some delay. The template path shown here
    is provided by pluto-rt and does not need to be created (but feel
    free to override).
    """

    def get(self, request, queue_name: str):
        """
        Real-time results display of demo report run
        """

        ctx = {
            "queue_name": queue_name,
            "num_per_gulp": 3,
            "interval_seconds": 2
        }

        return render(request, "pluto_rt/rt_results.html", ctx)

```

Each use case is different, so modify the numeric args to suit.





