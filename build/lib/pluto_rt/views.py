from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from redis.connection import Connection, SSLConnection, urlparse
from qr3.qr import Queue


def rt_messages(request: HttpRequest, queue_name: str) -> HttpResponse:
    """ Private/internal API response generator.
    Query redis for a named queue, and return the last `count` messages from that queue.
    Messages are *deleted* from the queue (via .pop()) as they are retrieved. This is fine, as these
    messages are intended for ephemeral real-time display only - any messages intended for permanent
    / future display must be stored separately in persistent storage.

    Works with any python data structure, but general usage assumes messages are stored
    as a list of dicts in the following format:
        {
            "status": "info|success|warning|error",
            "msg": "This is an example"
        }

    qr3.qr provides a direct interface onto redis queues, and provides the following methods
    common to Python queue data structures:

        bqueue = Queue('foobar')
        bqueue.push(someobj)
        bqueue.clear()
        bqueue.elements()
        bqueue.peek()
        bqueue.pop()
        bqueue.push()

    Args:
        queue_name: Required queue name
    Query params:
        count: Optional number of messages to retrieve "per gulp"

    Returns:
        Last `n` messages in the stored data structure, generally as a list of dictionaries, in JSON.
    """

    count = request.GET.get("count") if request.GET.get("count") else 5
    count = int(count)

    # Pull `count` elements off the BACK of the queue and into a list for use elsewhere. Final list
    # should be ordered oldest-first; queue.pop() retrieves the oldest element. Caller may have
    # requested a bigger "gulp" than the number of items in the queue.
    rs = urlparse(settings.CACHES["default"]["LOCATION"])
    prefix = settings.CACHES["default"]["KEY_PREFIX"]
    bqueue = Queue(
        f"{prefix}_{queue_name}",
        host=rs.hostname,
        username=rs.username,
        password=rs.password,
        port=rs.port,
        # SSL connection to AWS. So this works for localhost or server:
        connection_class=SSLConnection if rs.scheme == "rediss" else Connection,
    )
    _ret = list()
    for _ in range(count):
        temp_obj = bqueue.pop()
        if temp_obj:
            _ret.append(temp_obj)

    return JsonResponse(_ret, safe=False)


def get_rt_queue_handle(queue_name: str):
    """Get or create a handle on a QR3 mqueue connection - this
    makes it easy to add messages to a queue from multiple apps
    without repeating this code.

    Identifier should include a function descriptor and ID like
    "eopt_upload_357" or "dragonfly_report_74"

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
