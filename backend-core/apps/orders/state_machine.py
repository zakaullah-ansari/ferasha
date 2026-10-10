"""Order state machine.

Transitions are validated in a service function rather than by assigning to
``order.status``. An order is a contract with a customer and a production
instruction to the atelier; an illegal jump - "delivered" from "draft", or a
refund on an order that was never paid - must be impossible rather than merely
discouraged.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import Order, OrderEvent, OrderStatus

S = OrderStatus

#: Permitted transitions. Absence from this map means the transition is illegal.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    S.DRAFT: frozenset({S.PLACED, S.CANCELLED}),
    S.PLACED: frozenset({S.PAYMENT_CONFIRMED, S.CANCELLED}),
    S.PAYMENT_CONFIRMED: frozenset(
        {S.IN_ATELIER, S.MEASUREMENT_REVIEW, S.PACKED, S.CANCELLED}
    ),
    S.MEASUREMENT_REVIEW: frozenset({S.IN_ATELIER, S.CANCELLED}),
    S.IN_ATELIER: frozenset({S.STITCHING, S.MEASUREMENT_REVIEW, S.CANCELLED}),
    S.STITCHING: frozenset({S.QUALITY_CHECK, S.CANCELLED}),
    S.QUALITY_CHECK: frozenset({S.PACKED, S.STITCHING}),
    S.PACKED: frozenset({S.SHIPPED}),
    S.SHIPPED: frozenset({S.DELIVERED}),
    S.DELIVERED: frozenset({S.RETURN_REQUESTED}),
    S.RETURN_REQUESTED: frozenset({S.RETURNED, S.DELIVERED}),
    S.RETURNED: frozenset({S.REFUNDED}),
    # Terminal.
    S.REFUNDED: frozenset(),
    S.CANCELLED: frozenset(),
}

TERMINAL_STATUSES = frozenset({S.REFUNDED, S.CANCELLED})

#: Statuses from which stock has been committed and must be released on cancel.
STOCK_COMMITTED_STATUSES = frozenset(
    {S.PLACED, S.PAYMENT_CONFIRMED, S.MEASUREMENT_REVIEW, S.IN_ATELIER,
     S.STITCHING, S.QUALITY_CHECK, S.PACKED, S.SHIPPED}
)


class IllegalTransition(ValueError):
    """Raised when a requested order state change is not permitted."""


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def available_transitions(current: str) -> frozenset[str]:
    return ALLOWED_TRANSITIONS.get(current, frozenset())


@transaction.atomic
def transition_order(
    order: Order,
    target: str,
    *,
    actor=None,
    reason: str = "",
    metadata: dict | None = None,
) -> Order:
    """Move ``order`` to ``target``, recording an audit event.

    Raises ``IllegalTransition`` if the move is not permitted. The order row is
    locked for the duration so two concurrent operators cannot both transition
    it from the same starting state.
    """
    locked = Order.objects.select_for_update().get(pk=order.pk)
    current = locked.status
    # Normalise: callers pass either the enum member or its value, and an
    # enum repr leaking into a customer-visible error message is sloppy.
    target = str(getattr(target, "value", target))

    if current == target:
        raise IllegalTransition(f"Order {locked.order_number} is already {target!r}.")

    if current in TERMINAL_STATUSES:
        raise IllegalTransition(
            f"Order {locked.order_number} is in terminal state {current!r} and cannot "
            f"be moved to {target!r}."
        )

    if not can_transition(current, target):
        allowed = sorted(available_transitions(current)) or ["(none - terminal)"]
        raise IllegalTransition(
            f"Cannot move order {locked.order_number} from {current!r} to {target!r}. "
            f"Allowed from {current!r}: {', '.join(allowed)}."
        )

    if target == S.REFUNDED and current != S.RETURNED:  # pragma: no cover - defensive
        raise IllegalTransition("A refund requires the goods to have been returned first.")

    locked.status = target
    update_fields = ["status", "updated_at"]

    if target == S.PLACED and locked.placed_at is None:
        locked.placed_at = timezone.now()
        update_fields.append("placed_at")
    if target == S.DELIVERED and locked.delivered_at is None:
        locked.delivered_at = timezone.now()
        update_fields.append("delivered_at")

    locked.save(update_fields=update_fields)

    OrderEvent.objects.create(
        order=locked,
        from_status=current,
        to_status=target,
        actor=actor,
        reason=reason[:300],
        metadata=metadata or {},
    )

    order.status = target
    order.placed_at = locked.placed_at
    order.delivered_at = locked.delivered_at
    return locked
