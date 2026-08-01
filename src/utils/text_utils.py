

import unicodedata


def normalizar_texto(texto):
    """
    Normaliza un texto eliminando tildes, convirtiendo a minúsculas y quitando espacios extra.
    Útil para comparar cadenas de texto de manera insensible a mayúsculas/minúsculas y acentos.
    """
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto