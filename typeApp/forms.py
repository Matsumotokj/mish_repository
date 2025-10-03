from django import forms
from django.forms import ModelForm, inlineformset_factory



class TranscriptionForm(forms.Form):
    text = forms.CharField(
        label='文字起こし',
        widget=forms.Textarea(attrs={'rows': 20, 'cols': 80, 'id': 'user-input'})
    )

# from .models import Transcription
# class TranscriptionForm(ModelForm):
#     class Meta:
#         model = Transcription
#         fields = ['text']

