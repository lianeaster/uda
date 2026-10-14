"""Помічники для тестів: предмет одразу в програмі курсу."""

from .models import CourseSubject, Subject


def make_subject(name, course=None, position=0, code=''):
    subject = Subject.objects.create(name=name)
    if course is not None:
        CourseSubject.objects.create(course=course, subject=subject, position=position, code=code)
    return subject
