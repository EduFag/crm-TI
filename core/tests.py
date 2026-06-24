from django.test import TestCase

from core.models import CustomUser
from core.permissions import MODULO_GESTAO_USUARIOS, usuario_pode_acessar_modulo


class PermissoesModuloGestaoUsuariosTest(TestCase):
    def test_it_user_pode_acessar_gestao_usuarios(self):
        usuario = CustomUser(role=CustomUser.RoleChoices.IT_USER)
        self.assertTrue(usuario_pode_acessar_modulo(usuario, MODULO_GESTAO_USUARIOS))

    def test_standard_nao_pode_acessar_gestao_usuarios(self):
        usuario = CustomUser(role=CustomUser.RoleChoices.STANDARD)
        self.assertFalse(usuario_pode_acessar_modulo(usuario, MODULO_GESTAO_USUARIOS))
