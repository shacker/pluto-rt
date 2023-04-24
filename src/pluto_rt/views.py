from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from redis.connection import Connection, SSLConnection, urlparse
from qr3.qr import Queue


def get_rt_queue_handle(queue_name: str):
    """Get or create a handle on a QR3 mqueue connection,
    for reading or writing.

    Identifier should include a function descriptor and ID like
    "equipment_upload_357" or "dragonfly_report_74"
    """
    rs = urlparse(settings.CACHES["default"]["LOCATION"])
    prefix = settings.CACHES["default"]["KEY_PREFIX"]
    mqueue = Queue(
        f"{prefix}_{queue_name}",
        host=rs.hostname,
        username=rs.username,
        password=rs.password,
        port=rs.port,
        # SSL connection to AWS. So this works for localhost or server:
        connection_class=SSLConnection if rs.scheme == "rediss" else Connection,
    )

    return mqueue


def rt_messages(request: HttpRequest, queue_name: str) -> HttpResponse:
    """Private/internal API response generator.

    Query redis for a named queue, and return the last `count` messages from that queue.
    Messages are deleted from the queue (via .pop()) as they are retrieved.

    Works with any python data structure, but pluto-rt usage assumes messages are stored
    as a list of dicts in the following format:

        {
            "status": "info|success|warning|error",
            "msg": "This is an example"
        }

    The consumer converts that list of dicts to table rows in an htmx template fragment.

    qr3.qr provides a direct interface onto redis queues, and provides the following methods
    common to Python queue data structures:

        mqueue = Queue('foobar')
        mqueue.push(someobj)
        mqueue.clear()
        mqueue.elements()
        mqueue.peek()
        mqueue.pop()
        mqueue.push()

    Args:
        queue_name: Required queue name
    Query params:
        count: Optional number of messages to retrieve "per gulp"

    Returns:
        Last `n` messages in the queue, generally as a list of dictionaries, in JSON.
    """

    count = request.GET.get("count")
    count = int(count) if count else 5
    mqueue = get_rt_queue_handle(queue_name)

    if mqueue.elements():
        items = list()
        for _ in range(count):
            temp_obj = mqueue.pop()
            if temp_obj:
                items.append(temp_obj)

        return render(request, "pluto_rt/rows.html", {"items": items})

    else:
        # Send a 286 response to stop htmx polling when the queue is empty
        response = HttpResponse()
        response.status_code = 286
        return response
