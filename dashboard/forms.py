from django import forms
from apps.tours.models import Tour, ItineraryItem, ActivityCategory


class TourForm(forms.ModelForm):
    """
    Form for creating and editing Tour instances via the guide dashboard.

    Handles datetime-local HTML input format (ISO 8601 partial: YYYY-MM-DDTHH:MM).
    The 'guide' field is intentionally excluded — it is assigned automatically
    in the view based on the logged-in user's role.

    Fields excluded: guide (set in view), tour_code (auto-generated on model save),
    polygon, location_lat, location_lng (Phase 7 map picker), created_at/updated_at.

    ASSUMPTIONS:
    1. The Tour model's start_datetime and end_datetime accept timezone-aware or
       naive datetimes — Django USE_TZ=True means we may need awareness in prod.
    2. The 'guide' assignment is handled entirely in the view; this form never
       touches guide to avoid privilege escalation (guide shouldn't reassign tours).
    3. min_fitness_level default of 1-5 scale matches model PositiveSmallIntegerField.

    FAILURE MODES:
    - Missing start_datetime → form.is_valid() returns False → re-render with errors.
    - Invalid datetime format → form shows field-level error, no DB write occurs.
    - capacity of 0 → PositiveSmallIntegerField allows 0; validation logic TBD Phase 6.
    """

    start_datetime = forms.DateTimeField(
        # Use datetime-local HTML5 input for mobile-friendly date+time picker
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'],
        help_text='Tour start date and time',
    )
    end_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        ),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'],
        help_text='Optional end date and time',
    )

    class Meta:
        """Define the model, included fields, widget overrides, and human-readable labels."""

        model = Tour
        fields = [
            'name',
            'description',
            'start_datetime',
            'end_datetime',
            'location_name',
            'capacity',
            'status',
            'min_fitness_level',
            'rsvp_deadline_hours',
        ]
        widgets = {
            # Textarea for description — 3 rows keeps the form compact on mobile
            'description': forms.Textarea(attrs={'rows': 3}),
            # Placeholder text aids input UX without cluttering the label
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Whale Watching at Hermanus'}),
            'location_name': forms.TextInput(attrs={'placeholder': 'e.g. Hermanus Harbour'}),
        }
        labels = {
            # Override verbose field names to be more human-friendly in the UI
            'name': 'Tour Name',
            'rsvp_deadline_hours': 'RSVP Deadline (hours before start)',
            'min_fitness_level': 'Minimum Fitness Level (1=easy, 5=extreme)',
        }


class ItineraryItemForm(forms.ModelForm):
    """
    Form for creating and editing ItineraryItem instances in the itinerary builder.

    Uses a time HTML5 input for mobile-friendly time selection.
    The 'tour' FK is intentionally excluded — it is set in the view from the URL.
    The 'order' field is a hidden input so the current position is submitted
    but not shown as an editable field (reordering is done via drag-and-drop).

    Fields excluded: tour (set in view), location_lat/lng (Phase 7 map picker),
    distance_km (optional, advanced — can be added later).

    ASSUMPTIONS:
    1. The caller (view) sets item.tour before saving — this form never sets tour.
    2. The 'order' value submitted is the item's current position; the reorder
       endpoint handles position changes after drag-and-drop.
    3. ActivityCategory queryset is unfiltered — all categories shown to all guides.

    FAILURE MODES:
    - Missing title/day/start_time → form.is_valid() returns False → re-render.
    - Invalid time format → field-level error, no DB write.
    """

    start_time = forms.TimeField(
        # HTML5 time picker for mobile-friendly HH:MM input
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text='Activity start time',
    )

    class Meta:
        """Define the model, included fields, widget overrides, and human-readable labels."""

        model = ItineraryItem
        fields = [
            'title',
            'description',
            'category',
            'day',
            'order',
            'start_time',
            'duration_minutes',
            'location_name',
            'difficulty',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'day': forms.NumberInput(attrs={'min': 1, 'placeholder': '1'}),
            # order is submitted hidden — drag-to-reorder controls the visual position
            'order': forms.HiddenInput(),
        }
        labels = {
            'duration_minutes': 'Duration (minutes)',
            'location_name': 'Location name',
        }


class ActivityCategoryForm(forms.ModelForm):
    """
    Form for creating and editing ActivityCategory instances.

    The colour field uses an HTML5 color picker for intuitive selection.
    Validation is also handled by the model-level RegexValidator on the colour field
    (must be a valid 6-digit hex colour like #F97316).

    The icon field accepts any Bootstrap Icons name (e.g. 'geo-alt', 'water', 'bicycle').
    There is no dropdown — guides type the icon name directly.
    A help text link to icons.getbootstrap.com is shown in the template.
    """

    class Meta:
        """Define the model, included fields, widget overrides, and human-readable labels."""

        model = ActivityCategory
        fields = ['name', 'icon', 'colour', 'is_active', 'order']
        widgets = {
            # HTML5 color picker — renders as a colour swatch, outputs #RRGGBB
            'colour': forms.TextInput(attrs={'type': 'color'}),
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Hiking, Wine Tasting'}),
            'icon': forms.TextInput(attrs={'placeholder': 'e.g. geo-alt, water, bicycle'}),
        }
        labels = {
            # Human-readable labels to replace the default verbose field names
            'is_active': 'Show in itinerary builder',
            'order': 'Display order (lower = first)',
        }
        help_texts = {
            # Link to Bootstrap Icons catalogue so guides can look up icon names
            'icon': 'Bootstrap Icons name — find all at icons.getbootstrap.com',
        }
