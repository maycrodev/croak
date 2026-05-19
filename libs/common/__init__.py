"""Utilidades compartidas: configuracion, persistencia, JWT, logging y auditoria.

Este __init__ NO importa submodulos de forma anticipada: cada servicio importa
solo lo que necesita (p. ej. el gateway no arrastra SQLAlchemy).
"""
