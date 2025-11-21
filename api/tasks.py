from celery import shared_task
from django.core.mail import EmailMessage
from .models import Booking
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings

@shared_task
def send_booking_notifications(booking_id):
    try:
        booking = Booking.objects.select_related('site','site__location','user').get(id=booking_id)
    except Booking.DoesNotExist:
        return

    # Generate PDF receipt HTML
    html = render_to_string('booking_receipt.html', {'booking': booking})
    pdf_file = f"/tmp/receipt_{booking_id}.pdf"
    HTML(string=html).write_pdf(pdf_file)

    # Send email
    subject = f"Your booking receipt - {booking.id}"
    body = "Please find attached receipt."
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.user.email] if booking.user else [booking.user.email or ''])
    email.attach_file(pdf_file)
    try:
        email.send()
    except Exception as e:
        # log

        pass

    # Send SMS
    # Implement provider call here, e.g. Twilio or Indian SMS provider
    # sms_send(phone_number, f"Booking confirmed: {booking.id}")

    return True
