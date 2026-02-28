from django import forms
from apps.tours.models import Tour


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
