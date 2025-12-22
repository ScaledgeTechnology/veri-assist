from django.urls import path

from . import views

urlpatterns = [
    path('',views.spec_index,name='spec_index'),

]