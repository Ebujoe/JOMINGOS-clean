from django import forms
from .models import VitalSigns


class VitalSignsForm(forms.ModelForm):
    recorded_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = VitalSigns
        fields = ['temperature', 'bp_systolic', 'bp_diastolic', 'heart_rate',
                  'respiratory_rate', 'oxygen_saturation', 'blood_glucose',
                  'weight_kg', 'pain_score', 'consciousness', 'recorded_at', 'notes']
        widgets = {
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '37.0', 'step': '0.1'}),
            'bp_systolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '120'}),
            'bp_diastolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '80'}),
            'heart_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '72'}),
            'respiratory_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '16'}),
            'oxygen_saturation': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '98', 'step': '0.1'}),
            'blood_glucose': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5.5', 'step': '0.1'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '70.0', 'step': '0.1'}),
            'pain_score': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': 0, 'max': 10}),
            'consciousness': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
