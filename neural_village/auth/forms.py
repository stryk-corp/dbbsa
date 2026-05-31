from django import forms


LOGIN_ROLE_CHOICES = [
    ('student', 'Student'),
    ('instructor', 'Instructor'),
]


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'w-full rounded-3xl border border-slate-200 px-5 py-4 text-slate-700',
            'placeholder': 'Username',
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full rounded-3xl border border-slate-200 px-5 py-4 text-slate-700',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        }),
    )
    role = forms.ChoiceField(
        choices=LOGIN_ROLE_CHOICES,
        widget=forms.HiddenInput(),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-teal-600 focus:ring-teal-500 border-gray-300 rounded',
        }),
    )
