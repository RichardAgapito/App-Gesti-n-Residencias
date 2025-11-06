
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views 
urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.dashboard, name='dashboard'), 
    path('usuarios/crear/', views.crear_usuario_view, name='crear_usuario'),
    path('usuarios/', views.lista_usuarios_view, name='lista_usuarios'),
    path('usuarios/<int:user_id>/', views.detalle_usuario_view, name='detalle_usuario'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario_view, name='editar_usuario'),
]