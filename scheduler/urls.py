from django.urls import path

from . import views

app_name = "scheduler"

urlpatterns = [
    # Views
    path(
        "",
        views.supervisor_dashboard,
        name="dashboard",
    ),
    
    path(
        "schedules/",
        views.ScheduleListView.as_view(),
        name="schedule_list",
    ),
    
    path(
        "schedules/<int:pk>/",
        views.ScheduleDetailView.as_view(),
        name="schedule_detail",
    ),
    
    # API endpoints
    path(
        "api/schedules/<int:schedule_id>/operations/",
        views.schedule_operations_json,
        name="schedule_operations_json",
    ),
]
