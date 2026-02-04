from django.urls import path,include
from .views import *


urlpatterns = [
    path('mrz/', PassportAPI.as_view()), #  Branch.as_view({'get': 'list'}) bele olsaydi Branch View yox gerek Viewset olardi
    path('statistics/', StatisticsApi.as_view()),
    path('customer-list/', CustomerList.as_view()),
    path('visit-list-customer/', VisitListOfCustomer.as_view()), 
    path('export/', Export.as_view()), 
    path('transactions/<int:visit_id>/',TransactionList.as_view()),
    path('declarations/visits/<int:visit_id>/',VisitsList.as_view()),
    path('services',ServiceListApi.as_view()),
    path('branches',BranchListApi.as_view()),
    path('risk-fin/', RiskFinUpdateApi.as_view()),
    path('audio-recording/', AudioRecordingApi.as_view()),
    path('audio-recordings/', AudioRecordingsApi.as_view())
]
