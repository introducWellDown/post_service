from django.db import models

class EmailAccount(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)


class EmailMessage(models.Model):
    email_account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    sent_date = models.DateTimeField()
    received_date = models.DateTimeField()
    body = models.TextField()
    attachments = models.JSONField()
    uid = models.CharField(max_length=255, unique=True) 

    @staticmethod
    def get_last_received_date(email_account):
        last_message = EmailMessage.objects.filter(email_account=email_account).order_by('-received_date').first()
        return last_message.received_date if last_message else None