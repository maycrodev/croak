# lms-mainframe-mock

Mainframe LMS legacy simulado. Puerto 8012.

Expone `POST /COBOL/GRADESYNC`: recibe un registro de ancho fijo de 80 caracteres
y responde con codigos numericos (0000 OK / 0012 validacion / 0099 interno).
Implementado en MVP2. Layout: docs/arquitectura/adr-005-mainframe-layout.md.