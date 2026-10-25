from django.urls import path
from .views import (
    HealthView,
    DocumentView,
    DocumentDetailView,
    DocumentPageView,
    DocumentLayoutView,
    DocumentStatusView,
    DocumentExportView,
)

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path('documents/', DocumentView.as_view(), name='document-list'),
    path('documents/<int:document_id>/layout/', DocumentLayoutView.as_view(), name='document-layout'),
    path('documents/<int:document_id>/status/', DocumentStatusView.as_view(), name='document-status'),
    path('documents/<int:pk>/pages/<int:page_num>/', DocumentPageView.as_view(), name='document-page'),
    path('documents/<int:document_id>/export/', DocumentExportView.as_view(), name='document-export'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
]