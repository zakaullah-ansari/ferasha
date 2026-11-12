"""Media admin: upload images, and decide the ones the detector could not.

* **Add** is an upload page: several files at once, each stored privately and
  queued for the face-blur worker. Nothing else about an asset is typed in.
* **Change** is only possible while an image waits for review. The reviewer
  sees the original (staff only, never cached), ticks that they checked for
  faces, and approves or rejects. Every other asset is view only: the
  pipeline's verdicts are not hand-edited.
* The unblurred original is never a field on these pages and never a public
  URL; it is streamed only through ``review_image`` while a person decides.
"""

from __future__ import annotations

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from unfold.admin import ModelAdmin
from unfold.decorators import display

from . import services
from .models import MediaAsset, ModerationStatus

#: Shown read-only on every asset's page.
DETAIL_FIELDS = (
    "preview",
    "kind",
    "moderation_status",
    "faces_detected",
    "blur_verified",
    "exif_stripped",
    "processing_error",
    "width",
    "height",
    "byte_size",
    "content_type",
    "uploaded_by",
    "created_at",
    "processed_at",
    "attempts",
    "reviewed_by",
    "reviewed_at",
    "checksum",
)

REVIEW_FIELDS = ("decision", "faces_checked", "review_notes")


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleImageInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleImageInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, list | tuple):
            return [single(item, initial) for item in data]
        return [single(data, initial)] if data else []


class MediaUploadForm(forms.ModelForm):
    files = MultipleImageField(
        label=_("Images"),
        help_text=_(
            "JPEG, PNG or WebP, up to 25 MB each. Every image goes through the "
            "face-blur check before it can be shown on the shop."
        ),
    )

    class Meta:
        model = MediaAsset
        fields = ("kind",)

    def clean_files(self):
        files = self.cleaned_data["files"]
        if not files:
            raise ValidationError(_("Choose at least one image."))
        errors = []
        for file in files:
            try:
                if file.size > settings.MEDIA_UPLOAD_MAX_BYTES:
                    raise ValidationError(_("larger than 25 MB"))
                services.inspect_image(file.read())
            except ValidationError as exc:
                errors.append(f"{file.name}: {' '.join(exc.messages)}")
            finally:
                file.seek(0)
        if errors:
            raise ValidationError(errors)
        return files


