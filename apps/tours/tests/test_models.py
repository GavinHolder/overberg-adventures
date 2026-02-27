import pytest
from django.contrib.auth import get_user_model
from apps.tours.models import ActivityCategory, TourCodeWord, Tour, ItineraryItem

User = get_user_model()


@pytest.fixture
def guide():
    return User.objects.create_user(
        username='guide@test.com', email='guide@test.com', password='x'
    )


@pytest.fixture
def tour(guide):
    from django.utils import timezone
    return Tour.objects.create(
        name='Palmiet River Walk',
        guide=guide,
        start_datetime=timezone.now(),
        location_name='Kleinmond',
        location_lat=-34.334,
        location_lng=19.034,
        capacity=10,
        status=Tour.Status.ACTIVE,
    )


@pytest.fixture
def category():
    return ActivityCategory.objects.create(
        name='Hiking', icon='geo-alt', colour='#F97316', order=1
    )


# ActivityCategory tests
@pytest.mark.django_db
def test_activity_category_str():
    cat = ActivityCategory.objects.create(name='Kayaking', icon='water', colour='#0284C7')
    assert str(cat) == 'Kayaking'


@pytest.mark.django_db
def test_activity_category_ordering():
    ActivityCategory.objects.create(name='Z Last', order=3)
    ActivityCategory.objects.create(name='A First', order=1)
    ActivityCategory.objects.create(name='B Second', order=2)
    names = list(ActivityCategory.objects.values_list('name', flat=True))
    assert names[0] == 'A First'


# TourCodeWord tests
@pytest.mark.django_db
def test_tour_code_word_generate():
    TourCodeWord.objects.create(word='fynbos')
    word = TourCodeWord.generate()
    assert word == 'fynbos'
    assert TourCodeWord.objects.get(word='fynbos').is_used is True


@pytest.mark.django_db
def test_tour_code_word_generate_exhausted():
    with pytest.raises(ValueError, match='exhausted'):
        TourCodeWord.generate()


@pytest.mark.django_db
def test_tour_code_word_unique():
    TourCodeWord.objects.create(word='pelican')
    with pytest.raises(Exception):
        TourCodeWord.objects.create(word='pelican')


# Tour tests
@pytest.mark.django_db
def test_tour_str(tour):
    assert 'Palmiet River Walk' in str(tour)


@pytest.mark.django_db
def test_tour_spots_remaining_no_bookings(tour):
    assert tour.spots_remaining == 10
    assert not tour.is_full


@pytest.mark.django_db
def test_tour_spots_remaining_with_bookings(tour):
    from apps.bookings.models import Booking
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for i in range(3):
        user = User.objects.create_user(username=f'guest{i}', password='x')
        Booking.objects.create(user=user, tour=tour, status='RSVP_PENDING')
    assert tour.spots_remaining == 7  # capacity=10, 3 booked


@pytest.mark.django_db
def test_tour_is_full_when_at_capacity(tour):
    tour.capacity = 0
    tour.save()
    assert tour.is_full


# ItineraryItem tests
@pytest.mark.django_db
def test_itinerary_item_ordering(tour, category):
    from datetime import time
    item2 = ItineraryItem.objects.create(
        tour=tour, day=1, order=2, title='Lunch',
        category=category, start_time=time(12, 0)
    )
    item1 = ItineraryItem.objects.create(
        tour=tour, day=1, order=1, title='Breakfast',
        category=category, start_time=time(7, 0)
    )
    items = list(tour.itinerary_items.all())
    assert items[0].title == 'Breakfast'
    assert items[1].title == 'Lunch'


@pytest.mark.django_db
def test_itinerary_item_duration_display(tour, category):
    from datetime import time
    item = ItineraryItem.objects.create(
        tour=tour, day=1, order=1, title='Walk',
        category=category, start_time=time(9, 0),
        duration_minutes=90
    )
    assert item.duration_display == '1 hr 30 min'


@pytest.mark.django_db
def test_itinerary_item_duration_display_hours_only(tour, category):
    from datetime import time
    item = ItineraryItem.objects.create(
        tour=tour, day=1, order=1, title='Drive',
        category=category, start_time=time(9, 0),
        duration_minutes=120
    )
    assert item.duration_display == '2 hr'


# Seed command test
@pytest.mark.django_db
def test_seed_categories_command(capsys):
    from django.core.management import call_command
    call_command('seed_categories')
    assert ActivityCategory.objects.count() == 10
    assert ActivityCategory.objects.filter(name='Hiking').exists()
    assert ActivityCategory.objects.filter(name='Food & Dining').exists()


@pytest.mark.django_db
def test_seed_tour_codes_command():
    from django.core.management import call_command
    call_command('seed_tour_codes')
    assert TourCodeWord.objects.count() > 40
    assert TourCodeWord.objects.filter(word='fynbos').exists()
    assert TourCodeWord.objects.filter(word='pelican').exists()
