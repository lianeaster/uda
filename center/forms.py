from core.forms import ContactRequestForm
from core.models import ContactRequest


class CenterContactForm(ContactRequestForm):
    """Та сама заявка, що й в Академії, лише з позначкою «з Центру».

    Питання тут інше — не «який курс», а «що у вас є»: сировина, обсяг, ідея.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interest'].label = 'Що у вас є або що цікавить'
        self.fields['interest'].widget.attrs['placeholder'] = (
            'Сировина й обсяг, ідея продукту, пілотна партія, навчання…'
        )

    def save(self, commit=True):
        self.instance.source = ContactRequest.Source.CENTER
        return super().save(commit)


class FoodAcademyContactForm(ContactRequestForm):
    """Заявка з харчової академії: напрям і чи людина хоче вчитися, чи викладати."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interest'].label = 'Який напрям цікавить'
        self.fields['interest'].widget.attrs['placeholder'] = (
            'Снеки, соуси, ферментація… Хочу вчитися чи викладати'
        )

    def save(self, commit=True):
        self.instance.source = ContactRequest.Source.FOOD_ACADEMY
        return super().save(commit)