class MediaReviewForm(forms.ModelForm):
    decision = forms.ChoiceField(
        label=_("Decision"),
        required=False,
        choices=(
            ("", _("Decide later")),
            ("approve", _("Approve: no face can be seen")),
            ("reject", _("Reject: a face or something private is visible")),
        ),
    )
    faces_checked = forms.BooleanField(
        label=_("I have looked at the whole image, including veiled and side-on faces"),
        required=False,
    )

    class Meta:
        model = MediaAsset
        fields = ("review_notes",)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "approve" and not cleaned.get("faces_checked"):
            self.add_error("faces_checked", _("Tick this to confirm you checked the image for faces."))
        return cleaned


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ("__str__", "kind", "moderation_badge", "faces_detected", "blur_verified", "created_at")
    list_filter = ("moderation_status", "kind", "blur_verified")
    search_fields = ("id", "checksum", "uploaded_by__email")
    actions = ("send_to_privacy_check",)

    # -- permissions ---------------------------------------------------------

    def has_change_permission(self, request, obj=None) -> bool:
        if obj is not None and obj.moderation_status != ModerationStatus.NEEDS_REVIEW:
            return False  # the pipeline's verdicts are view only
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None) -> bool:
        return False  # product images PROTECT their asset; nothing is deleted here

    # -- forms ---------------------------------------------------------------

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("kind", "files")
        if self.has_change_permission(request, obj):
            return (*REVIEW_FIELDS, *DETAIL_FIELDS)
        return DETAIL_FIELDS

    def get_readonly_fields(self, request, obj=None):
        return () if obj is None else DETAIL_FIELDS

    def get_form(self, request, obj=None, change=False, **kwargs):
        kwargs["form"] = MediaUploadForm if obj is None else MediaReviewForm
        return super().get_form(request, obj, change=change, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            with transaction.atomic():
                created = [
                    services.create_from_upload(file, kind=form.cleaned_data["kind"], uploaded_by=request.user)
                    for file in form.cleaned_data["files"]
                ]
            # The admin logs and redirects using `obj`: point it at the first upload.
            obj.pk, obj._state.adding = created[0].pk, False
            obj.moderation_status = created[0].moderation_status
            self.message_user(
                request,
                ngettext(
                    "%(n)d image uploaded. It will show as Approved or Needs review within a minute.",
                    "%(n)d images uploaded. They will show as Approved or Needs review within a minute.",
                    len(created),
                )
                % {"n": len(created)},
                messages.SUCCESS,
            )
            return

        decision, notes = form.cleaned_data.get("decision"), form.cleaned_data.get("review_notes", "")
        if decision == "approve":
            services.approve_after_review(obj, reviewer=request.user, notes=notes)
        elif decision == "reject":
            services.reject_after_review(obj, reviewer=request.user, notes=notes)
        # "Decide later" changes nothing.

    def response_add(self, request, obj, post_url_continue=None):
        # One message from save_model is enough; go back to the list.
        return HttpResponseRedirect(reverse("admin:media_assets_mediaasset_changelist"))

    # -- display -------------------------------------------------------------

    @display(description=_("Image"))
    def preview(self, obj: MediaAsset):
        if obj.moderation_status == ModerationStatus.NEEDS_REVIEW:
            src = reverse("admin:media_assets_mediaasset_review_image", args=[obj.pk])
        elif obj.is_publishable:
            src = obj.public_url
        else:
            return "-"
        return format_html(
            '<img src="{}" alt="" style="max-height:28rem;max-width:100%;border-radius:.5rem">', src
        )

    @display(
        description=_("Moderation"),
        ordering="moderation_status",
        label={
            ModerationStatus.APPROVED.label: "success",
            ModerationStatus.NEEDS_REVIEW.label: "warning",
            ModerationStatus.PENDING.label: "info",
            ModerationStatus.PROCESSING.label: "info",
            ModerationStatus.REJECTED.label: "danger",
            ModerationStatus.FAILED.label: "danger",
        },
    )
    def moderation_badge(self, obj: MediaAsset) -> str:
        return obj.get_moderation_status_display()

    # -- actions -------------------------------------------------------------

    @admin.action(description=_("Send to the privacy check again"), permissions=["change"])
    def send_to_privacy_check(self, request, queryset):
        retry = queryset.filter(moderation_status__in=[ModerationStatus.PENDING, ModerationStatus.FAILED])
        for asset in retry:
            services.enqueue_blur(asset)
        self.message_user(
            request,
            _("%(sent)d sent again; %(skipped)d skipped (only waiting or failed images can be).")
            % {"sent": retry.count(), "skipped": queryset.count() - retry.count()},
        )

    # -- the reviewer's view of the original ----------------------------------

    def get_urls(self):
        return [
            path(
                "<uuid:object_id>/review-image/",
                self.admin_site.admin_view(self.review_image),
                name="media_assets_mediaasset_review_image",
            ),
            *super().get_urls(),
        ]

    def review_image(self, request, object_id):
        if not super().has_change_permission(request):
            raise Http404
        asset = get_object_or_404(MediaAsset, pk=object_id)
        if asset.moderation_status != ModerationStatus.NEEDS_REVIEW:
            raise Http404  # the original is shown only while a person decides
        response = FileResponse(asset.original.open("rb"), content_type=asset.content_type)
        response["Cache-Control"] = "no-store, private"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    # -- the product-image picker --------------------------------------------

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        # The product-image picker (autocomplete) offers only assets that may be
        # published, instead of listing everything and refusing on save.
        if request.GET.get("model_name") == "productimage":
            queryset = queryset.filter(moderation_status=ModerationStatus.APPROVED)
        return queryset, may_have_duplicates
