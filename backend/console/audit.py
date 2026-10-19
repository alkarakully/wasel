from .models import AuditEntry


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def record(request, action, summary, target=None, changes=None):
    """Write one audit entry for a change made in the platform admin."""
    user = request.user if request.user.is_authenticated else None
    profile = getattr(request, "staff", None)
    return AuditEntry.objects.create(
        actor=user,
        actor_email=profile.email if profile else "",
        action=action,
        target_type=type(target).__name__.lower() if target is not None else "",
        target_id=str(getattr(target, "pk", "") or ""),
        summary=summary[:300],
        changes=changes or {},
        ip=client_ip(request),
    )


def diff(instance, data, fields):
    """{field: [old, new]} for the fields in `data` that change on `instance`."""
    changes = {}
    for field in fields:
        if field in data:
            old, new = getattr(instance, field), data[field]
            if str(old) != str(new):
                changes[field] = [str(old), str(new)]
    return changes
