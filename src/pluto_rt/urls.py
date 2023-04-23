from django.urls import path
from pluto_rt.views import rt_messages

urlpatterns = [
    # Private API view returns and pops items from named queue
    path("<str:queue_name>", view=rt_messages, name="rt_messages"),
]
