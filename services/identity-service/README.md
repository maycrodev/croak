# identity-service

Usuarios, roles y emision de JWT. Puerto **8001**, schema **`identity`**.

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/health` | Estado del servicio |
| POST | `/users` | Alta de usuario (`student` / `professor` / `admin`) |
| GET | `/users` | Listado de usuarios |
| POST | `/auth/login` | Valida credenciales y devuelve un JWT HS256 |
| GET | `/users/me` | Perfil del usuario autenticado (requiere `Authorization: Bearer`) |

Contrasenas: PBKDF2-HMAC-SHA256 (`security.py`, solo stdlib). El token JWT
incluye `sub` (id de usuario) y `role`, y lo valida el `gateway`.
