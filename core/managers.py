from __future__ import annotations

from django.db import models
from django.db.models import Q


class TaskQuerySet(models.QuerySet):
    def for_responsible(self, user):
        return self.filter(responsible=user)

    def for_manager(self, manager):
        return self.filter(Q(responsible=manager) | Q(responsible__under_supervision=manager))

    def evaluated(self):
        return self.filter(evaluation_status='evaluated')

    def due(self):
        return self.filter(status='due')

    def open_(self):
        return self.filter(status='open')


