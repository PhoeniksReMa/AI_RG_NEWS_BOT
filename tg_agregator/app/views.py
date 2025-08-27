from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

from .bot_sender import send_text
from .services import (
    refresh_tops_for_all_themes,
    fetch_recent_posts_for_top,
)


@csrf_exempt
@require_GET
def refresh_tops_view(request):
    data = refresh_tops_for_all_themes()
    return JsonResponse(
        data, safe=False,
        json_dumps_params={"ensure_ascii": False, "indent": 2}
    )

@csrf_exempt
@require_GET
def generate_posts_view(request):
    data = fetch_recent_posts_for_top()
    print(data)
    send_text(data)
    return JsonResponse(
        data, safe=False,
        json_dumps_params={"ensure_ascii": False, "indent": 2}
    )