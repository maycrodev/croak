# HU — Fundaciones e Identidad (Stream A)

Base transversal que habilita los MVPs: identidad, roles y punto de entrada único.

## HU-01 — Autenticación de usuarios

**Como** usuario de la plataforma (estudiante, profesor o administrador)
**quiero** iniciar sesión con mi email y contraseña
**para** obtener un token que me identifique en las demás operaciones.

**Criterios de aceptación:**
- Con credenciales válidas, `POST /auth/login` devuelve un JWT y los datos del usuario.
- Con credenciales inválidas, responde `401`.
- El token incluye el identificador del usuario (`sub`) y su `role`.

## HU-02 — Gestión de usuarios con roles

**Como** administrador
**quiero** dar de alta usuarios con un rol (`student`, `professor`, `admin`)
**para** que cada quien tenga los permisos correspondientes a su función.

**Criterios de aceptación:**
- `POST /users` crea un usuario con su rol y devuelve `201`.
- Un email duplicado responde `409`.
- La contraseña se almacena cifrada (hash), nunca en texto plano.

## HU-03 — Punto de entrada único y seguro

**Como** equipo de la plataforma
**quiero** que todas las llamadas pasen por un único gateway que valide el token
**para** centralizar la seguridad y el enrutamiento entre microservicios.

**Criterios de aceptación:**
- El `gateway` enruta cada petición al microservicio correcto según la ruta.
- Las rutas protegidas sin token válido responden `401`.
- El gateway propaga la identidad verificada (`X-User-Id`, `X-User-Role`) a los
  servicios internos.
