"""Order state machine, tax snapshot immutability and audit trail tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.orders.models import (
    Order,
    OrderEvent,
    OrderLine,
    OrderStatus,
    OrderTaxSnapshot,
    SupplyType,
)
from apps.orders.state_machine import (
    IllegalTransition,
    available_transitions,
    can_transition,
    transition_order,
)
from apps.taxes.services import PlaceOfSupply, TaxableLine, calculate_gst
from tests.factories import make_user

pytestmark = pytest.mark.django_db

S = OrderStatus


def make_order(**kw):
    defaults = dict(
        order_number=f"FER-{Order.objects.count() + 1:06d}",
        guest_email="guest@example.com",
        status=S.DRAFT,
        place_of_supply_state="MH",
        place_of_supply_country="IN",
    )
    defaults.update(kw)
    return Order.objects.create(**defaults)


class TestOrderConstraints:
    def test_order_needs_customer_or_guest_email(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(order_number="FER-X", guest_email="", customer=None)

    def test_guest_order_allowed(self):
        order = make_order(customer=None, guest_email="guest@example.com")
        assert order.is_guest is True
        assert order.contact_email == "guest@example.com"

    def test_registered_order_uses_account_email(self):
        user = make_user(email="ayesha@example.com")
        order = make_order(customer=user, guest_email="")
        assert order.is_guest is False
        assert order.contact_email == "ayesha@example.com"

    def test_negative_grand_total_rejected(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_order(grand_total=Decimal("-1.00"))

    def test_invalid_status_rejected_by_database(self):
        order = make_order()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Order.objects.filter(pk=order.pk).update(status="teleported")

    def test_order_number_is_unique(self):
        make_order(order_number="FER-000999")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_order(order_number="FER-000999")


class TestStateMachine:
    def test_happy_path_ready_to_wear(self):
        order = make_order()
        for target in (S.PLACED, S.PAYMENT_CONFIRMED, S.PACKED, S.SHIPPED, S.DELIVERED):
            transition_order(order, target)
        order.refresh_from_db()
        assert order.status == S.DELIVERED

    def test_happy_path_bespoke(self):
        order = make_order()
        for target in (
            S.PLACED, S.PAYMENT_CONFIRMED, S.MEASUREMENT_REVIEW, S.IN_ATELIER,
            S.STITCHING, S.QUALITY_CHECK, S.PACKED, S.SHIPPED, S.DELIVERED,
        ):
            transition_order(order, target)
        order.refresh_from_db()
        assert order.status == S.DELIVERED

    def test_cannot_skip_to_delivered(self):
        order = make_order()
        with pytest.raises(IllegalTransition, match="Cannot move order"):
            transition_order(order, S.DELIVERED)

    def test_cannot_ship_before_packing(self):
        order = make_order()
        transition_order(order, S.PLACED)
        transition_order(order, S.PAYMENT_CONFIRMED)
        with pytest.raises(IllegalTransition):
            transition_order(order, S.SHIPPED)

    def test_cannot_refund_without_return(self):
        """A refund on goods never returned is a fraud vector."""
        order = make_order()
        for target in (S.PLACED, S.PAYMENT_CONFIRMED, S.PACKED, S.SHIPPED, S.DELIVERED):
            transition_order(order, target)
        with pytest.raises(IllegalTransition):
            transition_order(order, S.REFUNDED)

    def test_full_return_path(self):
        order = make_order()
        for target in (
            S.PLACED, S.PAYMENT_CONFIRMED, S.PACKED, S.SHIPPED, S.DELIVERED,
            S.RETURN_REQUESTED, S.RETURNED, S.REFUNDED,
        ):
            transition_order(order, target)
        order.refresh_from_db()
        assert order.status == S.REFUNDED

    def test_terminal_states_are_final(self):
        order = make_order()
        transition_order(order, S.CANCELLED)
        with pytest.raises(IllegalTransition, match="terminal state"):
            transition_order(order, S.PLACED)

    def test_same_state_transition_rejected(self):
        order = make_order()
        with pytest.raises(IllegalTransition, match="already"):
            transition_order(order, S.DRAFT)

    def test_cannot_cancel_after_shipping(self):
        order = make_order()
        for target in (S.PLACED, S.PAYMENT_CONFIRMED, S.PACKED, S.SHIPPED):
            transition_order(order, target)
        with pytest.raises(IllegalTransition):
            transition_order(order, S.CANCELLED)

    def test_quality_check_can_send_back_to_stitching(self):
        order = make_order()
        for target in (S.PLACED, S.PAYMENT_CONFIRMED, S.IN_ATELIER, S.STITCHING, S.QUALITY_CHECK):
            transition_order(order, target)
        transition_order(order, S.STITCHING, reason="Hem finish rejected at QC")
        order.refresh_from_db()
        assert order.status == S.STITCHING

    def test_error_message_lists_allowed_targets(self):
        order = make_order()
        with pytest.raises(IllegalTransition) as exc:
            transition_order(order, S.SHIPPED)
        assert "placed" in str(exc.value)

    def test_error_message_has_no_enum_repr(self):
        """Messages reach operators and customers; leaking a Python repr is sloppy."""
        order = make_order()
        with pytest.raises(IllegalTransition) as exc:
            transition_order(order, S.DELIVERED)
        message = str(exc.value)
        assert "OrderStatus." not in message
        assert "'delivered'" in message

    def test_accepts_plain_string_target(self):
        order = make_order()
        transition_order(order, "placed")
        order.refresh_from_db()
        assert order.status == S.PLACED

    def test_helpers(self):
        assert can_transition(S.DRAFT, S.PLACED) is True
        assert can_transition(S.DRAFT, S.DELIVERED) is False
        assert available_transitions(S.REFUNDED) == frozenset()


class TestTimestampsAndAudit:
    def test_placed_at_set_once(self):
        order = make_order()
        transition_order(order, S.PLACED)
        order.refresh_from_db()
        assert order.placed_at is not None

    def test_delivered_at_set(self):
        order = make_order()
        for target in (S.PLACED, S.PAYMENT_CONFIRMED, S.PACKED, S.SHIPPED, S.DELIVERED):
            transition_order(order, target)
        order.refresh_from_db()
        assert order.delivered_at is not None

    def test_every_transition_writes_an_event(self):
        order = make_order()
        actor = make_user()
        transition_order(order, S.PLACED, actor=actor, reason="Checkout completed")
        event = OrderEvent.objects.get(order=order)
        assert event.from_status == S.DRAFT
        assert event.to_status == S.PLACED
        assert event.actor == actor
        assert event.reason == "Checkout completed"

    def test_events_accumulate_in_order(self):
        order = make_order()
        transition_order(order, S.PLACED)
        transition_order(order, S.PAYMENT_CONFIRMED)
        assert OrderEvent.objects.filter(order=order).count() == 2

    def test_events_are_append_only(self):
        order = make_order()
        transition_order(order, S.PLACED)
        event = OrderEvent.objects.get(order=order)
        event.to_status = S.DELIVERED
        with pytest.raises(ValueError, match="append-only"):
            event.save()

    def test_failed_transition_writes_no_event(self):
        order = make_order()
        with pytest.raises(IllegalTransition):
            transition_order(order, S.DELIVERED)
        assert OrderEvent.objects.filter(order=order).count() == 0


class TestTaxSnapshot:
    """The snapshot is the invoice. It must be correct and it must be frozen."""

    def _snapshot_from_engine(self, order, *, as_of=None):
        breakdown = calculate_gst(
            [TaxableLine(sku="LEH-1", hsn_code="6211", unit_price=Decimal("48000.00"))],
            PlaceOfSupply(country_code="IN", state_code="MH"),
            as_of=as_of,
        )
        return OrderTaxSnapshot.objects.create(
            order=order,
            regime_name=breakdown.regime_name,
            supply_type=breakdown.supply_type.value,
            place_of_supply_state="MH",
            place_of_supply_country="IN",
            state_gst_code="27",
            taxable_value=breakdown.taxable_value,
            cgst_total=breakdown.cgst_total,
            sgst_total=breakdown.sgst_total,
            igst_total=breakdown.igst_total,
            tax_total=breakdown.tax_total,
            grand_total=breakdown.grand_total,
            is_zero_rated_export=breakdown.is_zero_rated_export,
            line_breakdown=[line.as_dict() for line in breakdown.lines],
            rate_summary=[
                {"rate": str(r), "taxable_value": str(t), "tax": str(x)}
                for r, t, x in breakdown.rate_summary
            ],
            notes=list(breakdown.notes),
        )

    def test_snapshot_records_current_regime(self):
        order = make_order()
        snapshot = self._snapshot_from_engine(order)
        assert "GST 2.0" in snapshot.regime_name
        assert snapshot.tax_total == Decimal("8640.00")

    def test_snapshot_preserves_historical_regime(self):
        """A pre-reform order keeps its 12% treatment forever."""
        order = make_order()
        snapshot = self._snapshot_from_engine(order, as_of=date(2025, 6, 1))
        assert "GST 1.0" in snapshot.regime_name
        assert snapshot.tax_total == Decimal("5760.00")

    def test_snapshot_is_immutable(self):
        order = make_order()
        snapshot = self._snapshot_from_engine(order)
        snapshot.tax_total = Decimal("0.00")
        with pytest.raises(ValueError, match="immutable"):
            snapshot.save()

    def test_components_must_sum_to_total(self):
        order = make_order()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                OrderTaxSnapshot.objects.create(
                    order=order,
                    regime_name="Test",
                    supply_type=SupplyType.INTRA_STATE,
                    place_of_supply_country="IN",
                    taxable_value=Decimal("1000.00"),
                    cgst_total=Decimal("25.00"),
                    sgst_total=Decimal("25.00"),
                    igst_total=Decimal("0.00"),
                    tax_total=Decimal("999.00"),  # deliberately wrong
                    grand_total=Decimal("1999.00"),
                    line_breakdown=[],
                )

    def test_grand_total_must_be_consistent(self):
        order = make_order()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                OrderTaxSnapshot.objects.create(
                    order=order,
                    regime_name="Test",
                    supply_type=SupplyType.INTRA_STATE,
                    place_of_supply_country="IN",
                    taxable_value=Decimal("1000.00"),
                    cgst_total=Decimal("25.00"),
                    sgst_total=Decimal("25.00"),
                    igst_total=Decimal("0.00"),
                    tax_total=Decimal("50.00"),
                    grand_total=Decimal("9999.00"),  # deliberately wrong
                    line_breakdown=[],
                )

    def test_export_must_be_zero_rated(self):
        order = make_order()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                OrderTaxSnapshot.objects.create(
                    order=order,
                    regime_name="Test",
                    supply_type=SupplyType.EXPORT,
                    place_of_supply_country="AE",
                    taxable_value=Decimal("1000.00"),
                    cgst_total=Decimal("0.00"),
                    sgst_total=Decimal("0.00"),
                    igst_total=Decimal("50.00"),
                    tax_total=Decimal("50.00"),  # an export cannot carry tax
                    grand_total=Decimal("1050.00"),
                    is_zero_rated_export=True,
                    line_breakdown=[],
                )


class TestOrderLine:
    def test_quantity_must_be_positive(self):
        order = make_order()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                OrderLine.objects.create(
                    order=order, sku="X", product_name="X", hsn_code="6204",
                    quantity=0, unit_price=Decimal("100.00"),
                )

    def test_modesty_snapshot_persists_as_sold(self):
        """Correcting a product later must not rewrite what was advertised."""
        order = make_order()
        line = OrderLine.objects.create(
            order=order, sku="KS-1", product_name="Karachi Suit", hsn_code="6204",
            quantity=1, unit_price=Decimal("12000.00"),
            modesty_snapshot={"badges": ["fully_lined", "full_coverage"]},
        )
        assert "full_coverage" in line.modesty_snapshot["badges"]

    def test_gross_calculation(self):
        order = make_order()
        line = OrderLine.objects.create(
            order=order, sku="X", product_name="X", hsn_code="6204",
            quantity=3, unit_price=Decimal("1000.00"),
        )
        assert line.gross == Decimal("3000.00")
